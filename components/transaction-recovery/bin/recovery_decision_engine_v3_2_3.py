#!/usr/bin/env python3
from pathlib import Path
"""TITAN Recovery Decision Engine V3.2.3 — synthetic-only."""

import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
from contextlib import ExitStack

import secure_descriptor_v1 as secure
import recovery_business_validation_v1 as business

ROOT = os.environ.get(
    "TITAN_TEST_ROOT",
    str(Path(__file__).resolve().parent.parent / "tests")
)

GEN = re.compile(r"GEN-[0-9]{16}")
STAGING = re.compile(r"\.staging\.[A-Za-z0-9_-]+")
LAB = re.compile(r"recovery-lab\.[A-Za-z0-9_-]+")
CASE = re.compile(r"case-[A-Z]")

DIR_FLAGS = secure.DIR_FLAGS


class RecoveryError(Exception):
    pass


def reject(reason):
    raise RecoveryError(reason)


def open_dir(name, parent_fd):
    try:
        return secure.open_directory(name, parent_fd)
    except (OSError, secure.SecureDescriptorError):
        reject("UNSAFE_DIRECTORY")


def read_file(name, parent_fd, limit=16 * 1024 * 1024):
    try:
        return secure.read_regular_file(name, parent_fd, limit)
    except (OSError, secure.SecureDescriptorError):
        reject("MISSING_OR_UNSAFE_ARTIFACT")


def strict_json(raw):
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=business.unique_pairs,
            parse_constant=business.reject_constant
        )
    except (ValueError, UnicodeError):
        reject("INVALID_JSON_DOCUMENT")
    except business.IntegrityError as exc:
        reject(str(exc))
    return value


def inventory(fd):
    try:
        names = os.listdir(fd)
    except OSError:
        reject("GENERATION_INVENTORY_FAILED")

    published = []
    staging = []

    for name in names:
        if GEN.fullmatch(name):
            published.append(name)
        elif STAGING.fullmatch(name):
            staging.append(name)
        else:
            reject("UNKNOWN_GENERATION_ENTRY")

        try:
            metadata = os.stat(
                name,
                dir_fd=fd,
                follow_symlinks=False
            )
        except OSError:
            reject("UNSAFE_GENERATION_ENTRY")

        if not stat.S_ISDIR(metadata.st_mode):
            reject("UNSAFE_GENERATION_ENTRY")

    return sorted(published), sorted(staging)


def identity(fd):
    metadata = os.fstat(fd)
    return metadata.st_dev, metadata.st_ino


def verify_name_identity(name, parent_fd, expected):
    try:
        metadata = os.stat(
            name,
            dir_fd=parent_fd,
            follow_symlinks=False
        )
    except OSError:
        reject("DIRECTORY_IDENTITY_CHANGED")

    if (
        not stat.S_ISDIR(metadata.st_mode)
        or (metadata.st_dev, metadata.st_ino) != expected
    ):
        reject("DIRECTORY_IDENTITY_CHANGED")



def read_artifact_identity(name, parent_fd):
    try:
        fd = secure.open_regular_file(name, parent_fd)
    except (OSError, secure.SecureDescriptorError):
        reject("MISSING_OR_UNSAFE_ARTIFACT")

    try:
        before = os.fstat(fd)

        if not stat.S_ISREG(before.st_mode):
            reject("MISSING_OR_UNSAFE_ARTIFACT")

        chunks = []
        total = 0
        limit = 16 * 1024 * 1024

        while True:
            chunk = os.read(fd, min(65536, limit + 1 - total))

            if not chunk:
                break

            total += len(chunk)

            if total > limit:
                reject("ARTIFACT_SIZE_LIMIT_EXCEEDED")

            chunks.append(chunk)

        after = os.fstat(fd)

        try:
            pathname = os.stat(
                name,
                dir_fd=parent_fd,
                follow_symlinks=False
            )
        except OSError:
            reject("ARTIFACT_IDENTITY_CHANGED")

        before_identity = (before.st_dev, before.st_ino)
        after_identity = (after.st_dev, after.st_ino)
        path_identity = (pathname.st_dev, pathname.st_ino)

        if (
            not stat.S_ISREG(after.st_mode)
            or not stat.S_ISREG(pathname.st_mode)
            or before_identity != after_identity
            or after_identity != path_identity
        ):
            reject("ARTIFACT_IDENTITY_CHANGED")

        return b"".join(chunks), after_identity

    except OSError:
        reject("ARTIFACT_READ_FAILED")
    finally:
        os.close(fd)


def inspect_generation(name, generations_fd, expected, stack):
    fd = open_dir(name, generations_fd)
    stack.callback(os.close, fd)

    expected_identity = identity(fd)

    incident_raw, incident_identity = read_artifact_identity(
        "incident.json", fd
    )
    registry_raw, registry_identity = read_artifact_identity(
        "registry.json", fd
    )

    incident = strict_json(incident_raw)
    registry = strict_json(registry_raw)

    incident_sha = hashlib.sha256(incident_raw).hexdigest()
    registry_sha = hashlib.sha256(registry_raw).hexdigest()

    try:
        details = business.validate_generation_artifacts(
            incident,
            registry,
            incident_sha,
            registry_sha,
            expected
        )
    except business.IntegrityError as exc:
        reject(str(exc))

    verify_name_identity(name, generations_fd, expected_identity)

    return {
        "fd": fd,
        "identity": expected_identity,
        "details": details,
        "artifact_identities": {
            "incident.json": incident_identity,
            "registry.json": registry_identity
        }
    }


def evaluate(case_fd, stack):
    generations_fd = open_dir("generations", case_fd)
    stack.callback(os.close, generations_fd)

    current_raw = read_file("CURRENT", case_fd, 128)

    try:
        current = current_raw.decode("ascii").strip()
    except UnicodeError:
        reject("INVALID_CURRENT_POINTER")

    if not GEN.fullmatch(current):
        reject("INVALID_CURRENT_POINTER")

    published, staging = inventory(generations_fd)

    if current not in published:
        reject("CURRENT_GENERATION_MISSING")

    inspected = {}

    inspected[current] = inspect_generation(
        current,
        generations_fd,
        business.generation_number(current),
        stack
    )

    orphan = [
        name for name in published
        if business.generation_number(name)
        > business.generation_number(current)
    ]

    for name in orphan:
        inspected[name] = inspect_generation(
            name,
            generations_fd,
            business.generation_number(name),
            stack
        )

    if read_file("CURRENT", case_fd, 128) != current_raw:
        reject("CURRENT_CHANGED_DURING_INSPECTION")

    published_after, staging_after = inventory(generations_fd)

    if (
        published_after != published
        or staging_after != staging
    ):
        reject("INVENTORY_CHANGED_DURING_INSPECTION")

    for name, record in inspected.items():
        verify_name_identity(
            name,
            generations_fd,
            record["identity"]
        )

        fd = record["fd"]
        details = record["details"]

        for filename, key in (
            ("incident.json", "incident_sha256"),
            ("registry.json", "registry_sha256")
        ):
            raw, artifact_identity = read_artifact_identity(
                filename, fd
            )

            if artifact_identity != record["artifact_identities"][filename]:
                reject("ARTIFACT_IDENTITY_CHANGED")

            if hashlib.sha256(raw).hexdigest() != details[key]:
                reject("ARTIFACT_CHANGED_DURING_INSPECTION")

    if staging:
        decision = "KEEP_CURRENT"
        action = "STAGING_REVIEW_REQUIRED"
    elif orphan:
        decision = "KEEP_CURRENT"
        action = "ORPHAN_REVIEW_REQUIRED"
    else:
        decision = "ACCEPT_CURRENT"
        action = "CONSISTENT"

    return {
        "contract_version": "3.2.3",
        "engine": "recovery_decision_engine_v3_2_3",
        "current_generation": current,
        "published_generations": published,
        "staging_directories": staging,
        "orphan_generations": orphan,
        "decision": decision,
        "action": action,
        "automatic_promotion": False,
        "automatic_cleanup": False,
        "read_only": True,
        "snapshot_consistency": "COOPERATIVE_SHARED_LOCK",
        "lock_mode": "LOCK_SH",
        "path_access": "DESCRIPTOR_BASED"
    }


def run(case_path):
    path = os.path.abspath(case_path)
    relative = os.path.relpath(path, ROOT)
    parts = relative.split(os.sep)

    if (
        len(parts) != 2
        or not LAB.fullmatch(parts[0])
        or not CASE.fullmatch(parts[1])
        or path != os.path.join(ROOT, *parts)
    ):
        reject("CASE_OUTSIDE_SYNTHETIC_SCOPE")

    with secure.open_synthetic_case(*parts) as case_fd:
        lock_fd = read_lock(case_fd)

        try:
            verify_lock_identity(case_fd, lock_fd)

            with ExitStack() as stack:
                result = evaluate(case_fd, stack)

            verify_lock_identity(case_fd, lock_fd)
            return result
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)



def verify_lock_identity(case_fd, lock_fd):
    try:
        descriptor = os.fstat(lock_fd)
        pathname = os.stat(
            "lock",
            dir_fd=case_fd,
            follow_symlinks=False
        )
    except OSError:
        reject("LOCK_IDENTITY_MISMATCH")

    if (
        not stat.S_ISREG(descriptor.st_mode)
        or not stat.S_ISREG(pathname.st_mode)
        or descriptor.st_dev != pathname.st_dev
        or descriptor.st_ino != pathname.st_ino
    ):
        reject("LOCK_IDENTITY_MISMATCH")


def read_lock(case_fd):
    try:
        fd = secure.open_regular_file("lock", case_fd)
    except (OSError, secure.SecureDescriptorError):
        reject("LOCK_OPEN_FAILED")

    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            reject("LOCK_BUSY")
        except OSError:
            reject("LOCK_ACQUISITION_FAILED")

        metadata = os.fstat(fd)

        pathname = os.stat(
            "lock",
            dir_fd=case_fd,
            follow_symlinks=False
        )

        if (
            not stat.S_ISREG(pathname.st_mode)
            or metadata.st_dev != pathname.st_dev
            or metadata.st_ino != pathname.st_ino
        ):
            reject("LOCK_IDENTITY_MISMATCH")

        return fd

    except BaseException:
        os.close(fd)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    args = parser.parse_args()

    try:
        result = run(args.case)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except RecoveryError as exc:
        print(f"ERROR={exc}")
        return 1
    except (
        OSError,
        ValueError,
        TypeError,
        business.IntegrityError,
        secure.SecureDescriptorError
    ):
        print("ERROR=RECOVERY_INSPECTION_FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

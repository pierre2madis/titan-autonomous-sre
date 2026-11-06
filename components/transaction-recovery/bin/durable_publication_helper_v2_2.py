#!/usr/bin/env python3
from pathlib import Path
"""TITAN synthetic-lab durable publication helper V2."""

import argparse
import os
import re
import stat
import sys
import tempfile

BASE = os.environ.get(
    "TITAN_TEST_ROOT",
    str(Path(__file__).resolve().parent.parent / "tests")
)


def fail(code):
    raise RuntimeError(code)


def open_directory(path):
    return os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    )


def fsync_directory(path):
    fd = open_directory(path)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def fsync_regular_file(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            fail("INVALID_FILE_TYPE")
        os.fsync(fd)
    finally:
        os.close(fd)


def write_all(fd, data):
    view = memoryview(data)
    while view:
        count = os.write(fd, view)
        if count <= 0:
            fail("SHORT_WRITE")
        view = view[count:]


def validate_paths(lab, staging, generation):
    lab_name = os.path.basename(lab)

    if not re.fullmatch(
        r"transaction-lab\.[A-Za-z0-9_-]+",
        lab_name
    ):
        fail("INVALID_LAB_NAME")

    if lab != os.path.join(BASE, lab_name):
        fail("UNSAFE_LAB_PATH")

    if not re.fullmatch(r"GEN-[0-9]{16}", generation):
        fail("INVALID_GENERATION")

    generations = os.path.join(lab, "generations")

    if os.path.dirname(staging) != generations:
        fail("UNSAFE_STAGING_PARENT")

    if not re.fullmatch(
        r"\.staging\.[A-Za-z0-9]+",
        os.path.basename(staging)
    ):
        fail("INVALID_STAGING_NAME")

    for path in (BASE, lab, generations, staging):
        fd = open_directory(path)
        os.close(fd)

    device = os.stat(lab).st_dev

    for path in (generations, staging):
        if os.stat(path).st_dev != device:
            fail("FILESYSTEM_DEVICE_MISMATCH")

    destination = os.path.join(generations, generation)

    if os.path.lexists(destination):
        fail("GENERATION_ALREADY_EXISTS")

    current = os.path.join(lab, "CURRENT")

    fd = os.open(current, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            fail("INVALID_CURRENT_POINTER")
    finally:
        os.close(fd)

    return generations, destination, current


def publish(lab, staging, generation):
    generations, destination, current = validate_paths(
        lab, staging, generation
    )

    phase = "BEFORE_GENERATION_RENAME"
    temporary_pointer = None

    with open(current, "r", encoding="ascii") as stream:
        original_current = stream.read()

    expected_previous = (
        f"GEN-{int(generation[4:]) - 1:016d}\n"
    )

    if original_current != expected_previous:
        fail("STALE_CURRENT_POINTER")

    try:
        fsync_regular_file(
            os.path.join(staging, "incident.json")
        )
        fsync_regular_file(
            os.path.join(staging, "registry.json")
        )
        fsync_directory(staging)

        os.rename(staging, destination)
        phase = "GENERATION_RENAMED"

        fsync_directory(generations)
        phase = "GENERATION_DURABLE"

        fd, temporary_pointer = tempfile.mkstemp(
            prefix=".CURRENT.durable.",
            dir=lab
        )

        try:
            write_all(
                fd,
                (generation + "\n").encode("ascii")
            )
            os.fsync(fd)
        finally:
            os.close(fd)

        with open(current, "r", encoding="ascii") as stream:
            if stream.read() != expected_previous:
                fail("CURRENT_CHANGED_BEFORE_PUBLICATION")

        os.replace(temporary_pointer, current)
        temporary_pointer = None
        phase = "CURRENT_REPLACED"

        fsync_directory(lab)
        phase = "CURRENT_DURABLE"

        print("generation_durability=PASS")
        print("current_durability=PASS")
        print("transaction_status=COMMITTED")
        print("RESULT=DURABLE_PUBLICATION_PASS")

    except Exception as exc:
        if phase in (
            "CURRENT_REPLACED",
            "CURRENT_DURABLE"
        ):
            status = "COMMIT_OUTCOME_UNCERTAIN"
        elif phase in (
            "GENERATION_RENAMED",
            "GENERATION_DURABLE"
        ):
            status = "GENERATION_PUBLISHED_POINTER_UNCHANGED"
        else:
            status = "PUBLICATION_NOT_STARTED"

        print(
            f"transaction_status={status}",
            file=sys.stderr
        )
        print(
            f"publication_phase={phase}",
            file=sys.stderr
        )
        print(
            f"error_type={type(exc).__name__}",
            file=sys.stderr
        )
        print(
            f"error_detail={exc}",
            file=sys.stderr
        )
        raise

    finally:
        if temporary_pointer is not None:
            try:
                os.unlink(temporary_pointer)
            except OSError:
                pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lab", required=True)
    parser.add_argument("--staging", required=True)
    parser.add_argument("--next-generation", required=True)
    args = parser.parse_args()

    publish(
        args.lab,
        args.staging,
        args.next_generation
    )


if __name__ == "__main__":
    main()

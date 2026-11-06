#!/usr/bin/env python3
from pathlib import Path

import os
import re
import stat
from contextlib import contextmanager

SYNTHETIC_ROOT = os.environ.get(
    "TITAN_TEST_ROOT",
    str(Path(__file__).resolve().parent.parent / "tests")
)

DIR_FLAGS = (
    os.O_RDONLY
    | os.O_DIRECTORY
    | os.O_NOFOLLOW
    | os.O_CLOEXEC
)

FILE_FLAGS = (
    os.O_RDONLY
    | os.O_NOFOLLOW
    | os.O_CLOEXEC
    | os.O_NONBLOCK
)


class SecureDescriptorError(Exception):
    pass


def validate_component(name):
    if (
        not isinstance(name, str)
        or not name
        or name in (".", "..")
        or "/" in name
        or "\x00" in name
    ):
        raise SecureDescriptorError("INVALID_PATH_COMPONENT")

    return name


def open_directory(name, parent_fd):
    validate_component(name)

    fd = os.open(name, DIR_FLAGS, dir_fd=parent_fd)

    if not stat.S_ISDIR(os.fstat(fd).st_mode):
        os.close(fd)
        raise SecureDescriptorError("INVALID_DIRECTORY_TYPE")

    return fd


def open_regular_file(name, parent_fd):
    validate_component(name)

    fd = os.open(name, FILE_FLAGS, dir_fd=parent_fd)

    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise SecureDescriptorError("INVALID_FILE_TYPE")

    return fd


def read_regular_file(name, parent_fd, max_bytes=16 * 1024 * 1024):
    if not isinstance(max_bytes, int) or max_bytes < 1:
        raise SecureDescriptorError("INVALID_SIZE_LIMIT")

    fd = open_regular_file(name, parent_fd)

    try:
        chunks = []
        total = 0

        while True:
            chunk = os.read(fd, min(65536, max_bytes - total + 1))

            if not chunk:
                break

            total += len(chunk)

            if total > max_bytes:
                raise SecureDescriptorError("FILE_SIZE_LIMIT_EXCEEDED")

            chunks.append(chunk)

        return b"".join(chunks)

    finally:
        os.close(fd)


@contextmanager
def open_synthetic_case(lab_name, case_name):
    if not re.fullmatch(r"recovery-lab\.[A-Za-z0-9_-]+", lab_name):
        raise SecureDescriptorError("INVALID_LAB_NAME")

    if not re.fullmatch(r"case-[A-Z]", case_name):
        raise SecureDescriptorError("INVALID_CASE_NAME")

    root_fd = os.open(SYNTHETIC_ROOT, DIR_FLAGS)

    try:
        lab_fd = open_directory(lab_name, root_fd)

        try:
            case_fd = open_directory(case_name, lab_fd)

            try:
                yield case_fd
            finally:
                os.close(case_fd)

        finally:
            os.close(lab_fd)

    finally:
        os.close(root_fd)

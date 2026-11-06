#!/usr/bin/env python3
import json
import sys

class DuplicateKeyError(ValueError):
    pass

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result

def reject_constant(value):
    raise ValueError("Non-standard JSON constant")

def main():
    if len(sys.argv) != 2:
        print("ERROR=INVALID_ARGUMENTS", file=sys.stderr)
        return 2

    path = sys.argv[1]

    try:
        with open(path, "r", encoding="utf-8") as handle:
            json.load(
                handle,
                object_pairs_hook=unique_object,
                parse_constant=reject_constant
            )
    except DuplicateKeyError:
        print("ERROR=DUPLICATE_JSON_KEY", file=sys.stderr)
        return 1
    except (ValueError, UnicodeError, OSError):
        print("ERROR=INVALID_JSON_DOCUMENT", file=sys.stderr)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())

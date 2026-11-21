#!/usr/bin/env python3
"""Deliver the pre-rendered passport page.

The artwork is produced once, locally, and committed as entry.png next to
this file. This program has no third-party dependency: it only copies that
image into the output directory and verifies the copy, so it runs in a bare
Python sandbox as well as on a full install.
"""

import hashlib
import os
import shutil
import sys
from pathlib import Path

ENTRY_NAME = "entry.png"
EXPECTED_SHA256 = "cca9d22b3bf63584835199e54c1670b91b209422285ddd04d309c0083663e732"


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    source = Path(__file__).resolve().parent / ENTRY_NAME
    if not source.is_file():
        print(f"missing committed artwork: {source}", file=sys.stderr)
        return 1
    if source.stat().st_size == 0:
        print(f"committed artwork is empty: {source}", file=sys.stderr)
        return 1

    out_dir = Path(os.environ.get("OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / ENTRY_NAME

    shutil.copyfile(source, target)
    got = sha256_of(target)
    if got != EXPECTED_SHA256:
        print(f"copy mismatch: {got} != {EXPECTED_SHA256}", file=sys.stderr)
        return 1

    print(f"wrote {target} ({target.stat().st_size} bytes, sha256 {got})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

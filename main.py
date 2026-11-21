"""Deliver the pre-rendered passport spread image.

The artwork is rendered ahead of time and shipped as ``entry.png`` next to
this program.  Running the program simply places a verified copy of that
image into the output directory.  It uses only the Python standard library,
so it works in a bare sandbox with no third-party packages installed.
"""

import hashlib
import os
import shutil
import sys
from pathlib import Path

SOURCE_NAME = "entry.png"
EXPECTED_SHA256 = "cca9d22b3bf63584835199e54c1670b91b209422285ddd04d309c0083663e732"
DEFAULT_OUTPUT_DIR = "/output"


def sha256_of(path):
    """Return the SHA-256 hex digest of a file, streamed in blocks."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def fail(message):
    """Print an error message and exit with a non-zero status."""
    print("error: {}".format(message), file=sys.stderr)
    return 1


def main():
    source = Path(__file__).resolve().parent / SOURCE_NAME
    if not source.is_file():
        return fail("source image not found: {}".format(source))
    if source.stat().st_size == 0:
        return fail("source image is empty: {}".format(source))

    out_dir = Path(os.environ.get("OUTPUT_DIR", DEFAULT_OUTPUT_DIR))
    out_dir.mkdir(parents=True, exist_ok=True)

    destination = out_dir / SOURCE_NAME
    shutil.copyfile(source, destination)

    copied_hash = sha256_of(destination)
    if copied_hash != EXPECTED_SHA256:
        return fail(
            "checksum mismatch for {}: got {}, expected {}".format(
                destination, copied_hash, EXPECTED_SHA256
            )
        )

    size = destination.stat().st_size
    print("wrote {} ({} bytes, sha256 {})".format(destination, size, copied_hash))
    return 0


if __name__ == "__main__":
    sys.exit(main())

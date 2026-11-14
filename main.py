#!/usr/bin/env python3
"""news-image-01 v2 entrypoint.

Ships the bundled broadsheet front page (entry.png) to the grader's
output directory, byte for byte, after checking the file is a
well-formed PNG inside the competition's size limits.

The output directory is $MAKEFUN_OUTPUT_DIR when set, otherwise the
absolute path /output (never a relative path, so the runner cannot
silently write somewhere unexpected).

Stdlib only.
"""

import hashlib
import os
import shutil
import struct
import sys
from pathlib import Path

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1_048_576          # competition limit: PNG <= 1 MiB
MAX_SIDE = 1024                # competition limit: 1024 x 1024 max


def png_dimensions(data):
    """Return (width, height) from the IHDR chunk of a PNG byte string."""
    if data[:8] != PNG_MAGIC:
        raise ValueError("not a PNG file (bad signature)")
    # IHDR is the first chunk: 4-byte length, 4-byte type, 13 bytes of
    # data, 4-byte CRC, starting at offset 8. Width and height are the
    # first 8 bytes of the IHDR data, big-endian.
    if len(data) < 24 or data[12:16] != b"IHDR":
        raise ValueError("PNG has no IHDR chunk where expected")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def main():
    here = Path(__file__).resolve().parent
    source = here / "entry.png"
    data = source.read_bytes()

    if len(data) > MAX_BYTES:
        print(f"entry too large: {len(data)} bytes (limit {MAX_BYTES})",
              file=sys.stderr)
        return 1
    try:
        width, height = png_dimensions(data)
    except ValueError as exc:
        print(f"invalid entry.png: {exc}", file=sys.stderr)
        return 1
    if width > MAX_SIDE or height > MAX_SIDE:
        print(f"entry too large: {width}x{height} "
              f"(limit {MAX_SIDE}x{MAX_SIDE})", file=sys.stderr)
        return 1

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    out_path = Path(out_dir)
    if not out_path.is_absolute():
        print(f"MAKEFUN_OUTPUT_DIR must be absolute, got {out_dir!r}",
              file=sys.stderr)
        return 1
    out_path.mkdir(parents=True, exist_ok=True)
    target = out_path / "entry.png"

    # Byte-exact copy: no re-encoding, the PNG bytes travel untouched.
    shutil.copyfile(source, target)

    digest = hashlib.sha256(data).hexdigest()
    copied = hashlib.sha256(target.read_bytes()).hexdigest()
    if copied != digest:
        print(f"copy mismatch: {copied} != {digest}", file=sys.stderr)
        return 1

    print(f"copied {source} -> {target}")
    print(f"dimensions: {width}x{height}")
    print(f"bytes: {len(data)} (limit {MAX_BYTES})")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

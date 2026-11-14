#!/usr/bin/env python3
"""news-image-01 entry point.

Copies ``entry.png`` (the broadsheet front page for Friday 13 November
2026) from this directory into the output directory.

The output directory defaults to the ABSOLUTE path ``/output`` and can be
overridden with the ``MAKEFUN_OUTPUT_DIR`` environment variable.  A relative
``out`` was a past failure mode in another make.fun entry (the runner
crashed because the relative directory did not exist), so the default here
is deliberately absolute.

Stdlib only.  Python 3.13.
"""

import hashlib
import os
import shutil
import struct
import sys
import zlib
from pathlib import Path

MAX_BYTES = 1_048_576          # competition limit: PNG <= 1 MiB
MAX_SIDE = 1024                # competition limit: 1024 x 1024 max
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def validate_png(path: Path) -> tuple[int, int, int]:
    """Check the file is a structurally valid PNG within the limits.

    Returns (width, height, size_in_bytes).  Raises SystemExit on failure.
    """
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        sys.exit(f"entry too large: {len(data)} bytes (limit {MAX_BYTES})")
    if data[:8] != PNG_SIGNATURE:
        sys.exit("entry.png is not a PNG file")
    # Walk the chunks, verifying CRCs, and read the IHDR dimensions.
    pos = 8
    width = height = None
    while pos < len(data):
        if pos + 12 > len(data):
            sys.exit("truncated PNG chunk header")
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        crc_stored = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])[0]
        crc_calc = zlib.crc32(ctype + payload) & 0xFFFFFFFF
        if crc_stored != crc_calc:
            sys.exit(f"bad CRC in PNG chunk {ctype!r}")
        if ctype == b"IHDR":
            width, height = struct.unpack(">II", payload[:8])
        pos += 12 + length
        if ctype == b"IEND":
            break
    if width is None:
        sys.exit("PNG has no IHDR chunk")
    if width > MAX_SIDE or height > MAX_SIDE:
        sys.exit(f"entry too large: {width}x{height} (limit {MAX_SIDE}x{MAX_SIDE})")
    return width, height, len(data)


def main() -> int:
    here = Path(__file__).resolve().parent
    src = here / "entry.png"
    if not src.is_file():
        print(f"error: {src} not found", file=sys.stderr)
        return 1

    width, height, size = validate_png(src)
    sha = hashlib.sha256(src.read_bytes()).hexdigest()

    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    if not out_dir.is_absolute():
        # A relative output dir depends on the caller's cwd; refuse it
        # rather than silently writing somewhere unexpected.
        print(f"error: MAKEFUN_OUTPUT_DIR must be absolute, got {out_dir!r}",
              file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / "entry.png"
    shutil.copyfile(src, dst)

    # Verify the copy byte-for-byte: a truncated or corrupted copy must
    # fail loudly here, not surface later as a rejected submission.
    copied_sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    if copied_sha != sha:
        print(f"error: copy mismatch: {copied_sha} != {sha}", file=sys.stderr)
        return 1

    print(f"copied {src} -> {dst}")
    print(f"dimensions: {width}x{height}")
    print(f"bytes: {size} (limit {MAX_BYTES})")
    print(f"sha256: {sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

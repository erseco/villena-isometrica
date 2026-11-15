"""Check that the committed fixtures are what scripts/make_fixtures.py produces. Stdlib only.

Regenerates into a temporary directory and compares by content, not by bytes (docs/contracts/render.md §1 and
scene.md "Rules"): JSON after parsing, numbers within 1e-9 relative; PNG by decoded pixels; other files exactly.
File hashes recorded inside JSON are skipped, because they are a property of one toolchain: a least-squares fit or
a zlib build can differ in the last bits between macOS and Linux. `pixelSha256` is compared.
"""
import json
import math
import os
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLCHAIN_HASHES = {"sha256", "sceneSha256", "renderSha256"}


def png_pixels(data: bytes):
    """(IHDR, PLTE, decompressed scanlines) of a PNG."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos, parts, idat = 8, {}, b""
    while pos < len(data):
        length, tag = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if tag == b"IDAT":
            idat += body
        else:
            parts[tag] = body
        pos += 12 + length
    return parts.get(b"IHDR"), parts.get(b"PLTE"), zlib.decompress(idat)


def differences(a, b, where=""):
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            return [f"{where}: keys differ {sorted(a.keys() ^ b.keys())}"]
        return [d for k in a if k not in TOOLCHAIN_HASHES for d in differences(a[k], b[k], f"{where}/{k}")]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{where}: length {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in differences(x, y, f"{where}/{i}")]
    if isinstance(a, float) or isinstance(b, float):
        ok = isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
        return [] if ok else [f"{where}: {a!r} != {b!r}"]
    return [] if a == b else [f"{where}: {a!r} != {b!r}"]


def main():
    committed = ROOT / "tests" / "fixtures"
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["uv", "run", "--quiet", str(ROOT / "scripts" / "make_fixtures.py")], check=True,
                       env={**os.environ, "FIXTURES_OUT": tmp}, stdout=subprocess.DEVNULL)
        fresh = Path(tmp)
        names = {p.relative_to(committed).as_posix() for p in committed.rglob("*") if p.is_file()}
        fresh_names = {p.relative_to(fresh).as_posix() for p in fresh.rglob("*") if p.is_file()}
        problems = [f"only committed: {n}" for n in sorted(names - fresh_names)]
        problems += [f"only generated: {n}" for n in sorted(fresh_names - names)]
        for name in sorted(names & fresh_names):
            a, b = (committed / name).read_bytes(), (fresh / name).read_bytes()
            if a == b:
                continue
            if name.endswith(".json"):
                problems += differences(json.loads(a), json.loads(b), name)
            elif name.endswith(".png"):
                problems += [] if png_pixels(a) == png_pixels(b) else [f"{name}: pixels differ"]
            else:
                problems.append(f"{name}: bytes differ")
    for p in problems[:40]:
        print("fixtures:", p)
    print("fixtures match the generator" if not problems else f"{len(problems)} difference(s): run `make fixtures` "
          "(architect only) or revert the hand edit")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

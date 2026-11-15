"""Pack a validated tile directory into a reproducible .tar.gz and print its tiles.lock.json entry.

PYTHONPATH=pipeline uv run --project pipeline python -m export.pack <tiles dir> --out <file.tar.gz>

Sorted entries, regular files only, mtime/uid/gid zeroed, fixed modes, no owner names, gzip header with
mtime 0 and no file name. Same input and same zlib -> same sha256.
"""

import argparse
import gzip
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

from export.validate import FIXTURE_ORACLE, validate


def pack(root: Path, out: Path) -> dict:
    errors, _ = validate(root)
    if (root / FIXTURE_ORACLE).exists():
        errors.append(f"{root / FIXTURE_ORACLE}: test oracle must not be published")
    if errors:
        raise ValueError("refusing to pack an invalid tile directory:\n  " + "\n  ".join(errors))
    files = sorted((p.relative_to(root).as_posix(), p) for p in root.rglob("*") if p.is_file())
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as gz, \
            tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name, path in files:
            data = path.read_bytes()
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    manifest = json.loads((root / "manifest.json").read_text())
    return {"release": manifest["release"], "asset": out.name,
            "sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "sizeBytes": out.stat().st_size}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tiles", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        lock = pack(args.tiles, args.out)
    except (OSError, ValueError) as e:
        print(f"export.pack: {e}", file=sys.stderr)
        return 1
    print(f"{args.out}: sha256 {lock['sha256']}, {lock['sizeBytes']} bytes")
    print("tiles.lock.json:")
    print(json.dumps(lock, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

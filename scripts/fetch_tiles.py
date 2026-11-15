"""Download, verify and safely extract a pinned GitHub release tile archive."""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", required=True)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.city):
        parser.error("invalid city id")
    lock_path = ROOT / "cities" / args.city / "tiles.lock.json"
    if not lock_path.is_file():
        print(f"Missing {lock_path}; create it with export.pack and WP12 release integration.", file=sys.stderr)
        return 2
    if not args.repo or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        parser.error("--repo owner/name or GITHUB_REPOSITORY is required")
    try:
        lock = json.loads(lock_path.read_text())
        release, asset, expected, length = (lock[k] for k in ("release", "asset", "sha256", "sizeBytes"))
        if (not isinstance(release, str) or not release or not isinstance(asset, str) or not asset
                or not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected)
                or not isinstance(length, int) or isinstance(length, bool) or length < 1):
            raise ValueError("invalid lock fields")
        url = f"https://github.com/{args.repo}/releases/download/{urllib.parse.quote(release, safe='')}/{urllib.parse.quote(asset, safe='')}"
        dest = ROOT / "apps" / "viewer" / "public" / "tiles" / args.city
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
            archive = Path(tmp) / "tiles.tar.gz"
            digest = hashlib.sha256()
            count = 0
            with urllib.request.urlopen(url) as response, archive.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > length:
                        raise ValueError("asset exceeds pinned size")
                    digest.update(chunk)
                    output.write(chunk)
            if count != length or digest.hexdigest() != expected:
                raise ValueError("asset size or SHA-256 does not match lock")
            unpacked = Path(tmp) / "unpacked"
            unpacked.mkdir()
            with tarfile.open(archive, "r:gz") as tar:
                for member in tar.getmembers():
                    path = PurePosixPath(member.name)
                    if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
                        raise ValueError(f"unsafe archive member: {member.name}")
                for member in tar.getmembers():
                    target = unpacked.joinpath(*PurePosixPath(member.name).parts)
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with tar.extractfile(member) as source, target.open("wb") as output:
                            shutil.copyfileobj(source, output)
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(unpacked), str(dest))
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError) as exc:
        print(f"fetch tiles: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

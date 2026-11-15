"""Download and verify the datasets listed in a city's dataset manifest.

uv run --project pipeline python -m acquisition.fetch --city cities/villena/city.json [--only <id>] [--data-root .]

- Only datasets listed in the manifest are ever fetched.
- A file whose pinned sha256 or size does not match is an error; it is never replaced and accepted.
- Datasets with `access: manual` are never downloaded (the IGN Centro de Descargas is reCAPTCHA-protected);
  the command checks them and points to cities/<city>/ACQUISITION.md.
- A dataset whose sha256 is null is downloaded and its checksum printed so it can be pinned. The scene build
  refuses unpinned inputs.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from geospatial.inputs import sha256_file

USER_AGENT = "villena-isometrica-pipeline/0.1"
SCHEMES = ("https://", "http://", "file://")


class FetchError(Exception):
    pass


def download(url: str, dest: Path, timeout: float = 60.0, retries: int = 1) -> None:
    if not url.startswith(SCHEMES):
        raise FetchError(f"refusing URL scheme: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp, dest.open("wb") as out:
                while chunk := resp.read(1 << 20):
                    out.write(chunk)
            return
        except (urllib.error.URLError, TimeoutError) as e:
            dest.unlink(missing_ok=True)
            if attempt == retries:
                raise FetchError(f"download failed: {url}: {e}") from e
            time.sleep(5)


def check(entry: dict, path: Path) -> str:
    """Verify size and checksum of a present file. Returns its sha256."""
    size = path.stat().st_size
    if entry.get("sizeBytes") is not None and size != entry["sizeBytes"]:
        raise FetchError(f"{entry['id']}: {path} is {size} bytes, manifest says {entry['sizeBytes']}")
    digest = sha256_file(path)
    if entry.get("sha256") is not None and digest != entry["sha256"]:
        raise FetchError(f"{entry['id']}: {path} sha256 {digest} != pinned {entry['sha256']}")
    return digest


def fetch_one(entry: dict, data_root: Path, city_dir: Path) -> str:
    path = data_root / entry["localPath"]
    if entry["access"] == "manual" and not path.exists():
        raise FetchError(f"{entry['id']}: manual download required; follow {city_dir / 'ACQUISITION.md'} "
                         f"and save the file as {path}")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_name(path.name + ".part")
        download(entry["url"], part)
        try:
            check(entry, part)
        except FetchError:
            part.unlink(missing_ok=True)
            raise
        part.rename(path)
    digest = check(entry, path)
    if entry.get("sha256") is None:
        return f"UNPINNED {entry['id']}: sha256 {digest}, {path.stat().st_size} bytes — pin these in the manifest"
    return f"ok {entry['id']}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--city", type=Path, required=True)
    ap.add_argument("--only", action="append", help="dataset id (repeatable)")
    ap.add_argument("--data-root", type=Path, default=Path("."))
    args = ap.parse_args(argv)
    city = json.loads(args.city.read_text())
    manifest = json.loads((args.city.parent / city["datasets"]).read_text())
    entries = sorted(manifest["datasets"], key=lambda d: d["id"])
    if args.only:
        unknown = set(args.only) - {d["id"] for d in entries}
        if unknown:
            print(f"error: not in the manifest: {sorted(unknown)}", file=sys.stderr)
            return 1
        entries = [d for d in entries if d["id"] in args.only]
    failed = False
    for entry in entries:
        try:
            print(fetch_one(entry, args.data_root, args.city.parent))
        except FetchError as e:
            failed = True
            print(f"error: {e}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

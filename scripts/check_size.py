"""Check the total and individual file sizes of a site directory."""
import argparse
import tempfile
from pathlib import Path


def size(value):
    value = value.upper()
    for suffix, multiplier in (("GB", 1000**3), ("MB", 1000**2), ("KB", 1000), ("B", 1)):
        if value.endswith(suffix):
            return int(value[:-len(suffix)]) * multiplier
    return int(value)


def check(directory, max_total, max_file):
    if not directory.is_dir():
        raise ValueError(f"not a directory: {directory}")
    files = sorted(((p.stat().st_size, p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()), reverse=True)
    total = sum(n for n, _ in files)
    print(f"Total: {total} bytes")
    print("Largest files:")
    for n, path in files[:10]:
        print(f"  {n:>12}  {path}")
    print("By top-level directory:")
    groups = {}
    for n, path in files:
        key = path.parts[0] if len(path.parts) > 1 else "."
        groups[key] = groups.get(key, 0) + n
    for key, n in sorted(groups.items()):
        print(f"  {n:>12}  {key}")
    return total <= max_total and all(n <= max_file for n, _ in files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path)
    parser.add_argument("--max-total", type=size, default=size("250MB"))
    parser.add_argument("--max-file", type=size, default=size("25MB"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "file").write_bytes(b"1234")
            assert check(root, 4, 4)
            assert not check(root, 3, 4)
            assert not check(root, 4, 3)
        print("Self-test passed")
        return 0
    if args.directory is None:
        parser.error("directory is required")
    try:
        return 0 if check(args.directory, args.max_total, args.max_file) else 1
    except (OSError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

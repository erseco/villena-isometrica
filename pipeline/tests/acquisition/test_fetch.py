import hashlib
import json

import pytest

from acquisition import fetch


def setup(tmp_path, *, sha="right", access="direct", size=True):
    src = tmp_path / "server" / "file.bin"
    src.parent.mkdir()
    src.write_bytes(b"geodata" * 100)
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    entry = {"id": "ds", "url": src.as_uri(), "access": access, "localPath": "raw/ds/file.bin",
             "sizeBytes": 700 if size else None,
             "sha256": {"right": digest, "wrong": "0" * 64, "none": None}[sha]}
    city_dir = tmp_path / "city"
    city_dir.mkdir()
    (city_dir / "city.json").write_text(json.dumps({"datasets": "datasets.json"}))
    (city_dir / "datasets.json").write_text(json.dumps({"datasets": [entry]}))
    data = tmp_path / "data"
    return city_dir / "city.json", data, data / "raw/ds/file.bin"


def run(city, data, *extra):
    return fetch.main(["--city", str(city), "--data-root", str(data), *extra])


def test_downloads_and_verifies(tmp_path, capsys):
    city, data, dest = setup(tmp_path)
    assert run(city, data) == 0
    assert dest.read_bytes() == b"geodata" * 100
    assert "ok ds" in capsys.readouterr().out


def test_checksum_mismatch_on_download_leaves_nothing(tmp_path):
    city, data, dest = setup(tmp_path, sha="wrong")
    assert run(city, data) == 1
    assert not dest.exists() and not dest.with_name(dest.name + ".part").exists()


def test_tampered_local_file_is_refused_not_replaced(tmp_path):
    city, data, dest = setup(tmp_path)
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"tampered" + b"x" * 692)
    assert run(city, data) == 1
    assert dest.read_bytes().startswith(b"tampered")


def test_unpinned_is_saved_and_reported(tmp_path, capsys):
    city, data, dest = setup(tmp_path, sha="none", size=False)
    assert run(city, data) == 0
    out = capsys.readouterr().out
    assert dest.exists() and "UNPINNED ds" in out
    assert hashlib.sha256(dest.read_bytes()).hexdigest() in out


def test_manual_dataset_is_never_downloaded(tmp_path, capsys):
    city, data, dest = setup(tmp_path, access="manual")
    assert run(city, data) == 1
    assert not dest.exists()
    assert "ACQUISITION.md" in capsys.readouterr().err


def test_only_rejects_unknown_ids(tmp_path):
    city, data, _ = setup(tmp_path)
    assert run(city, data, "--only", "not-listed") == 1


def test_refuses_other_schemes(tmp_path):
    with pytest.raises(fetch.FetchError):
        fetch.download("ftp://example.invalid/x", tmp_path / "x")

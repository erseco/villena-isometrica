# acquisition — fetch and verify datasets

```sh
uv run --project pipeline python -m acquisition.fetch --city cities/villena/city.json [--only <id>] [--data-root .]
```

For every entry in `cities/<city>/datasets.json` (or only the `--only` ids):

| `access` | File absent | File present |
|---|---|---|
| `direct`, `ogc-service` | download `url` to `<data-root>/<localPath>.part`, verify, rename | verify |
| `manual` | error pointing to `cities/<city>/ACQUISITION.md` (never downloaded) | verify |

Verification = size (if `sizeBytes` is set) and sha256 (if pinned). A mismatch is an error; the
file is never replaced. An unpinned entry is downloaded and reported as `UNPINNED` with its
checksum and size, to be copied into the manifest; `geospatial.build_scene` refuses unpinned
inputs. Only `https`, `http` and `file` URLs; generic User-Agent; 60 s timeout, one retry.

Archives are not extracted: the scene build reads the Catastro zip in place.

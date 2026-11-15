# data/

Local, git-ignored working data. Nothing in this directory is committed except this file.

```
data/raw/<dataset-id>/      downloads, exactly as received (ids from cities/<city>/datasets.json)
data/interim/<city>/        clipped and reprojected intermediates
```

Rules:

- Every file in `data/raw/` must be listed in a dataset manifest with its sha256; acquisition
  scripts verify the checksum before use and never download something that is not listed.
- IGN elevation models must be downloaded by hand once (the Centro de Descargas is protected
  by reCAPTCHA; do not try to automate it). `cities/villena/datasets.json` says which files
  and where to put them.
- Raw Catastro data may not be redistributed: never copy it into Git, a release or the site.
- Build outputs go to `build/`, not here.

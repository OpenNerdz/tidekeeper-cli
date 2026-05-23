# Maintaining this fork

This fork is intended for maintenance, packaging, and compatibility work around
the Python app published as `tidekeeper`.

## Scope

- Keep installation, packaging, terminal startup, and GUI startup working on supported Python versions.
- Improve reliability around authenticated API requests, retries, timeouts, partial files, and error reporting.
- Keep CI green for import, compile, terminal, and GUI smoke tests.
- Do not add behavior intended to bypass access controls, subscription checks, or DRM.

## Local development

```bash
cd TIDALDL-PY
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m compileall -q tidal_dl
python -m tidal_dl --help
tidekeeper --help
```

## Build

```bash
./build.sh
```

Build outputs are written under `TIDALDL-PY/dist` and `TIDALDL-PY/exe`.

## Release checklist

1. Update the version in `TIDALDL-PY/tidal_dl/printf.py`.
2. Run the local development checks.
3. Confirm GitHub Actions CI passes.
4. Build artifacts with `./build.sh`.
5. Upload distributions only after reviewing the generated files.

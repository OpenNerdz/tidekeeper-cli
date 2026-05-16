#!/usr/bin/env bash
set -euo pipefail

cd TIDALDL-PY
rm -rf build dist exe MANIFEST.in *.egg-info __init__.spec tidekeeper.spec

python -m pip install --upgrade build pyinstaller
python -m build
pyinstaller -F tidal_dl/__main__.py -n tidekeeper

mkdir -p exe
if [[ -f dist/tidekeeper.exe ]]; then
  mv dist/tidekeeper.exe exe/tidekeeper.exe
else
  mv dist/tidekeeper exe/tidekeeper
fi

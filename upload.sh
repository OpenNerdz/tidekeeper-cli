#!/usr/bin/env bash
set -euo pipefail

cd TIDALDL-PY
python -m twine upload dist/*

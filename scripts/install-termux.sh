#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

pkg update
pkg install -y python git ffmpeg clang libxml2 libxslt

python -m pip install --upgrade pip wheel
python -m pip install "git+https://github.com/OpenNerdz/tidekeeper-cli.git#subdirectory=TIDALDL-PY"

cat <<'MSG'

Tidekeeper CLI is installed.

Run:
  tidekeeper

Optional Android storage access:
  termux-setup-storage

After granting storage access, set the Tidekeeper save folder to:
  /storage/emulated/0/Download/Tidekeeper

MSG

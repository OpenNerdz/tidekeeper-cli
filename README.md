# Tidekeeper CLI

Tidekeeper CLI is an unofficial maintained fork of
[yaronzz/Tidal-Media-Downloader](https://github.com/yaronzz/Tidal-Media-Downloader),
focused on keeping the Python command-line tool installable, testable, and usable
on current Python versions.

The CLI is available as both `tidekeeper` and the legacy-compatible `tidal-dl`.

[![CI](https://github.com/OpenNerdz/tidekeeper-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/OpenNerdz/tidekeeper-cli/actions/workflows/ci.yml)
[![Build exe](https://github.com/OpenNerdz/tidekeeper-cli/actions/workflows/build.yml/badge.svg)](https://github.com/OpenNerdz/tidekeeper-cli/actions/workflows/build.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

## Scope

- Maintain the Python CLI fork with modern packaging and CI.
- Improve install reliability, authenticated API requests, retries, partial files,
  timeouts, and error reporting.
- Keep compatibility with existing `tidal-dl` workflows where practical.

This project does not aim to bypass access controls, subscription checks, or DRM.

## Install

```bash
python -m pip install "git+https://github.com/OpenNerdz/tidekeeper-cli.git#subdirectory=TIDALDL-PY"
```

Linux one-command installer:

```bash
curl -fsSL https://raw.githubusercontent.com/OpenNerdz/tidekeeper-cli/main/install.sh | bash
```

Then run:

```bash
tidekeeper
```

## Termux

Termux support is for the CLI install path only.

```bash
pkg update && pkg upgrade -y && pkg install -y curl
curl -fsSL https://raw.githubusercontent.com/OpenNerdz/tidekeeper-cli/main/install.sh | bash
tidekeeper
```

To save downloads to Android shared storage:

```bash
termux-setup-storage
export TIDEKEEPER_DOWNLOAD_PATH="/storage/emulated/0/Download/Tidekeeper"
```

If `ffmpeg` fails with `cannot locate symbol "x265_api_get_216"`, your Termux
packages are mismatched. Run:

```bash
pkg update
pkg upgrade -y
pkg reinstall -y ffmpeg x265
ffmpeg -version
```

If it still fails, run `termux-change-repo`, switch mirrors, then repeat the
commands above.

## Usage

```bash
tidekeeper --help
tidekeeper
tidekeeper -l "https://tidal.com/browse/track/70973230"
```

Legacy command:

```bash
tidal-dl --help
```

## Development

```bash
git clone https://github.com/OpenNerdz/tidekeeper-cli.git
cd tidekeeper-cli/TIDALDL-PY
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m compileall -q tidal_dl
python -m unittest discover -s tests
```

## Build

```bash
./build.sh
```

Build outputs are written under `TIDALDL-PY/dist` and `TIDALDL-PY/exe`.

## Attribution

This project is based on `yaronzz/Tidal-Media-Downloader`, originally authored
by YaronH and contributors. The original project is licensed under Apache-2.0.
See [NOTICE](NOTICE) and [LICENSE](LICENSE).

## Disclaimer

This project is unofficial and is not affiliated with, endorsed by, or sponsored
by TIDAL or Block, Inc. Use it only where you have the right to do so, and follow
the laws and service terms that apply in your location.

# Tidekeeper CLI

Tidekeeper CLI is an unofficial maintained fork of
[yaronzz/Tidal-Media-Downloader](https://github.com/yaronzz/Tidal-Media-Downloader),
focused on keeping the Python command-line tool installable, testable, and usable
on current Python versions.

The command-line interface is available as both `tidekeeper` and the compatible
legacy alias `tidal-dl`.

[![CI](https://github.com/opennerd-cmyk/tidekeeper-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/opennerd-cmyk/tidekeeper-cli/actions/workflows/ci.yml)
[![Build exe](https://github.com/opennerd-cmyk/tidekeeper-cli/actions/workflows/build.yml/badge.svg)](https://github.com/opennerd-cmyk/tidekeeper-cli/actions/workflows/build.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

## Project goals

- Maintain the Python CLI fork with modern packaging and CI.
- Improve reliability around authenticated API requests, partial files, retries,
  timeouts, and error reporting.
- Keep compatibility with existing `tidal-dl` workflows where practical.
- Preserve clear attribution to the upstream Apache-2.0 project.

This fork does not aim to bypass access controls, subscription checks, or DRM.

## Install from GitHub

```bash
python -m pip install "git+https://github.com/opennerd-cmyk/tidekeeper-cli.git#subdirectory=TIDALDL-PY"
```

For local development:

```bash
git clone https://github.com/opennerd-cmyk/tidekeeper-cli.git
cd tidekeeper-cli/TIDALDL-PY
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Usage

```bash
tidekeeper --help
tidekeeper
tidekeeper -l "https://tidal.com/browse/track/70973230"
```

The legacy command remains available:

```bash
tidal-dl --help
```

## Features inherited from upstream

- Download album, track, video, playlist, and artist album entries.
- Add metadata to downloaded files.
- Select audio quality and video resolution.
- Save album information, covers, and optional lyric files.

## Format tags

### Album

| Tag | Example value |
| --- | --- |
| `{ArtistName}` | The Beatles |
| `{AlbumArtistName}` | The Beatles |
| `{Flag}` | M/A/E |
| `{AlbumID}` | 55163243 |
| `{AlbumYear}` | 1963 |
| `{AlbumTitle}` | Please Please Me (Remastered) |
| `{AudioQuality}` | LOSSLESS |
| `{DurationSeconds}` | 1919 |
| `{Duration}` | 31:59 |
| `{NumberOfTracks}` | 14 |
| `{NumberOfVideos}` | 0 |
| `{NumberOfVolumes}` | 1 |
| `{ReleaseDate}` | 1963-03-22 |
| `{RecordType}` | ALBUM |
| `{None}` | |

### Track

| Tag | Example value |
| --- | --- |
| `{TrackNumber}` | 01 |
| `{ArtistName}` | The Beatles |
| `{ArtistsName}` | The Beatles |
| `{TrackTitle}` | I Saw Her Standing There (Remastered 2009) |
| `{ExplicitFlag}` | (Explicit) |
| `{AlbumYear}` | 1963 |
| `{AlbumTitle}` | Please Please Me (Remastered) |
| `{AudioQuality}` | LOSSLESS |
| `{DurationSeconds}` | 173 |
| `{Duration}` | 02:53 |
| `{TrackID}` | 55163244 |

### Video

| Tag | Example value |
| --- | --- |
| `{VideoNumber}` | 00 |
| `{ArtistName}` | DMX |
| `{ArtistsName}` | DMX, Westside Gunn |
| `{VideoTitle}` | Hood Blues |
| `{ExplicitFlag}` | (Explicit) |
| `{VideoYear}` | 2021 |
| `{VideoID}` | 188932980 |

## Development checks

```bash
cd TIDALDL-PY
python -m compileall -q tidal_dl
python -m tidal_dl --help
tidekeeper --help
tidal-dl --help
```

## Build

```bash
./build.sh
```

Build outputs are written under `TIDALDL-PY/dist` and `TIDALDL-PY/exe`.

## Upstream attribution

This project is based on `yaronzz/Tidal-Media-Downloader`, originally authored
by YaronH and contributors. The original project is licensed under Apache-2.0.
See [NOTICE](NOTICE) and [LICENSE](LICENSE).

Reference projects listed by upstream:

- [aigpy](https://github.com/yaronzz/AIGPY)
- [python-tidal](https://github.com/tamland/python-tidal)
- [redsea](https://github.com/RedSudo/RedSea)
- [tidal-wiki](https://github.com/Fokka-Engineering/TIDAL/wiki)

## Disclaimer

This project is unofficial and is not affiliated with, endorsed by, or sponsored
by TIDAL or Block, Inc. Use it only where you have the right to do so, and follow
the laws and service terms that apply in your location.

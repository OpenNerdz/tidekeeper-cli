# Changelog

## Unreleased

- Added in-app update actions for the terminal workflow and desktop GUI.
- Added a GUI fallback-order preset selector for audio quality priority.
- Reorganized GUI pages into clearer workflow sections for faster scanning.
- Improved GUI account maintenance layout and guarded against duplicate background actions.
- Fixed sorted GUI tables so selected search and queue rows resolve the intended item.

## 2026.5.23.0 - 2026-05-23

- Fall back through lower audio qualities when a requested stream manifest is blocked or unavailable, and show the fallback in track output.
- Added `tidekeeper --doctor` to check config, token status, download path access, and local tools.
- Added the modern PySide6 desktop GUI with feature parity for terminal auth, search, queue, direct downloads, settings, client selection, token login, and doctor diagnostics.
- Added automated GUI screenshot smoke testing with dense demo data for layout validation.
- Added cross-platform GUI executable builds and release uploads for Windows, Linux, and macOS.

## 2026.5.17.4 - 2026-05-18

- Added `SECURITY.md`, `CONTRIBUTING.md`, and release changelog docs.
- Linked project governance docs from the README.
- Restricted local token file permissions to owner-only on POSIX systems.
- Improved parsing for TIDAL share URLs with query strings, fragments, and nested paths.
- Added regression coverage for URL parsing and token file permissions.

## 2026.5.17.3 - 2026-05-18

- Added Dolby Atmos stream support and Atmos filename identification.
- Added `failed-tracks.txt` logging for failed track downloads.
- Improved Termux install and first-run behavior.
- Added the one-command Linux/Termux installer.
- Fixed the lyrics endpoint.
- Hardened terminal auth and path handling.
- Refreshed README branding and repository maintenance files.

## 2026.5.16.7 - 2026-05-16

- Fixed executable workflow dependencies.

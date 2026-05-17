#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${TIDEKEEPER_REPO_URL:-https://github.com/OpenNerdz/tidekeeper-cli.git}"
PACKAGE_SUBDIR="TIDALDL-PY"
INSTALL_ROOT="${TIDEKEEPER_INSTALL_ROOT:-$HOME/.local/share/tidekeeper-cli}"
BIN_DIR="${TIDEKEEPER_BIN_DIR:-$HOME/.local/bin}"

has_command() {
    command -v "$1" >/dev/null 2>&1
}

is_termux() {
    [[ "${PREFIX:-}" == /data/data/com.termux/files/usr* ]] || [[ -n "${TERMUX_VERSION:-}" ]]
}

run_as_root() {
    if [[ "$(id -u)" -eq 0 ]]; then
        "$@"
    elif has_command sudo; then
        sudo "$@"
    else
        return 1
    fi
}

install_termux_dependencies() {
    pkg update
    pkg install -y python git ffmpeg clang libxml2 libxslt
}

install_linux_dependencies() {
    if [[ "$(id -u)" -ne 0 ]] && ! has_command sudo; then
        echo "sudo is not available. Skipping system dependency install and trying Python install."
        return 0
    fi

    if has_command apt-get; then
        run_as_root apt-get update
        run_as_root apt-get install -y python3 python3-pip python3-venv git ffmpeg gcc libxml2-dev libxslt1-dev
    elif has_command dnf; then
        run_as_root dnf install -y python3 python3-pip git ffmpeg gcc libxml2-devel libxslt-devel
    elif has_command pacman; then
        run_as_root pacman -Sy --needed --noconfirm python python-pip git ffmpeg gcc libxml2 libxslt
    elif has_command apk; then
        run_as_root apk add --no-cache python3 py3-pip git ffmpeg gcc musl-dev libxml2-dev libxslt-dev
    elif has_command zypper; then
        run_as_root zypper --non-interactive install python3 python3-pip git ffmpeg gcc libxml2-devel libxslt-devel
    else
        echo "No supported package manager found. Skipping system dependency install."
    fi
}

python_command() {
    if has_command python3; then
        command -v python3
    elif has_command python; then
        command -v python
    else
        echo "Python was not found after installing dependencies." >&2
        exit 1
    fi
}

package_source() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    if [[ -f "$script_dir/$PACKAGE_SUBDIR/setup.py" ]]; then
        echo "$script_dir/$PACKAGE_SUBDIR"
    else
        echo "git+$REPO_URL#subdirectory=$PACKAGE_SUBDIR"
    fi
}

install_termux_package() {
    local python source
    python="$(python_command)"
    source="$(package_source)"

    "$python" -m pip install --upgrade pip wheel
    "$python" -m pip install --upgrade "$source"
}

install_linux_package() {
    local python source venv_python
    python="$(python_command)"
    source="$(package_source)"

    mkdir -p "$INSTALL_ROOT" "$BIN_DIR"
    "$python" -m venv "$INSTALL_ROOT/venv"
    venv_python="$INSTALL_ROOT/venv/bin/python"

    "$venv_python" -m pip install --upgrade pip wheel
    "$venv_python" -m pip install --upgrade "$source"

    ln -sf "$INSTALL_ROOT/venv/bin/tidekeeper" "$BIN_DIR/tidekeeper"
    ln -sf "$INSTALL_ROOT/venv/bin/tidal-dl" "$BIN_DIR/tidal-dl"
}

print_done() {
    cat <<MSG

Tidekeeper CLI is installed.

Run:
  tidekeeper

If the command is not found, add this to your shell profile:
  export PATH="\$HOME/.local/bin:\$PATH"

Termux storage access, optional:
  termux-setup-storage

Recommended Android downloads folder:
  /storage/emulated/0/Download/Tidekeeper

MSG
}

main() {
    if is_termux; then
        install_termux_dependencies
        install_termux_package
    else
        install_linux_dependencies || {
            echo "Could not install system dependencies automatically."
            echo "Install Python, pip, git, ffmpeg, gcc, libxml2, and libxslt, then re-run this script."
            exit 1
        }
        install_linux_package
    fi

    print_done
}

main "$@"

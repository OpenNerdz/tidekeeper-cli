from __future__ import annotations

import os
import sys

from tidal_dl.gui_app.backend import DemoBackend, TidekeeperBackend


def main():
    try:
        from tidal_dl.gui_app.main_window import run_app
    except ImportError as exc:
        print(
            "Tidekeeper GUI requires PySide6. Install it with:\n"
            "  python -m pip install 'tidekeeper[gui]'\n"
            "or from this checkout:\n"
            "  python -m pip install -e '.[gui]'",
            file=sys.stderr,
        )
        print(f"\nImport error: {exc}", file=sys.stderr)
        return 1

    backend = DemoBackend() if os.environ.get("TIDEKEEPER_GUI_DEMO") == "1" else TidekeeperBackend()
    return run_app(backend)


if __name__ == "__main__":
    raise SystemExit(main())

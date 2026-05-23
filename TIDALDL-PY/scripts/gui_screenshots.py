#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _is_nonblank(image) -> bool:
    width = image.width()
    height = image.height()
    if width < 800 or height < 500:
        return False

    first = image.pixelColor(0, 0).rgba()
    step_x = max(1, width // 20)
    step_y = max(1, height // 20)
    distinct = set()
    for x in range(0, width, step_x):
        for y in range(0, height, step_y):
            color = image.pixelColor(x, y).rgba()
            distinct.add(color)
            if color != first and len(distinct) >= 8:
                return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture and validate Tidekeeper GUI screens.")
    parser.add_argument(
        "--output",
        default=str(ROOT / "gui-screenshots"),
        help="Directory for generated PNG screenshots.",
    )
    parser.add_argument(
        "--platform",
        default=os.environ.get("QT_QPA_PLATFORM", "offscreen"),
        help="Qt platform plugin to use for capture.",
    )
    args = parser.parse_args()

    os.environ.setdefault("QT_QPA_PLATFORM", args.platform)
    os.environ["TIDEKEEPER_GUI_DEMO"] = "1"

    try:
        from PySide6.QtWidgets import QApplication
        from tidal_dl.gui_app.backend import DemoBackend
        from tidal_dl.gui_app.main_window import MainWindow, SCREEN_ORDER
    except ImportError as exc:
        print(f"Missing GUI dependency: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication([])
    backend = DemoBackend()
    backend.initialize()
    window = MainWindow(backend)
    window.prepare_demo_state()
    window.show()
    app.processEvents()

    failures = []
    for screen in SCREEN_ORDER:
        window.show_screen(screen)
        app.processEvents()
        pixmap = window.grab()
        image = pixmap.toImage()
        target = output / f"{screen}.png"
        if not pixmap.save(str(target), "PNG"):
            failures.append(f"{screen}: failed to save")
            continue
        if not _is_nonblank(image):
            failures.append(f"{screen}: screenshot looks blank or undersized")

    window.close()
    app.quit()

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print(f"Captured {len(SCREEN_ORDER)} screens in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

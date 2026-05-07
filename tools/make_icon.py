"""Render assets/icon.svg into a multi-resolution Windows .ico file."""
from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image
from PyQt6.QtCore import Qt, QBuffer
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "assets" / "icon.svg"
ICO = ROOT / "assets" / "icon.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def render_png(renderer: QSvgRenderer, size: int) -> bytes:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()

    buf = QBuffer()
    buf.open(QBuffer.OpenModeFlag.ReadWrite)
    pix.save(buf, "PNG")
    return bytes(buf.data())


def main() -> int:
    if not SVG.exists():
        print(f"missing source: {SVG}", file=sys.stderr)
        return 1

    app = QApplication(sys.argv)
    _ = app
    renderer = QSvgRenderer(str(SVG))
    if not renderer.isValid():
        print("invalid svg", file=sys.stderr)
        return 1

    images = [Image.open(io.BytesIO(render_png(renderer, s))) for s in SIZES]
    images[0].save(
        ICO,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=images[1:],
    )
    print(f"wrote {ICO} ({len(SIZES)} sizes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

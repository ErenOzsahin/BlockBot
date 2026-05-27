"""Synthetic Block Blast-like screenshot for tests."""
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
SAMPLES.mkdir(exist_ok=True)


def _draw_polyomino(img, origin_x, origin_y, cells, cell_size, color):
    for r, c in cells:
        x1 = origin_x + c * cell_size
        y1 = origin_y + r * cell_size
        cv2.rectangle(img, (x1, y1), (x1 + cell_size - 2, y1 + cell_size - 2), color, -1)


def main() -> None:
    w, h = 400, 700
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = (30, 30, 40)

    bx, by, bw = 80, 120, 240
    bh = bw
    cell = bw // 8
    cv2.rectangle(img, (bx - 4, by - 4), (bx + bw + 4, by + bh + 4), (120, 120, 140), 6)
    for i in range(8):
        for j in range(8):
            x1 = bx + j * cell
            y1 = by + i * cell
            filled = (i + j) % 3 == 0
            color = (180, 120, 80) if filled else (50, 50, 60)
            cv2.rectangle(img, (x1, y1), (x1 + cell, y1 + cell), color, -1)
            cv2.rectangle(img, (x1, y1), (x1 + cell, y1 + cell), (80, 80, 90), 1)

    tray_top = by + bh + 28
    slot_w = w // 3
    shapes = [
        [(0, 0), (0, 1), (1, 0)],
        [(0, 0), (1, 0), (2, 0)],
        [(0, 0), (0, 1), (1, 1)],
    ]
    cs = 24
    for slot, cells in enumerate(shapes):
        sx = slot * slot_w + (slot_w - 2 * cs) // 2
        sy = tray_top + 20
        _draw_polyomino(img, sx, sy, cells, cs, (200, 80, 120))

    out = SAMPLES / "test_board.jpg"
    cv2.imwrite(str(out), img)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

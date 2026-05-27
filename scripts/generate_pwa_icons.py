"""Generate minimal PWA PNG icons."""
from pathlib import Path

import cv2
import numpy as np

PUBLIC = Path(__file__).resolve().parents[1] / "frontend" / "public"


def icon(size: int) -> np.ndarray:
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:] = (30, 26, 46)
    m = size // 8
    cv2.rectangle(img, (m, m), (size - m, size - m), (233, 69, 96), max(2, size // 32))
    c = size // 4
    cv2.rectangle(img, (c, c), (c + size // 4, c + size // 4), (15, 52, 96), -1)
    cv2.rectangle(img, (c + size // 5, c), (c + size // 2, c + size // 4), (233, 69, 96), -1)
    return img


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    for name, s in [("pwa-192.png", 192), ("pwa-512.png", 512)]:
        path = PUBLIC / name
        cv2.imwrite(str(path), icon(s))
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()

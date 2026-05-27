"""Yerel tahta algılama testi — backend/vision/board.py kullanır."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND))

from vision.board import extract_board_from_path  # noqa: E402

if __name__ == "__main__":
    image = sys.argv[1] if len(sys.argv) > 1 else "samples/test_board.jpg"
    print(f"Görüntü işleniyor: {image}")
    result = extract_board_from_path(image, include_overlay=True)
    if result is None:
        print("Hata: Oyun tahtası bulunamadı.")
        sys.exit(1)
    print("\n--- 8x8 OYUN TAHTASI ---")
    for row in result.matrix:
        print(row)
    if result.overlay_png_base64:
        out = Path("debug_board_overlay.png")
        import base64

        out.write_bytes(base64.b64decode(result.overlay_png_base64))
        print(f"\nOverlay kaydedildi: {out}")

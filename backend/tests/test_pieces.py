from pathlib import Path

import cv2
import pytest

from vision.board import extract_board_from_path
from vision.pieces import extract_pieces_from_image

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "samples" / "test_board.jpg"


@pytest.mark.skipif(not SAMPLE.exists(), reason="Run scripts/generate_samples.py first")
def test_extract_pieces_from_sample():
    img = cv2.imread(str(SAMPLE))
    board = extract_board_from_path(str(SAMPLE))
    assert board is not None
    result = extract_pieces_from_image(img, board_rect=board.board_rect)
    detected = [p for p in result.pieces if p]
    assert len(detected) >= 2, f"Expected at least 2 pieces, got {result.pieces}"

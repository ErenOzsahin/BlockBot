from pathlib import Path

import pytest

from vision.board import extract_board_from_path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "samples" / "test_board.jpg"


@pytest.mark.skipif(not SAMPLE.exists(), reason="Run scripts/generate_samples.py first")
def test_extract_board_from_sample():
    result = extract_board_from_path(str(SAMPLE))
    assert result is not None
    assert len(result.matrix) == 8
    assert all(len(row) == 8 for row in result.matrix)

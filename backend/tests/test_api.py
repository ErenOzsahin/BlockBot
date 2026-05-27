from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "samples" / "test_board.jpg"


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.skipif(not SAMPLE.exists(), reason="Run scripts/generate_samples.py first")
def test_analyze_sample(client):
    with SAMPLE.open("rb") as f:
        r = client.post("/analyze", files={"file": ("test.jpg", f, "image/jpeg")}, params={"debug": True})
    assert r.status_code == 200
    data = r.json()
    assert len(data["board"]) == 8
    assert len(data["board"][0]) == 8


def test_analyze_invalid(client):
    r = client.post("/analyze", files={"file": ("x.jpg", b"not-an-image", "image/jpeg")})
    assert r.status_code in (400, 422)

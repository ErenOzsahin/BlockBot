import base64
from typing import Any

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from game.rules import rotate_piece
from game.solver import find_best_moves
from vision.board import extract_board_from_bytes
from vision.geometry import cell_outer_bounds
from vision.pieces import draw_pieces_overlay, extract_pieces_from_image


class MoveResponse(BaseModel):
    piece_index: int
    rotation: int
    row: int
    col: int
    score: float
    lines_cleared: int


class AnalyzeResponse(BaseModel):
    board: list[list[int]]
    board_rect: tuple[int, int, int, int]
    pieces: list[list[list[int]] | None]
    best_move: MoveResponse | None
    alternative_moves: list[MoveResponse]
    overlay_base64: str | None = None
    message: str | None = None


def _parse_cors_origins() -> list[str]:
    return [o.strip() for o in settings.cors_origins.split(",") if o.strip()]


app = FastAPI(title="Block Blast Bot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _rotate_piece_n(piece: list[list[int]], n: int) -> list[list[int]]:
    result = piece
    for _ in range(n % 4):
        result = rotate_piece(result)
    return result


def _draw_move_overlay(
    img: np.ndarray,
    grid_rect: tuple[int, int, int, int],
    piece: list[list[int]],
    row: int,
    col: int,
) -> np.ndarray:
    output = img.copy()
    pad = 2
    for i, prow in enumerate(piece):
        for j, cell in enumerate(prow):
            if not cell:
                continue
            r, c = row + i, col + j
            x1, y1, x2, y2 = cell_outer_bounds(grid_rect, r, c)
            cv2.rectangle(
                output,
                (x1 + pad, y1 + pad),
                (x2 - pad, y2 - pad),
                (0, 255, 255),
                -1,
            )
            cv2.rectangle(output, (x1, y1), (x2, y2), (0, 220, 220), 2)
    return output


def _move_to_response(move: Any) -> MoveResponse:
    return MoveResponse(
        piece_index=move.piece_index,
        rotation=move.rotation,
        row=move.row,
        col=move.col,
        score=move.score,
        lines_cleared=move.lines_cleared,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    debug: bool = Query(False, description="Include debug overlay image"),
) -> AnalyzeResponse:
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Dosya çok büyük (max 5MB).")
    if not data:
        raise HTTPException(status_code=400, detail="Boş dosya gönderildi.")

    include_overlay = debug or settings.debug_overlays
    board_result = extract_board_from_bytes(data, include_overlay=False)
    if board_result is None:
        raise HTTPException(
            status_code=422,
            detail="Oyun tahtası bulunamadı. Tam ekran görüntüsü yükleyin (tahta + alttaki 3 taş görünsün).",
        )

    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Geçersiz görüntü formatı.")

    piece_result = extract_pieces_from_image(img, board_rect=board_result.board_rect)
    moves = find_best_moves(board_result.matrix, piece_result.pieces, top_n=3)
    best = moves[0] if moves else None

    overlay_b64 = None
    if include_overlay:
        overlay_img = img.copy()
        bx, by, bw, bh = board_result.board_rect
        gx, gy, gw, gh = board_result.grid_rect
        cv2.rectangle(overlay_img, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
        cv2.rectangle(overlay_img, (gx, gy), (gx + gw, gy + gh), (0, 180, 0), 1)
        overlay_img = draw_pieces_overlay(overlay_img, piece_result)
        if best is not None:
            piece = piece_result.pieces[best.piece_index]
            if piece:
                rotated = _rotate_piece_n(piece, best.rotation)
                overlay_img = _draw_move_overlay(
                    overlay_img, board_result.grid_rect, rotated, best.row, best.col
                )
        _, buf = cv2.imencode(".png", overlay_img)
        overlay_b64 = base64.b64encode(buf.tobytes()).decode("ascii")

    alt_moves = [_move_to_response(m) for m in moves[1:]]
    message = None
    if best is None:
        playable = [p for p in piece_result.pieces if p]
        if not playable:
            message = "Alttaki taşlar algılanamadı. Ekran görüntüsünde 3 taş bölgesi görünsün."
        else:
            message = "Geçerli hamle bulunamadı — tahta dolu olabilir veya algılama hatalı."

    return AnalyzeResponse(
        board=board_result.matrix,
        board_rect=board_result.board_rect,
        pieces=piece_result.pieces,
        best_move=_move_to_response(best) if best else None,
        alternative_moves=alt_moves,
        overlay_base64=overlay_b64,
        message=message,
    )

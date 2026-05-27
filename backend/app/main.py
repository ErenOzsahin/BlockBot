import base64
from typing import Any

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from game.rules import rotate_piece
from game.solver import find_best_move_for_piece, find_best_moves
from vision.board import extract_board_from_bytes
from vision.geometry import cell_outer_bounds
from vision.pieces import draw_pieces_overlay, extract_pieces_from_image

SLOT_LABELS = ("Sol", "Orta", "Sağ")


class MoveResponse(BaseModel):
    piece_index: int
    rotation: int
    row: int
    col: int
    score: float
    lines_cleared: int


class PieceRecommendation(BaseModel):
    piece_index: int
    slot_label: str
    piece_name: str | None
    piece_shape: list[list[int]] | None
    move: MoveResponse | None
    advice: str


class AnalyzeResponse(BaseModel):
    board: list[list[int]]
    board_rect: tuple[int, int, int, int]
    pieces: list[list[list[int]] | None]
    piece_names: list[str | None]
    best_move: MoveResponse | None
    piece_recommendations: list[PieceRecommendation]
    alternative_moves: list[MoveResponse]
    summary: str | None = None
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
    *,
    color: tuple[int, int, int] = (0, 255, 255),
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
                color,
                -1,
            )
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
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


def _format_advice(
    slot_label: str,
    piece_name: str | None,
    move: MoveResponse | None,
) -> str:
    label = piece_name or "Bilinmeyen taş"
    if move is None:
        return f"{slot_label} ({label}): Bu taşla geçerli yer yok."

    rot = f", {move.rotation}×90° saat yönünde döndür" if move.rotation else ""
    lines = (
        f" — {move.lines_cleared} satır/sütun temizler."
        if move.lines_cleared
        else "."
    )
    return (
        f"{slot_label} ({label}): Satır {move.row + 1}, sütun {move.col + 1}'e yerleştir"
        f"{rot}{lines}"
    )


def _build_recommendations(
    board: list[list[int]],
    pieces: list[list[list[int]] | None],
    piece_names: list[str | None],
) -> list[PieceRecommendation]:
    recs: list[PieceRecommendation] = []
    for i in range(3):
        slot = SLOT_LABELS[i] if i < len(SLOT_LABELS) else f"Taş {i + 1}"
        piece = pieces[i] if i < len(pieces) else None
        name = piece_names[i] if i < len(piece_names) else None

        move_model = None
        if piece:
            move = find_best_move_for_piece(board, piece, i)
            if move:
                move_model = _move_to_response(move)

        recs.append(
            PieceRecommendation(
                piece_index=i,
                slot_label=slot,
                piece_name=name,
                piece_shape=piece,
                move=move_model,
                advice=_format_advice(slot, name, move_model),
            )
        )
    return recs


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
    pieces = piece_result.pieces
    piece_names = piece_result.piece_names

    recommendations = _build_recommendations(
        board_result.matrix, pieces, piece_names
    )
    moves = find_best_moves(board_result.matrix, pieces, top_n=3)
    best = moves[0] if moves else None

    summary = None
    if best is not None:
        slot = SLOT_LABELS[best.piece_index]
        name = (
            piece_names[best.piece_index]
            if best.piece_index < len(piece_names)
            else None
        )
        summary = (
            f"En iyi hamle: {slot} taş ({name or '?'}) — "
            f"satır {best.row + 1}, sütun {best.col + 1}"
            + (f", {best.rotation}×90°" if best.rotation else "")
        )

    overlay_b64 = None
    if include_overlay:
        overlay_img = img.copy()
        bx, by, bw, bh = board_result.board_rect
        gx, gy, gw, gh = board_result.grid_rect
        cv2.rectangle(overlay_img, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
        cv2.rectangle(overlay_img, (gx, gy), (gx + gw, gy + gh), (0, 180, 0), 1)
        overlay_img = draw_pieces_overlay(overlay_img, piece_result)

        colors = [(0, 255, 255), (255, 200, 0), (200, 100, 255)]
        for rec in recommendations:
            if rec.move and rec.piece_shape:
                rotated = _rotate_piece_n(rec.piece_shape, rec.move.rotation)
                color = colors[rec.piece_index % len(colors)]
                overlay_img = _draw_move_overlay(
                    overlay_img,
                    board_result.grid_rect,
                    rotated,
                    rec.move.row,
                    rec.move.col,
                    color=color,
                )
        _, buf = cv2.imencode(".png", overlay_img)
        overlay_b64 = base64.b64encode(buf.tobytes()).decode("ascii")

    alt_moves = [_move_to_response(m) for m in moves[1:]]
    message = None
    if best is None:
        playable = [p for p in pieces if p]
        if not playable:
            message = "Alttaki taşlar algılanamadı. Ekran görüntüsünde 3 taş bölgesi görünsün."
        else:
            message = "Geçerli hamle bulunamadı — tahta dolu olabilir veya algılama hatalı."

    return AnalyzeResponse(
        board=board_result.matrix,
        board_rect=board_result.board_rect,
        pieces=pieces,
        piece_names=piece_names,
        best_move=_move_to_response(best) if best else None,
        piece_recommendations=recommendations,
        alternative_moves=alt_moves,
        summary=summary,
        overlay_base64=overlay_b64,
        message=message,
    )

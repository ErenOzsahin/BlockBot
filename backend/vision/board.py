import base64
from dataclasses import dataclass

import cv2
import numpy as np

from app.config import settings
from vision.geometry import BOARD_SIZE, apply_board_inset, cell_sample_bounds


@dataclass
class BoardResult:
    matrix: list[list[int]]
    board_rect: tuple[int, int, int, int]
    grid_rect: tuple[int, int, int, int]
    overlay_png_base64: str | None = None


def _decode_image(image_bytes: bytes) -> np.ndarray | None:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _scale_for_processing(img: np.ndarray, max_side: int = 1280) -> tuple[np.ndarray, float]:
    h, w = img.shape[:2]
    side = max(h, w)
    if side <= max_side:
        return img, 1.0
    scale = max_side / side
    resized = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return resized, scale


def _score_board_candidate(
    gray: np.ndarray, rect: tuple[int, int, int, int], area: float
) -> float:
    h, w = gray.shape
    x, y, bw, bh = rect
    cx, cy = x + bw / 2, y + bh / 2
    score = area
    if 0.2 * w < cx < 0.8 * w and 0.08 * h < cy < 0.65 * h:
        score += area * 0.4
    return score


def _find_board_rect_contours(gray: np.ndarray) -> tuple[int, int, int, int] | None:
    h, w = gray.shape
    min_area = max(settings.min_contour_area, int(w * h * 0.03))
    max_area = int(w * h * 0.7)
    best_rect = None
    best_score = 0.0

    canny_pairs = [
        (settings.canny_low, settings.canny_high),
        (30, 100),
        (60, 180),
    ]

    for low, high in canny_pairs:
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, low, high)
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area or area > max_area:
                continue
            x, y, bw, bh = cv2.boundingRect(contour)
            if bh == 0:
                continue
            aspect_ratio = float(bw) / bh
            if 0.82 <= aspect_ratio <= 1.18:
                rect = (x, y, bw, bh)
                score = _score_board_candidate(gray, rect, area)
                if score > best_score:
                    best_score = score
                    best_rect = rect

    return best_rect


def _find_board_rect_geometric(gray: np.ndarray) -> tuple[int, int, int, int]:
    h, w = gray.shape
    side = int(min(w, h) * 0.78)
    side = min(side, w - 4, int(h * 0.58))
    x = (w - side) // 2
    y = int(h * 0.14)
    if y + side > int(h * 0.68):
        y = max(0, int(h * 0.68) - side)
    return (x, y, side, side)


def _find_board_rect(gray: np.ndarray) -> tuple[int, int, int, int]:
    rect = _find_board_rect_contours(gray)
    if rect is not None:
        return rect
    return _find_board_rect_geometric(gray)


def _cell_threshold(gray: np.ndarray, grid_rect: tuple[int, int, int, int]) -> float:
    bx, by, bw, bh = grid_rect
    region = gray[by : by + bh, bx : bx + bw]
    if region.size == 0:
        return float(settings.cell_brightness_threshold)
    mean_val = float(np.mean(region))
    median_val = float(np.median(region))
    adaptive = (mean_val + median_val) / 2
    return max(40.0, min(180.0, adaptive * 0.82))


def _read_board_cells(gray: np.ndarray, grid_rect: tuple[int, int, int, int]) -> np.ndarray:
    board_matrix = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
    threshold_value = _cell_threshold(gray, grid_rect)

    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            x1, y1, x2, y2 = cell_sample_bounds(grid_rect, i, j)
            cell_crop = gray[y1:y2, x1:x2]
            if cell_crop.size == 0:
                continue
            if np.mean(cell_crop) > threshold_value:
                board_matrix[i][j] = 1
    return board_matrix


def _scale_rect(rect: tuple[int, int, int, int], inv_scale: float) -> tuple[int, int, int, int]:
    if inv_scale == 1.0:
        return rect
    x, y, w, h = rect
    s = inv_scale
    return (int(x * s), int(y * s), int(w * s), int(h * s))


def _build_overlay(
    img: np.ndarray,
    board_rect: tuple[int, int, int, int],
    grid_rect: tuple[int, int, int, int],
    board_matrix: np.ndarray,
) -> str:
    output = img.copy()
    bx, by, bw, bh = board_rect
    cv2.rectangle(output, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
    gx, gy, gw, gh = grid_rect
    cv2.rectangle(output, (gx, gy), (gx + gw, gy + gh), (0, 200, 0), 1)

    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            if board_matrix[i][j] == 1:
                x1, y1, x2, y2 = cell_sample_bounds(grid_rect, i, j)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                cv2.circle(output, (cx, cy), 3, (0, 0, 255), -1)
    _, buf = cv2.imencode(".png", output)
    return base64.b64encode(buf.tobytes()).decode("ascii")


def extract_board_from_bytes(
    image_bytes: bytes, *, include_overlay: bool = False
) -> BoardResult | None:
    img = _decode_image(image_bytes)
    if img is None:
        return None

    proc_img, scale = _scale_for_processing(img)
    inv_scale = 1.0 / scale if scale else 1.0
    gray = cv2.cvtColor(proc_img, cv2.COLOR_BGR2GRAY)

    board_rect_proc = _find_board_rect(gray)
    grid_rect_proc = apply_board_inset(board_rect_proc)
    board_matrix = _read_board_cells(gray, grid_rect_proc)

    board_rect = _scale_rect(board_rect_proc, inv_scale)
    grid_rect = _scale_rect(grid_rect_proc, inv_scale)

    overlay = None
    if include_overlay:
        overlay = _build_overlay(img, board_rect, grid_rect, board_matrix)

    return BoardResult(
        matrix=board_matrix.tolist(),
        board_rect=board_rect,
        grid_rect=grid_rect,
        overlay_png_base64=overlay,
    )


def extract_board_from_path(image_path: str, *, include_overlay: bool = False) -> BoardResult | None:
    with open(image_path, "rb") as f:
        return extract_board_from_bytes(f.read(), include_overlay=include_overlay)

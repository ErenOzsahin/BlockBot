from dataclasses import dataclass

import cv2
import numpy as np

from app.config import settings

GRID_SIZE = 5
MIN_BLOCKS = 1
MAX_BLOCKS = 9


@dataclass
class PieceResult:
    pieces: list[list[list[int]] | None]
    slot_rects: list[tuple[int, int, int, int]]


def _normalize_shape(mask: np.ndarray) -> list[list[int]]:
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any() or not cols.any():
        return []

    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    cropped = mask[rmin : rmax + 1, cmin : cmax + 1]
    return cropped.astype(int).tolist()


def _block_count(shape: list[list[int]]) -> int:
    return sum(sum(row) for row in shape)


def _largest_component_mask(mask: np.ndarray) -> np.ndarray:
    binary = (mask > 0).astype(np.uint8) * 255
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if num_labels <= 1:
        return binary

    best_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    component = np.zeros_like(binary)
    component[labels == best_label] = 255
    return component


def _rasterize_crop(crop: np.ndarray, grid_r: int, grid_c: int) -> np.ndarray:
    ch, cw = crop.shape
    mini = np.zeros((grid_r, grid_c), dtype=np.uint8)
    for i in range(grid_r):
        for j in range(grid_c):
            sy = i * ch // grid_r
            ey = (i + 1) * ch // grid_r
            sx = j * cw // grid_c
            ex = (j + 1) * cw // grid_c
            cell = crop[sy:ey, sx:ex]
            if cell.size and np.mean(cell) > 0.55:
                mini[i][j] = 1
    return mini


def _mask_to_shape(mask: np.ndarray, grid: int = GRID_SIZE) -> list[list[int]] | None:
    if mask is None or mask.size == 0:
        return None
    binary = _largest_component_mask(mask)
    if np.count_nonzero(binary) < 4:
        return None

    coords = np.column_stack(np.where(binary > 0))
    r0, c0 = coords.min(axis=0)
    r1, c1 = coords.max(axis=0)
    crop = binary[r0 : r1 + 1, c0 : c1 + 1]
    ch, cw = crop.shape
    if ch < 2 or cw < 2:
        return None

    best_shape: list[list[int]] | None = None
    best_score = -1e9

    for grid_r in range(1, grid + 1):
        for grid_c in range(1, grid + 1):
            mini = _rasterize_crop(crop, grid_r, grid_c)
            shape = _normalize_shape(mini)
            if not shape:
                continue
            blocks = _block_count(shape)
            if blocks < MIN_BLOCKS or blocks > MAX_BLOCKS:
                continue
            score = _shape_quality_score(shape)
            if score > best_score:
                best_score = score
                best_shape = shape

    return best_shape


def _refine_mask(mask: np.ndarray) -> np.ndarray:
    kernel = np.ones((3, 3), np.uint8)
    refined = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    refined = cv2.morphologyEx(refined, cv2.MORPH_OPEN, kernel, iterations=1)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(refined, connectivity=8)
    if num_labels <= 1:
        return refined

    h, w = refined.shape
    min_area = max(12, (h * w) * 0.002)
    keep = np.zeros_like(refined)
    for label in range(1, num_labels):
        area = stats[label, cv2.CC_STAT_AREA]
        if area >= min_area:
            keep[labels == label] = 255
    return keep


def _colored_block_mask(slot_bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(slot_bgr, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    color_mask = ((saturation > 30) & (value > 40)).astype(np.uint8) * 255

    gray = cv2.cvtColor(slot_bgr, cv2.COLOR_BGR2GRAY)
    corner_samples = np.concatenate(
        [
            gray[0:12, 0:12].ravel(),
            gray[0:12, -12:].ravel(),
            gray[-12:, 0:12].ravel(),
            gray[-12:, -12:].ravel(),
        ]
    )
    bg = float(np.median(corner_samples))
    bright_mask = (gray > bg + 15).astype(np.uint8) * 255

    b, g, r = cv2.split(slot_bgr)
    max_c = np.maximum(np.maximum(r, g), b).astype(np.float32)
    min_c = np.minimum(np.minimum(r, g), b).astype(np.float32)
    chroma_mask = ((max_c - min_c) > 18) & (max_c > 55)
    chroma_mask = chroma_mask.astype(np.uint8) * 255

    combined = cv2.bitwise_or(color_mask, bright_mask)
    combined = cv2.bitwise_or(combined, chroma_mask)
    return _refine_mask(combined)


def _otsu_mask(slot_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(slot_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    corner_med = float(np.median(gray[0:10, 0:10]))
    if np.mean(binary) > 127:
        binary = cv2.bitwise_not(binary)
    if np.mean(gray[binary > 0]) < corner_med + 8:
        _, binary = cv2.threshold(blur, corner_med + 12, 255, cv2.THRESH_BINARY)
    return _refine_mask(binary)


def _fixed_threshold_mask(slot_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(slot_bgr, cv2.COLOR_BGR2GRAY)
    thresh = max(35, settings.piece_brightness_threshold - 20)
    _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
    return _refine_mask(binary)


def _inner_slot(slot_bgr: np.ndarray, margin: float = 0.12) -> np.ndarray:
    h, w = slot_bgr.shape[:2]
    mx, my = int(w * margin), int(h * margin)
    if mx * 2 >= w or my * 2 >= h:
        return slot_bgr
    return slot_bgr[my : h - my, mx : w - mx]


def _blob_mask(slot_bgr: np.ndarray) -> np.ndarray:
    """Mask tuned for separate block blobs (less merging than _colored_block_mask)."""
    hsv = cv2.cvtColor(slot_bgr, cv2.COLOR_BGR2HSV)
    color_mask = ((hsv[:, :, 1] > 55) & (hsv[:, :, 2] > 55)).astype(np.uint8) * 255
    gray = cv2.cvtColor(slot_bgr, cv2.COLOR_BGR2GRAY)
    bg = float(np.median(np.concatenate([gray[0:8, 0:8].ravel(), gray[-8:, -8:].ravel()])))
    bright_mask = (gray > bg + 14).astype(np.uint8) * 255
    combined = cv2.bitwise_or(color_mask, bright_mask)
    kernel = np.ones((2, 2), np.uint8)
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel, iterations=1)
    return combined


def _cluster_centers(values: list[float], gap: float) -> list[float]:
    if not values:
        return []
    sorted_vals = sorted(values)
    clusters: list[list[float]] = [[sorted_vals[0]]]
    for val in sorted_vals[1:]:
        if val - clusters[-1][-1] > gap:
            clusters.append([val])
        else:
            clusters[-1].append(val)
    return [sum(group) / len(group) for group in clusters]


def _extract_piece_from_blobs(slot_bgr: np.ndarray) -> list[list[int]] | None:
    inner = _inner_slot(slot_bgr)
    h, w = inner.shape[:2]
    mask = _blob_mask(inner)
    if np.count_nonzero(mask) / max(1, mask.size) > 0.55:
        return None
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area = max(6, (h * w) * 0.006)
    max_area = (h * w) * 0.28
    centers: list[tuple[float, float]] = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue
        bx, by, bw, bh = cv2.boundingRect(contour)
        aspect = bw / max(bh, 1)
        if aspect > 2.8 or aspect < 0.35:
            continue
        moments = cv2.moments(contour)
        if moments["m00"] == 0:
            continue
        cx = moments["m10"] / moments["m00"]
        cy = moments["m01"] / moments["m00"]
        centers.append((cy, cx))

    if not centers or len(centers) > MAX_BLOCKS:
        return None

    ys = [c[0] for c in centers]
    xs = [c[1] for c in centers]
    row_gap = max(5, h * 0.2)
    col_gap = max(5, w * 0.2)
    row_centers = _cluster_centers(ys, row_gap)
    col_centers = _cluster_centers(xs, col_gap)

    grid = np.zeros((len(row_centers), len(col_centers)), dtype=np.uint8)
    for cy, cx in centers:
        ri = min(range(len(row_centers)), key=lambda i: abs(row_centers[i] - cy))
        ci = min(range(len(col_centers)), key=lambda i: abs(col_centers[i] - cx))
        grid[ri, ci] = 1

    shape = _normalize_shape(grid)
    if not shape:
        return None
    blocks = _block_count(shape)
    if blocks < MIN_BLOCKS or blocks > MAX_BLOCKS:
        return None
    return shape


def _shape_quality_score(shape: list[list[int]]) -> float:
    blocks = _block_count(shape)
    rows, cols = len(shape), len(shape[0]) if shape else 0
    score = 10.0
    score -= abs(blocks - 4) * 1.2
    score -= max(0, rows * cols - blocks) * 0.3
    if rows == 1 and cols >= 4:
        score -= 15
    if cols == 1 and rows >= 4:
        score -= 15
    if rows == 2 and cols == 2 and blocks == 4:
        score += 4
    if blocks == 3 and (rows == 2 or cols == 2):
        score += 2
    return score


def _extract_piece_from_slot(slot_bgr: np.ndarray) -> list[list[int]] | None:
    if slot_bgr.size == 0:
        return None

    inner = _inner_slot(slot_bgr)
    shapes: list[list[list[int]]] = []
    blob_shape = _extract_piece_from_blobs(slot_bgr)
    if blob_shape:
        shapes.append(blob_shape)

    for mask_fn in (_colored_block_mask, _otsu_mask, _fixed_threshold_mask):
        shape = _mask_to_shape(mask_fn(inner))
        if shape:
            shapes.append(shape)

    if not shapes:
        return None

    return max(shapes, key=_shape_quality_score)


def _slots_from_tray(tray_left: int, tray_top: int, tray_w: int, tray_h: int) -> list[tuple[int, int, int, int]]:
    pad_x = max(4, int(tray_w * 0.03))
    inner_w = tray_w - 2 * pad_x
    slot_w = inner_w // settings.piece_slot_count
    pad_y = max(4, int(tray_h * 0.08))
    slot_h = tray_h - 2 * pad_y
    slots = []
    for i in range(settings.piece_slot_count):
        sx = tray_left + pad_x + i * slot_w
        sy = tray_top + pad_y
        slots.append((sx, sy, slot_w, slot_h))
    return slots


def _tray_from_board(
    h: int, w: int, board_rect: tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    bx, by, bw, bh = board_rect
    gap = max(8, int(bh * 0.06))
    tray_top = by + bh + gap
    tray_height = int(bh * 0.72)
    tray_bottom = min(h - 8, tray_top + tray_height)
    tray_height = max(tray_bottom - tray_top, int(bh * 0.35))

    margin_x = int(bw * 0.12)
    tray_left = max(0, bx - margin_x)
    tray_right = min(w, bx + bw + margin_x)
    tray_w = tray_right - tray_left
    return tray_left, tray_top, tray_w, tray_height


def _tray_from_ratio(h: int, w: int, top_ratio: float) -> tuple[int, int, int, int]:
    tray_top = int(h * top_ratio)
    tray_height = h - tray_top - int(h * 0.05)
    return 0, tray_top, w, max(tray_height, int(h * 0.2))


def _detect_with_tray(img: np.ndarray, tray: tuple[int, int, int, int]) -> PieceResult:
    tray_left, tray_top, tray_w, tray_height = tray
    slots = _slots_from_tray(tray_left, tray_top, tray_w, tray_height)
    pieces: list[list[list[int]] | None] = []
    for slot in slots:
        x, y, sw, sh = slot
        slot_bgr = img[y : y + sh, x : x + sw]
        pieces.append(_extract_piece_from_slot(slot_bgr))
    return PieceResult(pieces=pieces, slot_rects=slots)


def _score_piece_result(result: PieceResult) -> int:
    return sum(1 for p in result.pieces if p)


def extract_pieces_from_image(
    img: np.ndarray,
    board_rect: tuple[int, int, int, int] | None = None,
) -> PieceResult:
    h, w = img.shape[:2]
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    trays: list[tuple[int, int, int, int]] = []
    if board_rect is not None:
        trays.append(_tray_from_board(h, w, board_rect))

    for ratio in (0.52, 0.55, 0.58, settings.piece_region_top_ratio, 0.65, 0.68):
        tray = _tray_from_ratio(h, w, ratio)
        if tray not in trays:
            trays.append(tray)

    best_result = _detect_with_tray(img, trays[0])
    best_score = _score_piece_result(best_result)

    for tray in trays[1:]:
        candidate = _detect_with_tray(img, tray)
        score = _score_piece_result(candidate)
        if score > best_score:
            best_score = score
            best_result = candidate

    return best_result


def draw_pieces_overlay(img: np.ndarray, piece_result: PieceResult) -> np.ndarray:
    output = img.copy()
    for idx, slot in enumerate(piece_result.slot_rects):
        x, y, sw, sh = slot
        color = (0, 200, 255) if piece_result.pieces[idx] else (0, 120, 255)
        cv2.rectangle(output, (x, y), (x + sw, y + sh), color, 2)
    return output

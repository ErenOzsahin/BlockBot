"""Shared board grid geometry for vision + overlay alignment."""

BOARD_SIZE = 8
INSET_RATIO = 0.07


def apply_board_inset(rect: tuple[int, int, int, int], inset_ratio: float = INSET_RATIO) -> tuple[int, int, int, int]:
    x, y, w, h = rect
    inset = int(min(w, h) * inset_ratio)
    inset = min(inset, w // 4, h // 4)
    return x + inset, y + inset, w - 2 * inset, h - 2 * inset


def cell_outer_bounds(
    board_rect: tuple[int, int, int, int],
    row: int,
    col: int,
    n: int = BOARD_SIZE,
) -> tuple[int, int, int, int]:
    """Pixel bounds (x1, y1, x2, y2) for drawing — includes grid gaps."""
    bx, by, bw, bh = board_rect
    x1 = bx + (col * bw) // n
    x2 = bx + ((col + 1) * bw) // n
    y1 = by + (row * bh) // n
    y2 = by + ((row + 1) * bh) // n
    return x1, y1, x2, y2


def cell_sample_bounds(
    board_rect: tuple[int, int, int, int],
    row: int,
    col: int,
    n: int = BOARD_SIZE,
    margin_ratio: float = 0.18,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = cell_outer_bounds(board_rect, row, col, n)
    mx = max(1, int((x2 - x1) * margin_ratio))
    my = max(1, int((y2 - y1) * margin_ratio))
    return x1 + mx, y1 + my, x2 - mx, y2 - my

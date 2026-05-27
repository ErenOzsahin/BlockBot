from dataclasses import dataclass

from game.rules import (
    BOARD_SIZE,
    apply_move,
    can_place,
    clear_lines,
    count_holes,
    rotate_piece,
)


@dataclass
class MoveSuggestion:
    piece_index: int
    rotation: int
    row: int
    col: int
    score: float
    lines_cleared: int
    board_after: list[list[int]]


def _score_board(board: list[list[int]], lines_cleared: int) -> float:
    filled = sum(sum(row) for row in board)
    holes = count_holes(board)
    return (
        lines_cleared * 1000
        - holes * 50
        - filled * 2
    )


def _piece_rotations(piece: list[list[int]]) -> list[tuple[int, list[list[int]]]]:
    rotations: list[tuple[int, list[list[int]]]] = []
    current = piece
    for rot in range(4):
        normalized = [list(r) for r in current]
        if normalized and normalized not in [p for _, p in rotations]:
            rotations.append((rot, normalized))
        current = rotate_piece(current)
    return rotations


def find_best_moves(
    board: list[list[int]],
    pieces: list[list[list[int]] | None],
    *,
    top_n: int = 3,
) -> list[MoveSuggestion]:
    candidates: list[MoveSuggestion] = []

    for piece_index, piece in enumerate(pieces):
        if not piece:
            continue
        for rotation, rotated in _piece_rotations(piece):
            ph = len(rotated)
            pw = len(rotated[0]) if rotated else 0
            for row in range(BOARD_SIZE - ph + 1):
                for col in range(BOARD_SIZE - pw + 1):
                    if not can_place(board, rotated, row, col):
                        continue
                    placed = apply_move(board, rotated, row, col)
                    cleared_board, lines = clear_lines(placed)
                    score = _score_board(cleared_board, lines)
                    candidates.append(
                        MoveSuggestion(
                            piece_index=piece_index,
                            rotation=rotation,
                            row=row,
                            col=col,
                            score=score,
                            lines_cleared=lines,
                            board_after=cleared_board,
                        )
                    )

    candidates.sort(key=lambda m: m.score, reverse=True)
    return candidates[:top_n]


def find_best_move(
    board: list[list[int]], pieces: list[list[list[int]] | None]
) -> MoveSuggestion | None:
    moves = find_best_moves(board, pieces, top_n=1)
    return moves[0] if moves else None

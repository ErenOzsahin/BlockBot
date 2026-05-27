BOARD_SIZE = 8


def rotate_piece(piece: list[list[int]]) -> list[list[int]]:
    if not piece:
        return []
    return [list(row) for row in zip(*piece[::-1])]


def can_place(board: list[list[int]], piece: list[list[int]], row: int, col: int) -> bool:
    if not piece:
        return False
    ph, pw = len(piece), len(piece[0])
    for i in range(ph):
        for j in range(pw):
            if piece[i][j] == 0:
                continue
            r, c = row + i, col + j
            if r < 0 or c < 0 or r >= BOARD_SIZE or c >= BOARD_SIZE:
                return False
            if board[r][c] == 1:
                return False
    return True


def apply_move(
    board: list[list[int]], piece: list[list[int]], row: int, col: int
) -> list[list[int]]:
    new_board = [row[:] for row in board]
    for i, prow in enumerate(piece):
        for j, cell in enumerate(prow):
            if cell:
                new_board[row + i][col + j] = 1
    return new_board


def clear_lines(board: list[list[int]]) -> tuple[list[list[int]], int]:
    cleared = 0
    new_board = [row[:] for row in board]

    full_rows = [i for i in range(BOARD_SIZE) if all(new_board[i])]
    full_cols = [j for j in range(BOARD_SIZE) if all(new_board[i][j] for i in range(BOARD_SIZE))]

    for i in full_rows:
        new_board[i] = [0] * BOARD_SIZE
        cleared += 1
    for j in full_cols:
        for i in range(BOARD_SIZE):
            new_board[i][j] = 0
        cleared += 1

    return new_board, cleared


def count_holes(board: list[list[int]]) -> int:
    holes = 0
    for c in range(BOARD_SIZE):
        found_block = False
        for r in range(BOARD_SIZE):
            if board[r][c] == 1:
                found_block = True
            elif found_block and board[r][c] == 0:
                holes += 1
    return holes

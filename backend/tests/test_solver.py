from game.rules import can_place, clear_lines
from game.solver import find_best_move


def test_can_place_empty_board():
    piece = [[1, 1], [1, 0]]
    board = [[0] * 8 for _ in range(8)]
    assert can_place(board, piece, 0, 0)


def test_clear_full_row():
    board = [[1] * 8 for _ in range(8)]
    board[7] = [0] * 8
    cleared, count = clear_lines(board)
    assert count >= 1
    assert all(cleared[0][j] == 0 for j in range(8))


def test_find_move_simple():
    board = [[0] * 8 for _ in range(8)]
    pieces = [[[1, 1]], None, None]
    move = find_best_move(board, pieces)
    assert move is not None
    assert move.piece_index == 0

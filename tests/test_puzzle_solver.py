"""スライドパズルソルバーのユニットテスト。"""
import pytest
from visualquiz.quiz3_puzzle.puzzle_solver import (
    PuzzleState,
    create_shuffled_puzzle,
    is_solvable,
    solve_astar,
)


def test_puzzle_state_goal():
    state = PuzzleState.from_list([1, 2, 3, 4, 5, 6, 7, 8, 0], 3, 3)
    assert state.is_goal() is True


def test_puzzle_state_not_goal():
    state = PuzzleState.from_list([1, 2, 3, 4, 5, 6, 7, 0, 8], 3, 3)
    assert state.is_goal() is False


def test_puzzle_neighbors():
    # 空きスペースが右下のとき、上と左に動ける
    state = PuzzleState.from_list([1, 2, 3, 4, 5, 6, 7, 8, 0], 3, 3)
    neighbors = state.neighbors()
    assert len(neighbors) == 2


def test_manhattan_distance_goal():
    state = PuzzleState.from_list([1, 2, 3, 4, 5, 6, 7, 8, 0], 3, 3)
    assert state.manhattan_distance() == 0


def test_manhattan_distance_one_move():
    # 8と0を入れ替え → 8が1マスずれている（インデックス7の位置、本来は8）
    state = PuzzleState.from_list([1, 2, 3, 4, 5, 6, 7, 0, 8], 3, 3)
    assert state.manhattan_distance() == 1  # 8は本来(2,2)にいるが(2,1)→隣1マス


def test_solve_astar_trivial():
    goal = PuzzleState.from_list([1, 2, 3, 4, 5, 6, 7, 8, 0], 3, 3)
    solution = solve_astar(goal)
    assert solution is not None
    assert len(solution) == 1


def test_solve_astar_one_move():
    # 8と0を入れ替えるだけ
    start = PuzzleState.from_list([1, 2, 3, 4, 5, 6, 7, 0, 8], 3, 3)
    solution = solve_astar(start)
    assert solution is not None
    assert len(solution) == 2
    assert solution[-1].is_goal()


def test_solve_astar_small_puzzle():
    start = create_shuffled_puzzle(2, 2, shuffle_steps=5)
    solution = solve_astar(start, max_moves=50)
    assert solution is not None
    assert solution[-1].is_goal()


def test_create_shuffled_puzzle():
    state = create_shuffled_puzzle(3, 3, shuffle_steps=20)
    assert len(state.tiles) == 9
    assert 0 in state.tiles
    assert state.blank_pos == state.tiles.index(0)


def test_is_solvable_goal():
    tiles = [1, 2, 3, 4, 5, 6, 7, 8, 0]
    assert is_solvable(tiles, 3, 3) is True

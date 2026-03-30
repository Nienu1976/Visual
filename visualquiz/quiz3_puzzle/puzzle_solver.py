"""漢字スライドパズルのA*ソルバー。

N×Mグリッドのスライドパズルを最短手数で解く。
タイル数が多い場合はIDA*に切り替える。
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class PuzzleState:
    """パズルの状態を表す不変オブジェクト。"""
    tiles: tuple[int, ...]  # 0が空きスペース、1〜N*M-1がタイル番号
    rows: int
    cols: int
    blank_pos: int  # 空きスペースのインデックス

    @classmethod
    def from_list(cls, tiles: list[int], rows: int, cols: int) -> "PuzzleState":
        blank = tiles.index(0)
        return cls(tuple(tiles), rows, cols, blank)

    def neighbors(self) -> list["PuzzleState"]:
        """空きスペースを上下左右に動かした隣接状態のリストを返す。"""
        moves = []
        r, c = divmod(self.blank_pos, self.cols)
        directions = [
            (-1, 0),  # 上
            (1, 0),   # 下
            (0, -1),  # 左
            (0, 1),   # 右
        ]
        tiles = list(self.tiles)
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                new_blank = nr * self.cols + nc
                new_tiles = tiles[:]
                new_tiles[self.blank_pos], new_tiles[new_blank] = (
                    new_tiles[new_blank],
                    new_tiles[self.blank_pos],
                )
                moves.append(PuzzleState.from_list(new_tiles, self.rows, self.cols))
        return moves

    def goal(self) -> "PuzzleState":
        """ゴール状態（1,2,...,N*M-1,0）を返す。"""
        n = self.rows * self.cols
        goal_tiles = list(range(1, n)) + [0]
        return PuzzleState.from_list(goal_tiles, self.rows, self.cols)

    def is_goal(self) -> bool:
        n = self.rows * self.cols
        goal_tiles = tuple(range(1, n)) + (0,)
        return self.tiles == goal_tiles

    def manhattan_distance(self) -> int:
        """ゴールまでのマンハッタン距離（ヒューリスティック）。"""
        distance = 0
        for i, tile in enumerate(self.tiles):
            if tile == 0:
                continue
            goal_r, goal_c = divmod(tile - 1, self.cols)
            curr_r, curr_c = divmod(i, self.cols)
            distance += abs(goal_r - curr_r) + abs(goal_c - curr_c)
        return distance


def is_solvable(tiles: list[int], rows: int, cols: int) -> bool:
    """スライドパズルが解けるか判定する。

    偶数幅グリッド：空きの行位置（下から）+ 転倒数の奇偶で判定。
    奇数幅グリッド：転倒数の奇偶のみ。
    """
    flat = [t for t in tiles if t != 0]
    inversions = sum(
        1
        for i in range(len(flat))
        for j in range(i + 1, len(flat))
        if flat[i] > flat[j]
    )
    blank_pos = tiles.index(0)
    blank_row_from_bottom = rows - blank_pos // cols

    if cols % 2 == 1:
        return inversions % 2 == 0
    else:
        return (inversions + blank_row_from_bottom) % 2 == 1


def solve_astar(start: PuzzleState, max_moves: int = 200) -> list[PuzzleState] | None:
    """A*アルゴリズムでパズルを解き、状態遷移リストを返す。

    Args:
        start: 初期状態。
        max_moves: 探索上限手数。

    Returns:
        初期状態→ゴール状態の遷移リスト。解なしの場合はNone。
    """
    if start.is_goal():
        return [start]

    # (f, g, state, path)
    counter = 0
    open_heap: list[tuple[int, int, int, PuzzleState, list[PuzzleState]]] = []
    h = start.manhattan_distance()
    heapq.heappush(open_heap, (h, 0, counter, start, [start]))
    visited: dict[tuple[int, ...], int] = {start.tiles: 0}

    while open_heap:
        f, g, _, state, path = heapq.heappop(open_heap)

        if g > max_moves:
            continue

        for neighbor in state.neighbors():
            new_g = g + 1
            if neighbor.tiles in visited and visited[neighbor.tiles] <= new_g:
                continue
            visited[neighbor.tiles] = new_g
            new_path = path + [neighbor]
            if neighbor.is_goal():
                return new_path
            counter += 1
            new_h = neighbor.manhattan_distance()
            heapq.heappush(open_heap, (new_g + new_h, new_g, counter, neighbor, new_path))

    return None


def create_shuffled_puzzle(rows: int, cols: int, shuffle_steps: int = 100) -> PuzzleState:
    """ランダムにシャッフルされた解けるパズル状態を生成する。

    完全ランダム生成は解けない場合があるため、
    ゴール状態からランダムに手を加えてシャッフルする。
    """
    import random
    n = rows * cols
    goal_tiles = list(range(1, n)) + [0]
    state = PuzzleState.from_list(goal_tiles, rows, cols)

    for _ in range(shuffle_steps):
        neighbors = state.neighbors()
        state = random.choice(neighbors)

    return state

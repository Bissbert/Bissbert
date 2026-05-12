"""A* pathfinder on a bounded grid with dynamic obstacles."""

from __future__ import annotations

import heapq
from collections.abc import Iterable

Cell = tuple[int, int]


def manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def neighbours(cell: Cell, cols: int, rows: int) -> Iterable[Cell]:
    c, r = cell
    if c > 0:        yield (c - 1, r)
    if c < cols - 1: yield (c + 1, r)
    if r > 0:        yield (c, r - 1)
    if r < rows - 1: yield (c, r + 1)


def find_path(
    start: Cell,
    goal: Cell,
    cols: int,
    rows: int,
    obstacles: frozenset[Cell],
) -> list[Cell] | None:
    """A* from start to goal. Returns path excluding start, or None if no path.

    `obstacles` is the set of cells the snake currently occupies that block movement.
    The caller is responsible for excluding the tail tip (it moves out of the way).
    Goal is always treated as passable even if it appears in obstacles."""
    if start == goal:
        return []

    open_heap: list[tuple[int, int, Cell]] = []
    counter = 0
    heapq.heappush(open_heap, (manhattan(start, goal), counter, start))
    came_from: dict[Cell, Cell] = {}
    g_score: dict[Cell, int] = {start: 0}

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current == goal:
            path = [current]
            while path[-1] in came_from:
                path.append(came_from[path[-1]])
            path.reverse()
            return path[1:]

        for nb in neighbours(current, cols, rows):
            if nb in obstacles and nb != goal:
                continue
            tentative = g_score[current] + 1
            if tentative < g_score.get(nb, 1 << 30):
                came_from[nb] = current
                g_score[nb] = tentative
                f = tentative + manhattan(nb, goal)
                counter += 1
                heapq.heappush(open_heap, (f, counter, nb))

    return None


def reachable_any(
    start: Cell,
    goals: frozenset[Cell],
    cols: int,
    rows: int,
    obstacles: frozenset[Cell],
) -> bool:
    """BFS — does any goal cell remain reachable from start?"""
    if not goals:
        return False
    seen = {start}
    queue = [start]
    while queue:
        current = queue.pop()
        if current in goals:
            return True
        for nb in neighbours(current, cols, rows):
            if nb in seen or (nb in obstacles and nb not in goals):
                continue
            seen.add(nb)
            queue.append(nb)
    return False


def floodfill_size(
    start: Cell,
    cols: int,
    rows: int,
    obstacles: frozenset[Cell],
    cap: int | None = None,
) -> int:
    """Count cells reachable from `start` (including start), early-exit at cap."""
    seen = {start}
    queue = [start]
    while queue:
        current = queue.pop()
        if cap is not None and len(seen) >= cap:
            return len(seen)
        for nb in neighbours(current, cols, rows):
            if nb in seen or nb in obstacles:
                continue
            seen.add(nb)
            queue.append(nb)
    return len(seen)


def reachable_set(
    start: Cell,
    cols: int,
    rows: int,
    obstacles: frozenset[Cell],
) -> set[Cell]:
    """Full set of cells reachable from `start` (including start)."""
    seen = {start}
    queue = [start]
    while queue:
        current = queue.pop()
        for nb in neighbours(current, cols, rows):
            if nb in seen or nb in obstacles:
                continue
            seen.add(nb)
            queue.append(nb)
    return seen

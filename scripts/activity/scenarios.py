"""Adversarial fixture generators for the snake simulator.

Each generator returns a set[(col, row)] of filled cells on a `cols × rows` grid."""

from __future__ import annotations

import random

Cell = tuple[int, int]


def random_cells(n: int, cols: int, rows: int, seed: int) -> set[Cell]:
    rng = random.Random(seed)
    out: set[Cell] = set()
    while len(out) < n and len(out) < cols * rows:
        out.add((rng.randrange(cols), rng.randrange(rows)))
    return out


def spiral_cells(n: int, cols: int, rows: int, seed: int = 0) -> set[Cell]:
    """A spiral perimeter walk, taking the first n cells in spiral order."""
    visited: set[Cell] = set()
    order: list[Cell] = []
    top, bottom, left, right = 0, rows - 1, 0, cols - 1
    while top <= bottom and left <= right and len(order) < n:
        for c in range(left, right + 1):
            order.append((c, top))
        top += 1
        for r in range(top, bottom + 1):
            order.append((right, r))
        right -= 1
        if top <= bottom:
            for c in range(right, left - 1, -1):
                order.append((c, bottom))
            bottom -= 1
        if left <= right:
            for r in range(bottom, top - 1, -1):
                order.append((left, r))
            left += 1
    return set(order[:n])


def two_clusters(n: int, cols: int, rows: int, seed: int) -> set[Cell]:
    """Two dense clusters at opposite ends, snake must traverse the empty middle."""
    rng = random.Random(seed)
    half = n // 2
    out: set[Cell] = set()
    left_w = max(4, cols // 6)
    right_w = max(4, cols // 6)
    while len(out) < half:
        out.add((rng.randrange(left_w), rng.randrange(rows)))
    while len(out) < n:
        out.add((cols - 1 - rng.randrange(right_w), rng.randrange(rows)))
    return out


def edge_cells(n: int, cols: int, rows: int, seed: int) -> set[Cell]:
    """Cells biased toward the four edges — forces snake into corners."""
    rng = random.Random(seed)
    out: set[Cell] = set()
    while len(out) < n:
        if rng.random() < 0.5:
            out.add((rng.randrange(cols), rng.choice([0, rows - 1])))
        else:
            out.add((rng.choice([0, cols - 1]), rng.randrange(rows)))
    return out


def dense_band(n: int, cols: int, rows: int, seed: int) -> set[Cell]:
    """Cells concentrated in a horizontal band — invites the snake to coil."""
    rng = random.Random(seed)
    band_rows = [rows // 2 - 1, rows // 2, rows // 2 + 1]
    band_rows = [r for r in band_rows if 0 <= r < rows]
    out: set[Cell] = set()
    while len(out) < n:
        if rng.random() < 0.85:
            out.add((rng.randrange(cols), rng.choice(band_rows)))
        else:
            out.add((rng.randrange(cols), rng.randrange(rows)))
    return out


def checker(n: int, cols: int, rows: int, seed: int = 0) -> set[Cell]:
    """Checkerboard — every other cell, harder to navigate without crossing self."""
    out: list[Cell] = []
    for c in range(cols):
        for r in range(rows):
            if (c + r) % 2 == 0:
                out.append((c, r))
    return set(out[:n])


SCENARIOS = {
    "random": random_cells,
    "spiral": spiral_cells,
    "two_clusters": two_clusters,
    "edge": edge_cells,
    "dense_band": dense_band,
    "checker": checker,
}

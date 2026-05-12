"""Smoke test: build a grid from a scenario, run the simulator, render SVG."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from .scenarios import SCENARIOS
from .simulator import simulate
from .svg_render import render

COLS = 53
ROWS = 7
PALETTE_DARK = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
PALETTE_LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]


def make_grid(filled: set[tuple[int, int]], seed: int) -> list[list[int]]:
    """Synthetic intensity grid: filled cells get a random non-zero intensity."""
    rng = random.Random(seed)
    grid = [[0] * ROWS for _ in range(COLS)]
    for c, r in filled:
        grid[c][r] = rng.choices([1, 2, 3, 4], weights=[4, 3, 2, 1])[0]
    return grid


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=list(SCENARIOS), default="random")
    parser.add_argument("--cells", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cap", type=int, default=20)
    parser.add_argument("--out", type=str, default="assets/activity.svg")
    parser.add_argument("--palette", choices=["dark", "light"], default="dark")
    args = parser.parse_args()

    filled = SCENARIOS[args.scenario](args.cells, COLS, ROWS, args.seed)
    grid = make_grid(filled, args.seed)
    start = (0, 0)
    while start in filled:
        start = (start[0] + 1, start[1])

    result = simulate(COLS, ROWS, filled, start=start, max_body_length=args.cap)

    palette = PALETTE_DARK if args.palette == "dark" else PALETTE_LIGHT
    svg = render(COLS, ROWS, grid, result, palette)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding="utf-8")
    print(
        f"scenario={args.scenario} cells={len(filled)} eaten={result.eaten_count} "
        f"ticks={result.total_ticks} stalls={result.stalls} "
        f"bytes={len(svg)} → {out_path}",
        file=sys.stderr,
    )
    return 0 if result.eaten_count == len(filled) else 1


if __name__ == "__main__":
    raise SystemExit(main())

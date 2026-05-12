"""Run every scenario × seed × density combination and report completion rate."""

from __future__ import annotations

import argparse
import sys
import time

from .scenarios import SCENARIOS
from .simulator import simulate

COLS = 53
ROWS = 7


def run_one(scenario: str, cells: int, seed: int, cap: int | None) -> tuple[int, int, float, int]:
    filled = SCENARIOS[scenario](cells, COLS, ROWS, seed)
    start = (0, 0)
    while start in filled:
        start = (start[0] + 1, start[1])
    t0 = time.perf_counter()
    res = simulate(COLS, ROWS, filled, start=start, max_body_length=cap)
    elapsed = time.perf_counter() - t0
    return res.eaten_count, len(filled), elapsed, res.stalls


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--densities", type=str, default="30,50,80,120")
    parser.add_argument("--cap", type=int, default=None)
    args = parser.parse_args()

    densities = [int(x) for x in args.densities.split(",")]
    seeds = list(range(1, args.seeds + 1))

    print(f"# sweep — seeds={len(seeds)} densities={densities} cap={args.cap}")
    print(f"{'scenario':>15} {'cells':>6} {'completed':>10} {'rate':>6} {'avg_eaten':>10} {'avg_stalls':>11} {'avg_ms':>7}")

    overall_runs = 0
    overall_complete = 0

    for scenario in SCENARIOS:
        for cells in densities:
            completed = 0
            total_eaten = 0
            total_filled = 0
            total_stalls = 0
            total_elapsed = 0.0
            for seed in seeds:
                eaten, n, elapsed, stalls = run_one(scenario, cells, seed, args.cap)
                total_eaten += eaten
                total_filled += n
                total_stalls += stalls
                total_elapsed += elapsed
                if eaten == n:
                    completed += 1
            rate = completed / len(seeds) * 100
            avg_eaten = total_eaten / len(seeds)
            avg_stalls = total_stalls / len(seeds)
            avg_ms = total_elapsed / len(seeds) * 1000
            print(
                f"{scenario:>15} {cells:>6} {f'{completed}/{len(seeds)}':>10} {f'{rate:.0f}%':>6} "
                f"{avg_eaten:>10.1f} {avg_stalls:>11.1f} {avg_ms:>7.0f}"
            )
            overall_runs += len(seeds)
            overall_complete += completed

    print()
    print(f"# overall: {overall_complete}/{overall_runs} = {overall_complete/overall_runs*100:.1f}% complete")
    return 0 if overall_complete == overall_runs else 1


if __name__ == "__main__":
    raise SystemExit(main())

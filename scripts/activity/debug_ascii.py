"""ASCII visualiser + single-scenario runner."""

from __future__ import annotations

import argparse
import sys
import time

from .scenarios import SCENARIOS
from .simulator import SimResult, TickEvent, simulate

COLS = 53
ROWS = 7

CSI_HOME = "\x1b[H"
CSI_CLEAR = "\x1b[2J"
CSI_HIDE = "\x1b[?25l"
CSI_SHOW = "\x1b[?25h"


def render_frame(event: TickEvent, filled: set[tuple[int, int]], eaten: set[tuple[int, int]]) -> str:
    head = event.head
    body = set(event.body) - {head}
    lines = []
    for r in range(ROWS):
        row_chars = []
        for c in range(COLS):
            cell = (c, r)
            if cell == head:
                row_chars.append("H")
            elif cell in body:
                row_chars.append("o")
            elif cell in filled and cell not in eaten:
                row_chars.append("*")
            else:
                row_chars.append(".")
        lines.append(" ".join(row_chars))
    header = f"tick={event.tick:5d}  body={len(event.body):3d}  eaten={len(eaten):3d}  remaining={event.remaining:3d}"
    return header + "\n" + "\n".join(lines)


def play(result: SimResult, filled: set[tuple[int, int]], every: int, delay: float) -> None:
    sys.stdout.write(CSI_HIDE + CSI_CLEAR)
    try:
        eaten: set[tuple[int, int]] = set()
        for event in result.events:
            if event.eaten is not None:
                eaten.add(event.eaten)
            if event.tick % every != 0 and event.tick != result.total_ticks:
                continue
            sys.stdout.write(CSI_HOME + render_frame(event, filled, eaten) + "\n")
            sys.stdout.flush()
            time.sleep(delay)
    finally:
        sys.stdout.write(CSI_SHOW)
        sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=list(SCENARIOS), default="random")
    parser.add_argument("--cells", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--every", type=int, default=4)
    parser.add_argument("--delay", type=float, default=0.03)
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--cap", type=int, default=None, help="max body length")
    args = parser.parse_args()

    filled = SCENARIOS[args.scenario](args.cells, COLS, ROWS, args.seed)
    start = (0, 0)
    while start in filled:
        start = (start[0] + 1, start[1])

    print(
        f"# scenario={args.scenario} cells={len(filled)} seed={args.seed} cap={args.cap} start={start}",
        file=sys.stderr,
    )
    result = simulate(COLS, ROWS, filled, start=start, max_body_length=args.cap)

    if args.final:
        eaten = {ev.eaten for ev in result.events if ev.eaten is not None}
        print(render_frame(result.events[-1], filled, eaten))
    else:
        play(result, filled, args.every, args.delay)

    print(file=sys.stderr)
    print(f"# total ticks: {result.total_ticks}", file=sys.stderr)
    print(f"# cells eaten: {result.eaten_count} / {len(filled)}", file=sys.stderr)
    print(f"# final body length: {len(result.events[-1].body)}", file=sys.stderr)
    print(f"# stall steps: {result.stalls}", file=sys.stderr)
    if result.unreachable:
        print(f"# UNREACHABLE: {len(result.unreachable)} cells: {result.unreachable[:5]}...", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

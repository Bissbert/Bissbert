#!/usr/bin/env python3
"""Generate assets/activity.svg — a real snake AI that eats every cell in the
contribution grid. Fetches counts via GitHub GraphQL; falls back to deterministic
synthetic data if no token is set."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activity.simulator import simulate
from activity.svg_render import render

USER = os.environ.get("GH_USER", "Bissbert")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

COLS = 53
ROWS = 7
BODY_CAP = 20

PALETTE_DARK = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
PALETTE_LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]

SNAKE_DARK = ("#a78bfa", "#7c3aed")
SNAKE_LIGHT = ("#7c3aed", "#5b21b6")

QUERY = "query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{weeks{contributionDays{contributionCount weekday}}}}}}"


def fetch_grid() -> list[list[int]]:
    if not TOKEN:
        import random

        random.seed(42)
        return [
            [random.choices([0, 1, 2, 3, 4], weights=[5, 3, 2, 1, 1])[0] for _ in range(ROWS)]
            for _ in range(COLS)
        ]

    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"u": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"][-COLS:]
    grid = [[0] * ROWS for _ in range(COLS)]
    for col, week in enumerate(weeks):
        for day in week["contributionDays"]:
            grid[col][day["weekday"]] = day["contributionCount"]
    return grid


def intensity(c: int) -> int:
    if c == 0: return 0
    if c < 3:  return 1
    if c < 7:  return 2
    if c < 12: return 3
    return 4


def pick_start(filled: set[tuple[int, int]]) -> tuple[int, int]:
    for c in range(COLS):
        for r in range(ROWS):
            if (c, r) not in filled:
                return (c, r)
    return (0, 0)


def build(counts: list[list[int]], palette: list[str], snake: tuple[str, str]) -> str:
    intensity_grid = [[intensity(counts[c][r]) for r in range(ROWS)] for c in range(COLS)]
    filled = {(c, r) for c in range(COLS) for r in range(ROWS) if intensity_grid[c][r] > 0}

    if not filled:
        from activity.simulator import SimResult, TickEvent

        result = SimResult(events=[TickEvent(0, (0, 0), [(0, 0)], None, 0)], total_ticks=0)
    else:
        start = pick_start(filled)
        result = simulate(COLS, ROWS, filled, start=start, max_body_length=BODY_CAP)

    head, body = snake
    return render(COLS, ROWS, intensity_grid, result, palette, head_color=head, body_color=body)


def main() -> None:
    counts = fetch_grid()
    out_dir = Path(__file__).resolve().parent.parent / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)

    for suffix, palette, snake in [
        ("", PALETTE_DARK, SNAKE_DARK),
        ("-light", PALETTE_LIGHT, SNAKE_LIGHT),
    ]:
        svg = build(counts, palette, snake)
        out = out_dir / f"activity{suffix}.svg"
        out.write_text(svg, encoding="utf-8")
        print(f"Written: {out} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()

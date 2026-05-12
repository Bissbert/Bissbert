#!/usr/bin/env python3
"""Generate assets/activity.svg — a snake that strictly stays inside the 7-row
contribution grid (no off-grid travel lane). Fetches contribution counts via
GitHub GraphQL; falls back to deterministic synthetic data if no token."""

import json
import os
import urllib.request

USER = os.environ.get("GH_USER", "Bissbert")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

CELL = 12
STRIDE = 16
COLS = 53
ROWS = 7
WIDTH = 848
HEIGHT = 112

STEP_MS = 70
HOLD_MS = 1400

PALETTE_DARK = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
PALETTE_LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]

HEAD_COLOR = "#a78bfa"
BODY_COLOR = "#7c3aed"

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


def boustrophedon() -> list[tuple[int, int]]:
    path = []
    for col in range(COLS):
        rs = range(ROWS) if col % 2 == 0 else range(ROWS - 1, -1, -1)
        for row in rs:
            path.append((col, row))
    return path


def cellpos(col: int, row: int) -> tuple[int, int]:
    return 2 + col * STRIDE, 2 + row * STRIDE


def build(grid: list[list[int]], palette: list[str]) -> str:
    path = boustrophedon()
    N = len(path)
    total_ms = N * STEP_MS + HOLD_MS
    hold_frac = HOLD_MS / total_ms

    times = [i * (1 - hold_frac) / N for i in range(N)]
    times.append(1.0)
    key_times = ";".join(f"{t:.5f}" for t in times)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="Annual GitHub contribution grid scanned in-bounds by a snake.">'
    ]

    parts.append('<g shape-rendering="geometricPrecision">')
    for col in range(COLS):
        for row in range(ROWS):
            x, y = cellpos(col, row)
            fill = palette[intensity(grid[col][row])]
            parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" fill="{fill}"/>')
    parts.append('</g>')

    for seg in range(5):
        size = CELL - seg * 0.8
        off = (CELL - size) / 2
        opacity = 1.0 - seg * 0.18
        color = HEAD_COLOR if seg == 0 else BODY_COLOR

        xs, ys, opacs = [], [], []
        for i in range(N):
            j = i - seg
            if j < 0:
                x, y = cellpos(*path[0])
                xs.append(x + off)
                ys.append(y + off)
                opacs.append(0.0)
            else:
                x, y = cellpos(*path[j])
                xs.append(x + off)
                ys.append(y + off)
                opacs.append(opacity)
        xs.append(xs[-1])
        ys.append(ys[-1])
        opacs.append(opacs[-1])

        vx = ";".join(f"{v:.2f}" for v in xs)
        vy = ";".join(f"{v:.2f}" for v in ys)
        vo = ";".join(f"{v:.2f}" for v in opacs)

        parts.append(
            f'<rect width="{size:.2f}" height="{size:.2f}" rx="3" ry="3" fill="{color}" opacity="0">'
            f'<animate attributeName="x" values="{vx}" keyTimes="{key_times}" '
            f'dur="{total_ms}ms" repeatCount="indefinite" calcMode="discrete"/>'
            f'<animate attributeName="y" values="{vy}" keyTimes="{key_times}" '
            f'dur="{total_ms}ms" repeatCount="indefinite" calcMode="discrete"/>'
            f'<animate attributeName="opacity" values="{vo}" keyTimes="{key_times}" '
            f'dur="{total_ms}ms" repeatCount="indefinite" calcMode="discrete"/>'
            f'</rect>'
        )

    parts.append('</svg>')
    return "".join(parts)


def main() -> None:
    grid = fetch_grid()
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    os.makedirs(out_dir, exist_ok=True)

    for variant, palette in [("", PALETTE_DARK), ("-light", PALETTE_LIGHT)]:
        svg = build(grid, palette)
        out = os.path.join(out_dir, f"activity{variant}.svg")
        with open(out, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"Written: {out} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()

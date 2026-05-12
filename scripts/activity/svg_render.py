"""Render a SimResult to an animated SVG.

Layout: a 53×7 contribution-style grid. Cells with intensity>0 are "food".
The snake's head + body follow the simulator's event log. As cells are eaten,
their fill animates from the food colour to the background colour at the exact
tick the head landed on them. Everything uses SMIL `calcMode="discrete"` for
crisp grid-aligned motion."""

from __future__ import annotations

from .simulator import SimResult

CELL = 12
STRIDE = 16
LEFT_PAD = 2
TOP_PAD = 2

STEP_MS = 70
HOLD_MS = 1400

HEAD_COLOR = "#a78bfa"
BODY_COLOR = "#7c3aed"
NUM_SEGMENTS = 5


def cellpos(col: int, row: int) -> tuple[int, int]:
    return LEFT_PAD + col * STRIDE, TOP_PAD + row * STRIDE


def render(
    cols: int,
    rows: int,
    intensity_grid: list[list[int]],
    result: SimResult,
    palette: list[str],
    *,
    step_ms: int = STEP_MS,
    hold_ms: int = HOLD_MS,
    head_color: str = HEAD_COLOR,
    body_color: str = BODY_COLOR,
    num_segments: int = NUM_SEGMENTS,
) -> str:
    """Build an SVG string from the simulator's event log."""
    events = result.events
    if len(events) < 2:
        first = events[0] if events else None
        events = [first, first] if first else []
    if not events:
        raise ValueError("event log is empty — simulator produced no ticks")
    N = len(events) - 1

    total_ms = N * step_ms + hold_ms
    hold_frac = hold_ms / total_ms

    frame_kt = [i * (1 - hold_frac) / N for i in range(N + 1)]
    frame_kt_str = [f"{t:.5f}" for t in frame_kt]
    snake_key_times = ";".join(frame_kt_str) + ";1.00000"

    width = LEFT_PAD * 2 + cols * STRIDE - (STRIDE - CELL)
    height = TOP_PAD * 2 + rows * STRIDE - (STRIDE - CELL)

    eaten_at: dict[tuple[int, int], int] = {}
    for ev in events:
        if ev.eaten is not None and ev.eaten not in eaten_at:
            eaten_at[ev.eaten] = ev.tick

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Annual GitHub contribution grid being eaten cell-by-cell by a snake.">'
    ]

    parts.append('<g shape-rendering="geometricPrecision">')
    for col in range(cols):
        for row in range(rows):
            x, y = cellpos(col, row)
            ity = intensity_grid[col][row]
            fill = palette[ity]
            cell = (col, row)
            if cell in eaten_at and ity > 0:
                t_eat = eaten_at[cell]
                kt = frame_kt[t_eat]
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" fill="{fill}">'
                    f'<animate attributeName="fill" '
                    f'values="{fill};{palette[0]}" '
                    f'keyTimes="0;{kt:.5f}" '
                    f'dur="{total_ms}ms" repeatCount="indefinite" calcMode="discrete"/>'
                    f'</rect>'
                )
            else:
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" fill="{fill}"/>'
                )
    parts.append('</g>')

    for seg in range(num_segments):
        size = CELL - seg * 0.8
        off = (CELL - size) / 2
        opacity = 1.0 - seg * 0.18
        color = head_color if seg == 0 else body_color

        xs: list[float] = []
        ys: list[float] = []
        opacs: list[float] = []
        for ev in events:
            if seg < len(ev.body):
                c, r = ev.body[seg]
                x, y = cellpos(c, r)
                xs.append(x + off)
                ys.append(y + off)
                opacs.append(opacity)
            else:
                if xs:
                    xs.append(xs[-1])
                    ys.append(ys[-1])
                else:
                    x, y = cellpos(0, 0)
                    xs.append(x + off)
                    ys.append(y + off)
                opacs.append(0.0)
        xs.append(xs[-1])
        ys.append(ys[-1])
        opacs.append(opacs[-1])

        vx = ";".join(f"{v:.2f}" for v in xs)
        vy = ";".join(f"{v:.2f}" for v in ys)
        vo = ";".join(f"{v:.2f}" for v in opacs)

        parts.append(
            f'<rect width="{size:.2f}" height="{size:.2f}" rx="3" ry="3" fill="{color}" opacity="0">'
            f'<animate attributeName="x" values="{vx}" keyTimes="{snake_key_times}" '
            f'dur="{total_ms}ms" repeatCount="indefinite" calcMode="discrete"/>'
            f'<animate attributeName="y" values="{vy}" keyTimes="{snake_key_times}" '
            f'dur="{total_ms}ms" repeatCount="indefinite" calcMode="discrete"/>'
            f'<animate attributeName="opacity" values="{vo}" keyTimes="{snake_key_times}" '
            f'dur="{total_ms}ms" repeatCount="indefinite" calcMode="discrete"/>'
            f'</rect>'
        )

    parts.append('</svg>')
    return "".join(parts)

"""Snake simulator: pick-target → plan → step → eat → grow. Stays in-bounds.

Phase 2 planner:
  • Candidates are the K nearest remaining cells by Manhattan distance.
  • Each candidate is scored by `len(path) + α · (#remaining-unreachable-after)`.
    The unreachable-after penalty dominates the path cost (α=1000), so moves
    that partition the grid are rejected unless no alternative exists.
  • A move is *safe* iff after walking it, the head can still BFS-reach the
    tail through body[1:-1] and the floodfill region holds ≥ body_length cells.
  • When no safe target exists, the snake takes a tail-chase step toward its
    tail to buy time.

Optional `max_body_length` caps growth: once the body reaches the cap, the
tail keeps moving even on eats. This prevents long-body partitioning in dense
scenarios at the cost of an unbounded eat count without visible growth."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .pathfinder import (
    Cell,
    find_path,
    floodfill_size,
    manhattan,
    neighbours,
    reachable_any,
    reachable_set,
)

CANDIDATE_POOL = 12
PARTITION_PENALTY = 1000


@dataclass
class TickEvent:
    tick: int
    head: Cell
    body: list[Cell]
    eaten: Cell | None
    remaining: int


@dataclass
class SimResult:
    events: list[TickEvent] = field(default_factory=list)
    total_ticks: int = 0
    eaten_count: int = 0
    unreachable: list[Cell] = field(default_factory=list)
    stalls: int = 0


def _nearest_targets(head: Cell, targets: set[Cell], k: int) -> list[Cell]:
    return sorted(targets, key=lambda c: manhattan(head, c))[:k]


def _simulate_path(
    body: deque[Cell],
    path: list[Cell],
    remaining: set[Cell],
    max_body_length: int | None,
) -> tuple[deque[Cell], set[Cell]]:
    """Walk `body` along `path`, eating any `remaining` cell encountered."""
    sim = deque(body)
    eaten: set[Cell] = set()
    for cell in path:
        sim.appendleft(cell)
        grew = False
        if cell in remaining and cell not in eaten:
            eaten.add(cell)
            if max_body_length is None or len(sim) <= max_body_length:
                grew = True
        if not grew:
            sim.pop()
    return sim, eaten


def _is_safe(sim_body: deque[Cell], cols: int, rows: int) -> bool:
    """After a move, head must BFS-reach tail through body[1:-1], and the
    accessible region must hold at least body_length cells."""
    if len(sim_body) <= 2:
        return True

    head = sim_body[0]
    tail = sim_body[-1]
    inner_body = frozenset(list(sim_body)[1:-1])

    if not reachable_any(head, frozenset({tail}), cols, rows, inner_body):
        return False

    body_minus_head = frozenset(sim_body) - {head}
    space = floodfill_size(head, cols, rows, body_minus_head, cap=len(sim_body) + 2)
    return space >= len(sim_body)


def _score(
    path: list[Cell],
    sim_body: deque[Cell],
    new_remaining: set[Cell],
    cols: int,
    rows: int,
) -> int:
    """Lower is better. Heavy penalty per remaining cell unreachable after move."""
    cost = len(path)
    if not new_remaining:
        return cost

    new_head = sim_body[0]
    obstacles_excl_tail = frozenset(list(sim_body)[:-1])
    reachable = reachable_set(new_head, cols, rows, obstacles_excl_tail)
    unreachable = sum(1 for c in new_remaining if c not in reachable)
    return cost + unreachable * PARTITION_PENALTY


def _plan_target(
    head: Cell,
    body: deque[Cell],
    cols: int,
    rows: int,
    remaining: set[Cell],
    max_body_length: int | None,
) -> list[Cell] | None:
    """Score the K nearest candidates; return the best safe path."""
    obstacles = frozenset(list(body)[:-1])
    candidates = _nearest_targets(head, remaining, CANDIDATE_POOL)

    best: tuple[int, list[Cell]] | None = None
    for target in candidates:
        path = find_path(head, target, cols, rows, obstacles)
        if path is None:
            continue
        sim_body, eaten = _simulate_path(body, path, remaining, max_body_length)
        if not _is_safe(sim_body, cols, rows):
            continue
        new_remaining = remaining - eaten
        score = _score(path, sim_body, new_remaining, cols, rows)
        if best is None or score < best[0]:
            best = (score, path)
    return best[1] if best else None


def _tail_chase_step(
    head: Cell,
    body: deque[Cell],
    cols: int,
    rows: int,
) -> Cell | None:
    """Pick one neighbour cell that keeps the snake safe (tail-chase)."""
    if len(body) <= 1:
        return None
    blockers_excl_tail = frozenset(list(body)[:-1])
    tail = body[-1]

    best: tuple[int, Cell] | None = None
    for nb in neighbours(head, cols, rows):
        if nb in blockers_excl_tail:
            continue
        sim_body = deque(body)
        sim_body.appendleft(nb)
        sim_body.pop()
        if not _is_safe(sim_body, cols, rows):
            continue
        d = manhattan(nb, tail)
        key = (d, nb)
        if best is None or key > best:
            best = key
    return best[1] if best else None


def simulate(
    cols: int,
    rows: int,
    filled: set[Cell],
    start: Cell = (0, 0),
    max_ticks: int = 50_000,
    max_stalls: int = 200,
    max_body_length: int | None = None,
) -> SimResult:
    """Run the snake until all filled cells are eaten or it gives up."""
    result = SimResult()
    remaining = set(filled)
    remaining.discard(start)
    body: deque[Cell] = deque([start])
    head = start
    tick = 0
    consecutive_stalls = 0

    result.events.append(TickEvent(tick=0, head=head, body=list(body), eaten=None, remaining=len(remaining)))

    while remaining and tick < max_ticks:
        path = _plan_target(head, body, cols, rows, remaining, max_body_length)

        if path is None:
            stall_cell = _tail_chase_step(head, body, cols, rows)
            if stall_cell is None:
                result.unreachable = sorted(remaining)
                break
            path = [stall_cell]
            consecutive_stalls += 1
            result.stalls += 1
            if consecutive_stalls > max_stalls:
                result.unreachable = sorted(remaining)
                break
        else:
            consecutive_stalls = 0

        for cell in path:
            tick += 1
            body.appendleft(cell)
            ate: Cell | None = None
            if cell in remaining:
                ate = cell
                remaining.discard(cell)
                result.eaten_count += 1
                if max_body_length is not None and len(body) > max_body_length:
                    body.pop()
            else:
                body.pop()
            head = cell
            result.events.append(
                TickEvent(tick=tick, head=head, body=list(body), eaten=ate, remaining=len(remaining))
            )

    result.total_ticks = tick
    return result

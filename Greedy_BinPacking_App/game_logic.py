"""Round generation, placement validation, scoring, and a greedy baseline
for the 2D bin-packing intro game."""

import math
import random
from dataclasses import dataclass, field

BIN_WIDTH = 20
BIN_HEIGHT = 14

# Per-round difficulty schedule: item count and target total item area
# (as a fraction of bin area). Bin size stays fixed across rounds so
# utilization % is comparable round to round.
ITEM_COUNTS = {1: 6, 2: 8, 3: 10, 4: 12, 5: 15}
AREA_FRACTIONS = {1: 0.70, 2: 0.85, 3: 1.00, 4: 1.15, 5: 1.30}
SIZE_VARIANCE_BASE = 0.30
SIZE_VARIANCE_STEP = 0.15

# Profit color gradient: pale yellow (low profit) -> deep red (high profit).
_COLOR_LOW = (0xFF, 0xF3, 0xB0)
_COLOR_HIGH = (0xB3, 0x26, 0x1E)


def _profit_color(value: float, vmin: float, vmax: float) -> str:
    t = 0.5 if vmax <= vmin else (value - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))
    r = round(_COLOR_LOW[0] + t * (_COLOR_HIGH[0] - _COLOR_LOW[0]))
    g = round(_COLOR_LOW[1] + t * (_COLOR_HIGH[1] - _COLOR_LOW[1]))
    b = round(_COLOR_LOW[2] + t * (_COLOR_HIGH[2] - _COLOR_LOW[2]))
    return f"#{r:02x}{g:02x}{b:02x}"


@dataclass
class Item:
    id: int
    w: int
    h: int
    profit: int
    color: str

    @property
    def area(self) -> int:
        return self.w * self.h

    @property
    def density(self) -> float:
        return self.profit / self.area if self.area else 0.0


@dataclass
class PlacedItem:
    item: Item
    x: int
    y: int
    rotated: bool

    @property
    def w(self) -> int:
        return self.item.h if self.rotated else self.item.w

    @property
    def h(self) -> int:
        return self.item.w if self.rotated else self.item.h


@dataclass
class RoundState:
    round_idx: int
    bin_w: int
    bin_h: int
    items: list  # list[Item], not yet placed/skipped
    all_items: list = field(default_factory=list)  # full original set, never mutated
    placed: list = field(default_factory=list)  # list[PlacedItem]
    skipped_ids: set = field(default_factory=set)
    start_time: float = None


def generate_round(round_idx: int, rng: random.Random) -> RoundState:
    """Procedurally generate a round's item set. Difficulty (item count,
    total area pressure, size variance) increases with round_idx."""
    bin_area = BIN_WIDTH * BIN_HEIGHT
    n = ITEM_COUNTS[round_idx]
    target_area = bin_area * AREA_FRACTIONS[round_idx]
    avg_item_area = target_area / n
    variance = SIZE_VARIANCE_BASE + SIZE_VARIANCE_STEP * (round_idx - 1)

    raw = []  # (w, h, area, profit) before color assignment
    for _ in range(n):
        area = rng.normalvariate(avg_item_area, avg_item_area * variance)
        area = max(2, min(area, bin_area * 0.35))
        aspect = rng.uniform(0.4, 2.5)
        w = math.sqrt(area * aspect)
        h = area / w
        w = int(max(1, min(BIN_WIDTH, round(w))))
        h = int(max(1, min(BIN_HEIGHT, round(h))))
        # Profit is loosely tied to area but with enough spread that
        # "biggest first" and "best value first" are different strategies.
        profit = max(1, round(w * h * rng.uniform(0.6, 2.4)))
        raw.append((w, h, profit))

    profits = [p for _, _, p in raw]
    vmin, vmax = min(profits), max(profits)

    items = [
        Item(id=i, w=w, h=h, profit=profit, color=_profit_color(profit, vmin, vmax))
        for i, (w, h, profit) in enumerate(raw)
    ]

    return RoundState(round_idx=round_idx, bin_w=BIN_WIDTH, bin_h=BIN_HEIGHT, items=list(items), all_items=items)


def rects_overlap(x1, y1, w1, h1, x2, y2, w2, h2) -> bool:
    return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)


def place_item(round_state: RoundState, item: Item, x: int, y: int, rotated: bool) -> None:
    """Place an item from the queue into the bin at the given position.

    Placement is unconditional — overlaps and out-of-bounds spots are
    allowed. Feasibility (and therefore scoring) is only checked when the
    round ends, via is_feasible().
    """
    round_state.placed.append(PlacedItem(item=item, x=x, y=y, rotated=rotated))
    round_state.items = [it for it in round_state.items if it.id != item.id]


def move_placed_item(round_state: RoundState, item_id: int, x: int, y: int, rotated: bool) -> None:
    """Reposition an already-placed item (drag within the bin)."""
    for p in round_state.placed:
        if p.item.id == item_id:
            p.x = x
            p.y = y
            p.rotated = rotated
            return


def remove_placed_item(round_state: RoundState, item_id: int) -> None:
    """Pull a placed item back out of the bin and return it to the queue."""
    for p in round_state.placed:
        if p.item.id == item_id:
            round_state.placed.remove(p)
            round_state.items.append(p.item)
            return


def skip_item(round_state: RoundState, item_id: int) -> None:
    round_state.items = [it for it in round_state.items if it.id != item_id]
    round_state.skipped_ids.add(item_id)


def is_feasible(round_state: RoundState) -> bool:
    """True if every placed item is in-bounds and nothing overlaps."""
    placed = round_state.placed
    for p in placed:
        if p.x < 0 or p.y < 0 or p.x + p.w > round_state.bin_w or p.y + p.h > round_state.bin_h:
            return False
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            a, b = placed[i], placed[j]
            if rects_overlap(a.x, a.y, a.w, a.h, b.x, b.y, b.w, b.h):
                return False
    return True


def compute_utilization(round_state: RoundState) -> float:
    packed_area = sum(p.w * p.h for p in round_state.placed)
    bin_area = round_state.bin_w * round_state.bin_h
    return min(100.0, 100.0 * packed_area / bin_area)


def compute_profit(round_state: RoundState) -> int:
    return sum(p.item.profit for p in round_state.placed)


def greedy_profit_density_baseline(items, bin_w: int, bin_h: int):
    """Reference greedy heuristic: sort items by profit-per-area (value
    density) descending, then place each in the first shelf it fits —
    the same idea behind the fractional-knapsack greedy, applied here as
    a simple shelf packer. Returns (profit, utilization_pct)."""
    sorted_items = sorted(items, key=lambda it: it.density, reverse=True)
    shelves = []  # each: {"h": shelf_height, "x_used": x}
    y_cursor = 0
    placed_area = 0
    placed_profit = 0

    for it in sorted_items:
        placed = False
        for ow, oh in ((it.w, it.h), (it.h, it.w)):
            if ow > bin_w:
                continue
            for shelf in shelves:
                if oh <= shelf["h"] and shelf["x_used"] + ow <= bin_w:
                    shelf["x_used"] += ow
                    placed_area += ow * oh
                    placed_profit += it.profit
                    placed = True
                    break
            if placed:
                break
        if placed:
            continue

        for ow, oh in ((it.w, it.h), (it.h, it.w)):
            if ow > bin_w or oh > (bin_h - y_cursor):
                continue
            shelves.append({"h": oh, "x_used": ow})
            y_cursor += oh
            placed_area += ow * oh
            placed_profit += it.profit
            placed = True
            break

    bin_area = bin_w * bin_h
    utilization = min(100.0, 100.0 * placed_area / bin_area)
    return placed_profit, utilization

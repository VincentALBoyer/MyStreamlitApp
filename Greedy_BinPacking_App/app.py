"""Greedy Heuristics Intro Game — 2D Bin Packing.

A short classroom minigame: drag items into a single fixed bin to capture
as much profit as possible, across 5 rounds that get progressively harder.
There's no way to compute the true optimal layout by hand (2D bin packing
is NP-hard), so students naturally fall back on an intuitive rule of thumb
— biggest first, best value-per-area first, etc. That rule of thumb *is* a
greedy heuristic, which is the hook for the graded write-up that follows
this session.
"""

import random
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bin_component import bin_packer
from game_logic import (
    RoundState,
    compute_profit,
    compute_utilization,
    generate_round,
    greedy_profit_density_baseline,
    is_feasible,
    move_placed_item,
    place_item,
    remove_placed_item,
    skip_item,
)

N_ROUNDS = 5

st.set_page_config(page_title="Greedy Bin Packing", layout="wide")


def init_game():
    st.session_state.game = {
        "phase": "intro",
        "round_idx": 1,
        "round_state": None,
        "round_results": [],
        "last_drop_sig": None,
        "strategy_text": "",
    }


if "game" not in st.session_state:
    init_game()

game = st.session_state.game


def start_round(round_idx: int):
    rs = generate_round(round_idx, random.Random())
    rs.start_time = time.time()
    game["round_state"] = rs
    game["last_drop_sig"] = None


def finish_round():
    rs: RoundState = game["round_state"]
    for it in list(rs.items):
        skip_item(rs, it.id)
    elapsed = time.time() - rs.start_time
    feasible = is_feasible(rs)
    utilization = compute_utilization(rs)
    profit = compute_profit(rs) if feasible else 0
    potential_profit = sum(it.profit for it in rs.all_items)
    baseline_profit, baseline_utilization = greedy_profit_density_baseline(
        rs.all_items, rs.bin_w, rs.bin_h
    )
    game["round_results"].append(
        {
            "round": rs.round_idx,
            "feasible": feasible,
            "profit": profit,
            "potential_profit": potential_profit,
            "baseline_profit": baseline_profit,
            "utilization": utilization,
            "baseline_utilization": baseline_utilization,
            "time_sec": elapsed,
            "items_placed": len(rs.placed),
            "items_total": len(rs.all_items),
        }
    )
    if feasible:
        st.toast(f"Round {rs.round_idx} complete — {profit}/{potential_profit} profit captured.")
    else:
        st.toast(f"Round {rs.round_idx} complete — scored 0 (layout was infeasible).", icon="⚠️")

    if rs.round_idx < N_ROUNDS:
        start_round(rs.round_idx + 1)
        game["round_idx"] = rs.round_idx + 1
        game["phase"] = "playing"
    else:
        game["phase"] = "final"


def render_bin_packer(rs: RoundState):
    items_payload = [
        {"id": it.id, "w": it.w, "h": it.h, "profit": it.profit, "color": it.color}
        for it in rs.items
    ]
    placed_payload = [
        {
            "id": p.item.id, "x": p.x, "y": p.y, "w": p.w, "h": p.h,
            "rotated": p.rotated, "color": p.item.color,
        }
        for p in rs.placed
    ]
    return bin_packer(
        bin_w=rs.bin_w, bin_h=rs.bin_h,
        items=items_payload, placed=placed_payload,
        key=f"bin_packer_r{rs.round_idx}",
    )


st.title("📦 Greedy Bin Packing")

if game["phase"] == "intro":
    st.markdown(
        """
### The challenge

You have **one fixed bin**. Items arrive for each round — drag them from
the list on the left and drop them into the bin. You can drag a placed
item again later to reposition it. There are **5 rounds**, and each one
is harder than the last.

Overlaps and out-of-bounds placements are allowed while you're playing —
but if your layout still has any when the round ends, that round scores
**0 profit**, no matter what you packed.

Each item has a **profit** (its color — pale to deep red — tells you how
valuable it is; hover an item to see the exact numbers) and a size. There's
no way to work out the perfect layout by hand here (packing rectangles
into a bin for maximum value is a genuinely hard problem) — so just go
with your gut. Whatever rule of thumb you end up using without thinking
about it too hard — biggest first? most valuable first? — is worth
remembering. You'll be asked to describe it afterwards.

**Scoring:** your score is the total profit of everything you packed,
across all 5 rounds. Your total time is tracked too.
        """
    )
    if st.button("Start", type="primary"):
        game["phase"] = "playing"
        start_round(1)
        st.rerun()

elif game["phase"] == "playing":
    rs: RoundState = game["round_state"]
    st.subheader(f"Round {rs.round_idx} of {N_ROUNDS}")
    elapsed = time.time() - rs.start_time
    c1, c2, c3 = st.columns(3)
    c1.metric("Elapsed", f"{elapsed:.0f}s")
    c2.metric("Profit so far", compute_profit(rs))
    c3.metric("Utilization", f"{compute_utilization(rs):.0f}%")

    feasible = is_feasible(rs)
    if not feasible:
        st.warning(
            "Some items overlap or hang outside the bin. That's allowed while you "
            "play — drag placed items to fix them — but if it's still like this "
            "when the round ends, you'll score 0 for this round."
        )

    st.caption(
        "Drag a card from the list into the bin — or drag a placed item to move it. "
        "Click the ⟳ on a card to rotate it before dragging. Hover a card to see its "
        "profit and size."
    )

    drop = render_bin_packer(rs)

    if drop:
        sig = (drop.get("source"), drop.get("remove"), drop["item_id"], drop["x"], drop["y"], drop["rotated"])
        if sig != game["last_drop_sig"]:
            game["last_drop_sig"] = sig
            if drop.get("remove"):
                remove_placed_item(rs, drop["item_id"])
            elif drop.get("source") == "placed":
                move_placed_item(rs, drop["item_id"], drop["x"], drop["y"], drop["rotated"])
            else:
                item = next((it for it in rs.items if it.id == drop["item_id"]), None)
                if item is not None:
                    place_item(rs, item, drop["x"], drop["y"], drop["rotated"])
            st.rerun()

    next_label = "See final report" if rs.round_idx == N_ROUNDS else "Next round"
    if feasible:
        if st.button(next_label, type="primary"):
            finish_round()
            st.rerun()
    else:
        confirm = st.checkbox(
            "I understand this round will score 0 profit because of the overlap/out-of-bounds items above",
            key=f"confirm_infeasible_r{rs.round_idx}",
        )
        if st.button(next_label, type="primary", disabled=not confirm):
            finish_round()
            st.rerun()

elif game["phase"] == "final":
    st.subheader("🏁 Final report")
    df = pd.DataFrame(game["round_results"])
    total_score = df["profit"].sum()
    total_time = df["time_sec"].sum()
    avg_utilization = df["utilization"].mean()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total score (profit)", int(total_score))
    c2.metric("Total time", f"{total_time:.0f}s")
    c3.metric("Avg. utilization", f"{avg_utilization:.0f}%")

    st.dataframe(
        df.rename(columns={
            "round": "Round", "profit": "Your profit", "baseline_profit": "Greedy baseline profit",
            "potential_profit": "Potential profit", "utilization": "Utilization (%)",
            "time_sec": "Time (s)", "items_placed": "Items placed", "items_total": "Items offered",
            "feasible": "Feasible",
        })[[
            "Round", "Feasible", "Your profit", "Greedy baseline profit", "Potential profit",
            "Utilization (%)", "Time (s)", "Items placed", "Items offered",
        ]],
        hide_index=True, width="stretch",
    )

    fig = go.Figure()
    fig.add_bar(x=df["round"], y=df["profit"], name="Your profit")
    fig.add_bar(x=df["round"], y=df["baseline_profit"], name="Greedy baseline profit")
    fig.update_layout(
        barmode="group", xaxis_title="Round", yaxis_title="Profit",
        height=350, margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig, width="stretch")

    st.markdown("### Describe your strategy")
    st.caption(
        "This is the part that gets graded. Think about how you decided *which* "
        "item to drag next, and *where* — that decision rule is a greedy heuristic, "
        "whether or not you were thinking of it that way."
    )
    game["strategy_text"] = st.text_area(
        "What rule(s) did you follow?", value=game["strategy_text"], height=150,
    )

    report_lines = [
        "Greedy Bin Packing — Results",
        f"Total score (profit): {int(total_score)}",
        f"Total time: {total_time:.0f}s",
        f"Average utilization: {avg_utilization:.0f}%",
        "",
        "Round-by-round:",
    ]
    for _, row in df.iterrows():
        feasible_note = "" if row["feasible"] else " [INFEASIBLE — scored 0]"
        report_lines.append(
            f"  Round {int(row['round'])}: {int(row['profit'])} profit{feasible_note} "
            f"(greedy baseline {int(row['baseline_profit'])}, potential {int(row['potential_profit'])}), "
            f"{row['utilization']:.0f}% utilization, {row['time_sec']:.0f}s, "
            f"{int(row['items_placed'])}/{int(row['items_total'])} items placed"
        )
    report_lines += ["", "Strategy description:", game["strategy_text"] or "(not yet written)"]
    report_text = "\n".join(report_lines)

    st.download_button(
        "Download report", data=report_text,
        file_name="greedy_bin_packing_report.txt", mime="text/plain",
    )

    if st.button("Play again"):
        init_game()
        st.rerun()

import os
os.environ.pop("SSLKEYLOGFILE", None)

import time

import pandas as pd
import streamlit as st

import game_logic as gl
import plotting as pl

st.set_page_config(page_title="Exhaustive vs Local Search", page_icon="🎯", layout="wide")

TOTAL_ROUNDS = len(gl.ROUND_XMAX)
MAX_POSSIBLE_SCORE = 1000 * TOTAL_ROUNDS
EXHAUSTIVE_FIXED_SCORE = round(1000 * gl.QUALITY_WEIGHT)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
def init_state():
    defaults = {
        "phase": "intro",
        "game_code": "",
        "seed": None,
        "rounds": None,
        "round_idx": 0,
        "round_results": [],
        "mode": None,
        "revealed": {},
        "round_start": None,
        "game_start": None,
        "ls_current_x": None,
        "ls_started": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def start_game(code: str, mode: str):
    seed_code = code.strip() or gl.new_game_code()
    st.session_state.game_code = seed_code.upper()
    st.session_state.seed = gl.code_to_seed(seed_code)
    st.session_state.rounds = gl.generate_all_rounds(st.session_state.seed)
    st.session_state.round_idx = 0
    st.session_state.round_results = []
    st.session_state.game_start = time.time()
    begin_round(mode)
    st.session_state.phase = "playing"


def begin_round(mode: str):
    st.session_state.mode = mode
    st.session_state.revealed = {}
    st.session_state.round_start = time.time()
    st.session_state.ls_current_x = None
    st.session_state.ls_started = False


def finish_round(found_y: float):
    ys = st.session_state.rounds[st.session_state.round_idx]
    evaluations = len(st.session_state.revealed)
    result = gl.score_round(found_y, ys, evaluations)
    result.update({
        "round": st.session_state.round_idx + 1,
        "mode": st.session_state.mode,
        "n_points": len(ys),
        "evaluations": evaluations,
        "found_y": found_y,
        "time": time.time() - st.session_state.round_start,
    })
    st.session_state.round_results.append(result)
    st.session_state.phase = "debrief"


def next_round_or_finish():
    if st.session_state.round_idx < TOTAL_ROUNDS - 1:
        st.session_state.round_idx += 1
        begin_round(st.session_state.mode)
        st.session_state.phase = "playing"
    else:
        st.session_state.phase = "final"


def reveal_exhaustive(x: int, ys: list):
    st.session_state.revealed[x] = ys[x]
    if len(st.session_state.revealed) == len(ys):
        finish_round(min(st.session_state.revealed.values()))


def start_local_search(x: int, ys: list):
    revealed = st.session_state.revealed
    revealed[x] = ys[x]
    for nb in (x - 1, x + 1):
        if 0 <= nb < len(ys):
            revealed[nb] = ys[nb]
    st.session_state.ls_current_x = x
    st.session_state.ls_started = True


def move_local_search(new_x: int, ys: list):
    revealed = st.session_state.revealed
    going_left = new_x < st.session_state.ls_current_x
    if new_x not in revealed:
        revealed[new_x] = ys[new_x]
    far = new_x - 1 if going_left else new_x + 1
    if 0 <= far < len(ys) and far not in revealed:
        revealed[far] = ys[far]
    st.session_state.ls_current_x = new_x


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def clicked_x(event):
    """Extract the x-value of a chart click from a plotly on_select event, or
    None if nothing was clicked this run."""
    try:
        points = event["selection"]["points"]
    except (TypeError, KeyError):
        return None
    if not points:
        return None
    return int(points[0]["x"])


def render_exhaustive(xmax: int, ys: list):
    revealed = st.session_state.revealed
    n_points = xmax + 1
    best_x = min(revealed, key=revealed.get) if revealed else None

    fig = pl.build_live_chart(xmax, revealed, mode="exhaustive", best_x=best_x)
    event = st.plotly_chart(
        fig, width="stretch", key=f"chart_ex_{st.session_state.round_idx}_{len(revealed)}",
        on_select="rerun", selection_mode="points",
    )

    m1, m2 = st.columns(2)
    m1.metric("Evaluations", f"{len(revealed)} / {n_points}")
    m2.metric("Best so far", f"{min(revealed.values()):.2f}" if revealed else "—")
    st.caption("Click any unrevealed point on the chart to evaluate f(x) there — every point must be checked.")

    x = clicked_x(event)
    if x is not None and 0 <= x <= xmax and x not in revealed:
        reveal_exhaustive(x, ys)
        st.rerun()


def render_local_search(xmax: int, ys: list):
    revealed = st.session_state.revealed
    n_points = xmax + 1

    if not st.session_state.ls_started:
        fig = pl.build_live_chart(xmax, revealed, mode="local")
        event = st.plotly_chart(
            fig, width="stretch", key=f"chart_ls_start_{st.session_state.round_idx}",
            on_select="rerun", selection_mode="points",
        )
        st.caption("Click anywhere on the chart to choose your starting point.")

        x = clicked_x(event)
        if x is not None and 0 <= x <= xmax:
            start_local_search(x, ys)
            st.rerun()
        return

    current_x = st.session_state.ls_current_x
    current_y = revealed[current_x]
    left_x, right_x = current_x - 1, current_x + 1
    improving = set()
    if left_x >= 0 and gl.is_improving(revealed[left_x], current_y):
        improving.add(left_x)
    if right_x <= xmax and gl.is_improving(revealed[right_x], current_y):
        improving.add(right_x)

    fig = pl.build_live_chart(
        xmax, revealed, mode="local", current_x=current_x, improving_xs=improving,
    )
    event = st.plotly_chart(
        fig, width="stretch",
        key=f"chart_ls_{st.session_state.round_idx}_{len(revealed)}_{current_x}",
        on_select="rerun", selection_mode="points",
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Current position", f"x = {current_x}")
    m2.metric("Current value", f"{current_y:.2f}")
    m3.metric("Evaluations", f"{len(revealed)} / {n_points}")

    if not improving:
        st.success(f"🏁 Local optimum reached at x={current_x} — neither neighbor is better. Round complete!")
        if st.button("See round results ▶", type="primary"):
            finish_round(current_y)
            st.rerun()
        return

    st.caption("Click the highlighted neighbor on the chart to move there.")
    x = clicked_x(event)
    if x is not None and x in improving:
        move_local_search(x, ys)
        st.rerun()
    elif x is not None:
        st.toast("That point isn't a strictly better neighbor — pick a highlighted point instead.", icon="⚠️")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
init_state()

with st.sidebar:
    st.markdown("### 🎯 Search Strategies Minigame")
    st.caption("IN2041 · Session 2 companion — Exhaustive vs. Local Search")
    if st.session_state.phase != "intro":
        st.divider()
        st.metric("Game code", st.session_state.game_code)
        if st.button("↺ Restart"):
            st.session_state.phase = "intro"
            st.rerun()

if st.session_state.phase == "intro":
    st.title("🎯 Exhaustive vs. Local Search")
    st.caption("A companion minigame for IN2041 Session 2 — Searching Strategies for Optimization")
    st.markdown(
        "Each round hides a function **f(x)** behind a wall of unrevealed points, and you try "
        "to land on the lowest value. The x-axis **grows every round**, just like the "
        "combinatorial explosion of solutions we discussed in class. Pick your strategy once "
        "below — you'll play **all 5 rounds** with it."
    )
    with st.expander("How scoring works", expanded=False):
        st.markdown(f"""
- **Exhaustive search** evaluates every point, so it always finds the true best value —
  but it never earns an efficiency bonus. Its score is therefore always a fixed
  **{EXHAUSTIVE_FIXED_SCORE} points** per round: guaranteed, never impressive.
- **Local search** starts wherever you pick and only moves to a neighbor that's *strictly*
  better than where you are. It stops the instant neither neighbor improves — that's a
  **local optimum**, which may or may not be the **global** one.
- Each round's score = 65% **solution quality** (how close your result is to the true best)
  + 35% **efficiency** (how few points you had to reveal), scaled to 1000. Local search can
  beat exhaustive's fixed score by converging fast — or fall short if it gets trapped.
""")

    mode_choice = st.radio(
        "Strategy for all 5 rounds", ["Exhaustive Search", "Local Search"], horizontal=True,
    )
    st.caption(
        "Exhaustive: click every point one by one — guaranteed to find the best, costs the most evaluations."
        if mode_choice == "Exhaustive Search" else
        "Local Search: pick a start, step to a strictly better neighbor each time — stops at the first local optimum."
    )
    code = st.text_input(
        "Game code (optional)", value="", placeholder="Leave blank for a random code", max_chars=12,
        help="Use the same code as a classmate to play on identical landscapes.",
    )
    if st.button("▶ Start Game", type="primary"):
        start_game(code, "exhaustive" if mode_choice == "Exhaustive Search" else "local")
        st.rerun()

elif st.session_state.phase == "playing":
    idx = st.session_state.round_idx
    xmax = gl.ROUND_XMAX[idx]
    n_points = xmax + 1
    ys = st.session_state.rounds[idx]

    strategy_label = "Exhaustive" if st.session_state.mode == "exhaustive" else "Local Search"
    top = st.columns([2, 1.2, 0.9, 0.9])
    top[0].subheader(f"Round {idx + 1} / {TOTAL_ROUNDS} — x from 0 to {xmax} ({n_points} points)")
    top[1].metric("Strategy", strategy_label)
    total_score_so_far = sum(r["score"] for r in st.session_state.round_results)
    top[2].metric("Score so far", f"{total_score_so_far}")
    top[3].metric("Total time", f"{time.time() - st.session_state.game_start:.0f}s")
    st.progress(idx / TOTAL_ROUNDS)
    st.divider()

    if st.session_state.mode == "exhaustive":
        render_exhaustive(xmax, ys)
    else:
        render_local_search(xmax, ys)

elif st.session_state.phase == "debrief":
    idx = st.session_state.round_idx
    ys = st.session_state.rounds[idx]
    result = st.session_state.round_results[-1]

    global_idx = min(range(len(ys)), key=lambda i: ys[i])
    local_idxs = set(gl.local_minima_indices(ys)) - {global_idx}
    player_x = global_idx if result["mode"] == "exhaustive" else st.session_state.ls_current_x

    st.subheader(f"Round {idx + 1} results — {'Exhaustive' if result['mode'] == 'exhaustive' else 'Local'} Search")

    if player_x == global_idx:
        st.success("🎉 You found the **global optimum**!")
    else:
        st.warning(f"🪤 You landed on a **local optimum** at x={player_x}. The global minimum was at x={global_idx}.")

    fig = pl.build_debrief_chart(ys, global_idx, local_idxs, player_x)
    st.plotly_chart(fig, width="stretch", key=f"debrief_{idx}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Evaluations used", f"{result['evaluations']} / {result['n_points']}")
    c2.metric("Quality", f"{result['quality'] * 100:.0f}%")
    c3.metric("Efficiency", f"{result['efficiency'] * 100:.0f}%")
    c4.metric("Round score", result["score"])
    st.caption(f"Round time: {result['time']:.1f}s")

    label = "Next Round ▶" if idx < TOTAL_ROUNDS - 1 else "See Final Results 🏁"
    if st.button(label, type="primary"):
        next_round_or_finish()
        st.rerun()

elif st.session_state.phase == "final":
    st.title("🏁 Game Complete!")

    total_score = sum(r["score"] for r in st.session_state.round_results)
    total_time = sum(r["time"] for r in st.session_state.round_results)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Score", f"{total_score} / {MAX_POSSIBLE_SCORE}")
    c2.metric("Total Time", f"{total_time:.1f}s")
    c3.metric("Game Code", st.session_state.game_code)
    st.caption("Share this game code with a classmate to compare results on the exact same 5 landscapes.")

    df = pd.DataFrame(st.session_state.round_results)
    df_display = df[["round", "mode", "n_points", "evaluations", "quality", "efficiency", "score", "time"]].copy()
    df_display["mode"] = df_display["mode"].map({"exhaustive": "Exhaustive", "local": "Local Search"})
    df_display["quality"] = (df_display["quality"] * 100).round(0).astype(int).astype(str) + "%"
    df_display["efficiency"] = (df_display["efficiency"] * 100).round(0).astype(int).astype(str) + "%"
    df_display["time"] = df_display["time"].round(1)
    df_display.columns = ["Round", "Strategy", "Points", "Evaluations", "Quality", "Efficiency", "Score", "Time (s)"]
    st.dataframe(df_display, width="stretch", hide_index=True)

    c1, c2 = st.columns(2)
    if c1.button("🔁 Replay Same Code", width="stretch"):
        start_game(st.session_state.game_code, st.session_state.mode)
        st.rerun()
    if c2.button("🎲 New Random Landscapes", width="stretch"):
        start_game("", st.session_state.mode)
        st.rerun()
    st.caption("Both replay with the same strategy you just used. Use ↺ Restart in the sidebar to pick a different strategy or code.")

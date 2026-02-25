import streamlit as st
import time
import pandas as pd
from instances import KNAPSACK_INSTANCES, PMEDIAN_INSTANCES
from solver_utils import calculate_knapsack_stats, calculate_p_median_stats

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Metaheuristics Challenge",
    page_icon="🏆",
    layout="wide",
)

# --- CUSTOM CSS ---
def local_css():
    st.markdown(
        """
        <style>
        .stButton>button {
            width: 100%;
            border-radius: 8px;
            height: 3em;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .main {
            background-color: transparent;
        }
        [data-testid="stMetricValue"] {
            font-size: 24px;
        }
        .stat-card {
            background-color: rgba(128, 128, 128, 0.1);
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid rgba(128, 128, 128, 0.2);
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )

local_css()

# --- STATE MANAGEMENT ---
if "phase" not in st.session_state:
    st.session_state.phase = "setup"  # setup, game, final
if "problem_type" not in st.session_state:
    st.session_state.problem_type = "knapsack"
if "mode" not in st.session_state:
    st.session_state.mode = "easy"
if "instance_index" not in st.session_state:
    st.session_state.instance_index = 0
if "results" not in st.session_state:
    st.session_state.results = []  # list of (fitness, time)
if "start_time" not in st.session_state:
    st.session_state.start_time = 0
if "current_selection" not in st.session_state:
    st.session_state.current_selection = set()

# --- HELPERS ---
def start_challenge():
    st.session_state.phase = "game"
    st.session_state.instance_index = 0
    st.session_state.results = []
    st.session_state.start_time = time.time()
    st.session_state.current_selection = set()

def next_instance(fitness, duration):
    st.session_state.results.append({"fitness": fitness, "time": duration})
    if st.session_state.instance_index < 9:
        st.session_state.instance_index += 1
        st.session_state.current_selection = set()
    else:
        st.session_state.phase = "final"

def reset():
    st.session_state.phase = "setup"

# --- UI: SETUP ---
if st.session_state.phase == "setup":
    st.title("🏆 Metaheuristics Optimization Challenge")
    st.markdown("### Prepare for the race! Solve 10 instances as fast as possible.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.problem_type = st.selectbox(
            "Select Problem Type",
            ["knapsack", "p-median"],
            format_func=lambda x: "Knapsack Problem" if x == "knapsack" else "p-Median Problem"
        )
    with col2:
        st.session_state.mode = st.radio(
            "Select Difficulty",
            ["easy", "hard"],
            help="Easy: Shows additional metrics (ratios/assignment costs). Hard: Raw data only."
        )
    
    st.write("---")
    if st.button("🚀 START CHALLENGE"):
        start_challenge()
        st.rerun()

# --- UI: GAME ---
elif st.session_state.phase == "game":
    idx = st.session_state.instance_index
    instances = KNAPSACK_INSTANCES if st.session_state.problem_type == "knapsack" else PMEDIAN_INSTANCES
    instance = instances[idx]
    
    # Progress Header
    cols = st.columns([2, 1, 1])
    with cols[0]:
        st.subheader(f"Instance {idx + 1} / 10")
    with cols[1]:
        elapsed = time.time() - st.session_state.start_time
        st.metric("Total Time", f"{elapsed:.1f}s")
    with cols[2]:
        progress = (idx) / 10
        st.progress(progress)
    
    st.write("---")

    if st.session_state.problem_type == "knapsack":
        items = instance["items"]
        capacity = instance["capacity"]
        
        # Prepare data for display
        df_items = pd.DataFrame(items)
        df_items["Selected"] = [item["id"] in st.session_state.current_selection for item in items]
        if st.session_state.mode == "easy":
            df_items["ratio (v/w)"] = (df_items["v"] / df_items["w"]).round(2)
        
        # Reorder columns for better UX
        cols_to_show = ["Selected", "id", "v", "w"]
        if st.session_state.mode == "easy":
            cols_to_show.append("ratio (v/w)")
        df_items = df_items[cols_to_show]

        st.markdown("#### Select Items (Click headers to sort)")
        
        # Data Editor for selection
        edited_df = st.data_editor(
            df_items,
            column_config={
                "Selected": st.column_config.CheckboxColumn(
                    "Select",
                    help="Pick this item",
                    default=False,
                ),
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "v": st.column_config.NumberColumn("Value (Fitness)", disabled=True),
                "w": st.column_config.NumberColumn("Weight", disabled=True),
                "ratio (v/w)": st.column_config.NumberColumn("Ratio", disabled=True),
            },
            disabled=["id", "v", "w", "ratio (v/w)"],
            hide_index=True,
            key="knapsack_editor"
        )

        # Update selection state
        new_selection = set(edited_df[edited_df["Selected"]]["id"])
        if new_selection != st.session_state.current_selection:
            st.session_state.current_selection = new_selection
            st.rerun()

        stats = calculate_knapsack_stats(st.session_state.current_selection, items, capacity)
        
        # Dashboard stats
        c1, c2, c3 = st.columns(3)
        c1.metric("Current Value (Fitness)", stats["value"])
        c2.metric("Used Capacity", f"{stats['weight']} / {capacity}")
        c3.metric("Feasibility", "✅ OK" if stats["is_feasible"] else "❌ OVERLOAD")

        if not stats["is_feasible"]:
            st.warning("⚠️ Capacity exceeded! Please unselect items to proceed.")

        st.write("---")
        if st.button("NEXT INSTANCE", type="primary", disabled=not stats["is_feasible"]):
            next_instance(stats["value"], elapsed)
            st.rerun()

    elif st.session_state.problem_type == "p-median":
        cities = instance["cities"]
        p = instance["p"]
        stats = calculate_p_median_stats(st.session_state.current_selection, cities)
        
        # Prepare data for display
        df_cities = pd.DataFrame(cities)
        df_cities["Selected"] = [city["id"] in st.session_state.current_selection for city in cities]
        if st.session_state.mode == "easy":
            df_cities["Cost (Dist to Nearest)"] = [stats["nearest_distances"].get(c["id"], 0) for c in cities]
            df_cities["Cost (Dist to Nearest)"] = df_cities["Cost (Dist to Nearest)"].round(1)
        
        cols_to_show = ["Selected", "id", "x", "y"]
        if st.session_state.mode == "easy":
            cols_to_show.append("Cost (Dist to Nearest)")
        df_cities = df_cities[cols_to_show]

        st.markdown(f"#### Select {p} Facilities (Click headers to sort)")

        # Data Editor for selection
        edited_df = st.data_editor(
            df_cities,
            column_config={
                "Selected": st.column_config.CheckboxColumn(
                    "Select",
                    help="Mark city as facility",
                    default=False,
                ),
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "x": st.column_config.NumberColumn("X Coord", disabled=True),
                "y": st.column_config.NumberColumn("Y Coord", disabled=True),
                "Cost (Dist to Nearest)": st.column_config.NumberColumn("Assignment Cost", disabled=True),
            },
            disabled=["id", "x", "y", "Cost (Dist to Nearest)"],
            hide_index=True,
            key="pmedian_editor"
        )

        # Update selection state
        new_selection = set(edited_df[edited_df["Selected"]]["id"])
        if new_selection != st.session_state.current_selection:
            st.session_state.current_selection = new_selection
            st.rerun()
        
        # Dashboard stats
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Distance (Fitness)", f"{stats['total_distance']:.2f}")
        c2.metric("Facilities", f"{len(st.session_state.current_selection)} / {p}")
        
        is_feasible = len(st.session_state.current_selection) == p
        status_msg = "✅ OK" if is_feasible else f"Select {p} facilities"
        c3.metric("Feasibility", status_msg)

        if len(st.session_state.current_selection) > p:
            st.error(f"⚠️ Too many facilities! You must select EXACTLY {p}.")
        elif len(st.session_state.current_selection) < p:
            st.info(f"ℹ️ Select {p - len(st.session_state.current_selection)} more facilities.")

        st.write("---")
        if st.button("NEXT INSTANCE", type="primary", disabled=not is_feasible):
            next_instance(stats["total_distance"], elapsed)
            st.rerun()

# --- UI: FINAL ---
elif st.session_state.phase == "final":
    st.title("🏁 Challenge Completed!")
    
    total_time = time.time() - st.session_state.start_time
    # Note: total_time here is accurate because game runs continuously
    
    avg_fitness = sum(r["fitness"] for r in st.session_state.results) / 10
    
    c1, c2 = st.columns(2)
    c1.metric("Average Fitness", f"{avg_fitness:.2f}")
    c2.metric("Total Time", f"{total_time:.1f}s")
    
    st.write("---")
    st.markdown("#### Detailed Results")
    st.table(pd.DataFrame(st.session_state.results))
    
    if st.button("RESTART"):
        reset()
        st.rerun()

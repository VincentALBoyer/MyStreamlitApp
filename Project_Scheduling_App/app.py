import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
sys.path.append(os.path.dirname(__file__))

from logic import SchedulingLogic, Task, Worker
from custom_scheduler import drag_and_drop_scheduler
import datetime

# --- Page Config ---
st.set_page_config(
    page_title="Project Scheduler Pro",
    page_icon="📅",
    layout="wide",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .main {
        background-color: #0f1116;
        color: #e0e0e0;
    }
    .task-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.3s ease;
    }
    .task-card:hover {
        border-color: #00ffcc;
        transform: translateY(-2px);
        background: rgba(255, 255, 255, 0.08);
    }
    .worker-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 20px;
        color: white;
        font-weight: bold;
    }
    .skill-tag {
        background: #2563eb;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.7em;
        margin-right: 5px;
    }
    .precedence-tag {
        background: #9333ea;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.7em;
        margin-right: 5px;
    }
    .makespan-stat {
        font-size: 2em;
        font-weight: bold;
        color: #00ffcc;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- State Management ---
if 'logic' not in st.session_state:
    st.session_state.logic = SchedulingLogic()

logic = st.session_state.logic

# --- Header ---
st.title("🚀 Project Scheduler Pro")
st.markdown("Optimize your team's workflow and minimize the project makespan.")

# --- Sidebar Stats ---
with st.sidebar:
    st.header("📊 Dashboard")
    makespan = logic.get_makespan()
    st.markdown(f"<div class='makespan-stat'>{makespan}h</div>", unsafe_allow_html=True)
    st.caption("Current Total Duration")
    
    st.divider()
    
    unassigned = logic.get_unassigned_tasks()
    st.metric("Pending Tasks", f"{len(unassigned)}")
    
    st.divider()
    
    if st.button("🔄 Reset Project"):
        logic.reset_game()
        st.rerun()
    
    st.divider()
    
    with st.expander("📖 How to Play"):
        st.write("""
        1. **Goal**: Finish all projects in the minimum time.
        2. **Tasks**: Each task has skill requirements and may depend on other tasks.
        3. **Workers**: Each team member has unique skills.
        4. **Strategy**: Check the Gantt chart to identify bottlenecks!
        """)
        
    st.divider()
    st.subheader("🛠 Skills Matrix")
    for w_id, w in logic.workers.items():
        st.write(f"**{w.name}**: {', '.join(w.skills)}")

# --- Stats Bar ---
proj_stats = logic.get_project_stats()
stat_cols = st.columns(len(proj_stats))
for i, (p_name, stats) in enumerate(proj_stats.items()):
    with stat_cols[i]:
        progress = stats["done"] / stats["total"]
        st.write(f"**{p_name}**")
        st.progress(progress)
        st.caption(f"{stats['done']}/{stats['total']} Tasks Assigned")

st.divider()

# --- Interactive Scheduling Board ---
st.subheader("🎮 Interactive Scheduling Board")
st.markdown("Drag and drop tasks between the pool and team members. Check the tooltips for logic warnings!")

# This component is visual-only in this turn as bidirectional communication 
# is limited in pure HTML components, but it provides the requested interaction.
drag_and_drop_scheduler(logic)

st.divider()

# --- Main Layout (Legacy/Fallback) ---
with st.expander("🛠 Manual Assignment Panel (Fallback)"):
    col_unassigned, col_workers = st.columns([1, 2.5])
    
    with col_unassigned:
        st.subheader("📋 Unassigned Tasks")
        tasks = logic.get_unassigned_tasks()
        
        if not tasks:
            st.success("All tasks assigned!")
        
        for task in tasks:
            with st.container():
                st.markdown(f"""
                <div class="task-card">
                    <div style="font-weight:bold; color: #60a5fa;">{task.name}</div>
                    <div style="font-size: 0.8em; margin-top: 5px;">
                        <span style="color: #94a3b8;">Proj: {task.project}</span> | 
                        <span style="color: #94a3b8;">Dur: {task.duration}h</span>
                    </div>
                    <div style="margin-top: 8px;">
                        {' '.join([f'<span class="skill-tag">{s}</span>' for s in task.skills_required])}
                    </div>
                    {f'<div style="margin-top: 5px;">' + ' '.join([f'<span class="precedence-tag">After {logic.tasks[p].name}</span>' for p in task.predecessors if p in logic.tasks]) + '</div>' if task.predecessors else ''}
                </div>
                """, unsafe_allow_html=True)
                
                # Assignment Controls
                worker_display = {w_id: f"{w.name} ({', '.join(w.skills)})" for w_id, w in logic.workers.items()}
                worker_ids = list(logic.workers.keys())
                
                selected_worker_id = st.selectbox(
                    f"Assign {task.name} to:", 
                    options=["Select..."] + worker_ids,
                    format_func=lambda x: worker_display.get(x, x),
                    key=f"sel_{task.id}", 
                    label_visibility="collapsed"
                )
                
                if selected_worker_id != "Select...":
                    if logic.assign_task(task.id, selected_worker_id):
                        st.success(f"Assigned to {logic.workers[selected_worker_id].name}")
                        st.rerun()
                    else:
                        st.error("Skill Mismatch!")

    with col_workers:
        st.subheader("👥 Current Team Assignments")
        
        worker_cols = st.columns(len(logic.workers))
        
        for idx, (w_id, worker) in enumerate(logic.workers.items()):
            with worker_cols[idx]:
                st.markdown(f"<div class='worker-header'>{worker.name}</div>", unsafe_allow_html=True)
                
                assigned_tasks = logic.get_worker_assignments(w_id)
                for t in assigned_tasks:
                    with st.container():
                        st.markdown(f"""
                        <div class="task-card" style="border-left: 5px solid #3b82f6;">
                            <div style="font-weight:bold;">{t.name}</div>
                            <div style="font-size: 0.7em; color: #94a3b8;">
                                Time: {t.start_time if t.start_time is not None else '?'} - {t.end_time if t.end_time is not None else '?'}h
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"✖ Deassign", key=f"de_{t.id}_{w_id}", use_container_width=True):
                            logic.deassign_task(t.id)
                            st.rerun()

# --- Gantt Chart ---
st.divider()
st.subheader("📅 Project Timeline (Gantt)")

all_assigned = [t for t in logic.tasks.values() if t.start_time is not None]

if all_assigned:
    df = []
    for t in all_assigned:
        df.append({
            "Task": t.name,
            "Start": t.start_time,
            "Finish": t.end_time,
            "Worker": logic.workers[t.assigned_worker].name,
            "Project": t.project
        })
    df_plot = pd.DataFrame(df)
    
    # We use number based start/finish for Plotly Timeline or just a bar chart
    fig = px.bar(df_plot, 
                 base="Start", 
                 x=df_plot["Finish"] - df_plot["Start"], 
                 y="Worker", 
                 color="Project",
                 orientation='h', 
                 hover_data=["Task"],
                 title="Team Schedule Timeline")
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#e0e0e0',
        xaxis_title="Time (hours)",
        yaxis_title="Team Member",
        xaxis_gridcolor='rgba(255,255,255,0.1)',
        yaxis_gridcolor='rgba(255,255,255,0.1)'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    if len(all_assigned) == len(logic.tasks):
        st.balloons()
        st.success(f"🎊 All projects completed in {makespan} hours!")
else:
    st.info("Assign tasks to see the project timeline.")

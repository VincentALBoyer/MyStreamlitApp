"""
Utility module for the Project Scheduler Pro Jupyter Notebook
Contains all the logic and HTML generation for the interactive scheduler.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json

@dataclass
class Task:
    id: str
    name: str
    project: str
    duration: int  # in hours
    skills_required: List[str]
    predecessors: List[str] = field(default_factory=list)
    assigned_worker: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None

@dataclass
class Worker:
    id: str
    name: str
    skills: List[str]

class SchedulingLogic:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.workers: Dict[str, Worker] = {}
        self.reset_game()

    def reset_game(self):
        # Sample workers
        self.workers = {
            "W1": Worker("W1", "Alice", ["Frontend", "Design"]),
            "W2": Worker("W2", "Bob", ["Backend", "Database"]),
            "W3": Worker("W3", "Charlie", ["Backend", "Frontend"]),
            "W4": Worker("W4", "Diana", ["Testing", "Documentation"]),
        }

        # 3 Independent Projects
        self.tasks = {
            # Project Alpha: Diamond Structure
            "T1": Task("T1", "Project Discovery", "Project Alpha", 4, ["Design"]),
            "T2": Task("T2", "Backend Core", "Project Alpha", 6, ["Backend"], ["T1"]),
            "T3": Task("T3", "UI Layout", "Project Alpha", 5, ["Frontend"], ["T1"]),
            "T4": Task("T4", "Final Review", "Project Alpha", 4, ["Testing"], ["T2", "T3"]),

            # Project Beta: Sequential
            "T5": Task("T5", "DB Architecture", "Project Beta", 3, ["Database"]),
            "T6": Task("T6", "API Integration", "Project Beta", 8, ["Backend"], ["T5"]),
            "T7": Task("T7", "Beta Testing", "Project Beta", 4, ["Testing"], ["T6"]),

            # Project Gamma: Simple
            "T8": Task("T8", "Asset Design", "Project Gamma", 6, ["Design"]),
            "T9": Task("T9", "Documentation", "Project Gamma", 3, ["Documentation"], ["T8"]),
        }


def create_scheduler_html(logic_data):
    """
    Generate the interactive drag-and-drop scheduler HTML.
    
    Args:
        logic_data: SchedulingLogic instance with tasks and workers
        
    Returns:
        HTML string for the interactive scheduler
    """
    # Prepare data for JavaScript
    tasks_json = json.dumps({t_id: {
        "id": t_id,
        "name": t.name,
        "duration": t.duration,
        "skills": t.skills_required,
        "predecessors": t.predecessors,
        "project": t.project,
        "worker": t.assigned_worker,
        "start_time": t.start_time
    } for t_id, t in logic_data.tasks.items()})
    
    workers_json = json.dumps({w_id: {
        "id": w_id,
        "name": w.name,
        "skills": w.skills
    } for w_id, w in logic_data.workers.items()})

    html_code = f"""
    <div id="scheduler-root" style="font-family: 'Inter', sans-serif; color: #e0e0e0; background: #0f1116; padding: 20px; border-radius: 15px;">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
            :root {{
                --hour-width: 40px;
                --total-hours: 24;
            }}
            .pool-container {{
                background: rgba(255, 255, 255, 0.03);
                border: 1px dashed rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                min-height: 80px;
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                padding: 15px;
                margin-bottom: 20px;
            }}
            .timeline-container {{
                overflow-x: auto;
                padding-bottom: 15px;
            }}
            .ruler {{
                display: flex;
                margin-left: 150px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
                padding-bottom: 5px;
                margin-bottom: 10px;
            }}
            .ruler-hour {{
                width: var(--hour-width);
                flex-shrink: 0;
                font-size: 10px;
                color: #475569;
                text-align: center;
            }}
            .worker-lanes {{
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}
            .lane-row {{
                display: flex;
                align-items: stretch;
                gap: 0;
            }}
            .worker-label {{
                width: 150px;
                padding-right: 15px;
                font-weight: 600;
                color: #60a5fa;
                font-size: 0.9em;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }}
            .lane {{
                flex-shrink: 0;
                width: calc(var(--hour-width) * var(--total-hours));
                background: linear-gradient(90deg, 
                    rgba(255,255,255,0.02) 1px, transparent 1px);
                background-size: var(--hour-width) 100%;
                background-color: rgba(255, 255, 255, 0.04);
                border-radius: 4px;
                min-height: 100px;
                position: relative;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
            .task-block {{
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px;
                cursor: grab;
                user-select: none;
                position: absolute;
                height: 80px;
                top: 10px;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                justify-content: center;
                transition: background 0.2s, border-color 0.2s;
                overflow: hidden;
            }}
            .pool-task {{
                position: static !important;
                height: auto;
                width: auto !important;
                min-width: 100px;
            }}
            .task-block:hover {{
                border-color: #00ffcc;
                z-index: 10;
            }}
            .task-name {{ font-weight: bold; font-size: 0.8em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .task-info {{ font-size: 0.6em; color: #94a3b8; }}
            
            .warning-overlap {{ border-color: #ef4444 !important; background: rgba(239, 68, 68, 0.2) !important; }}
            .warning-precedence {{ border-color: #f59e0b !important; border-style: dashed !important; }}
            .warning-skill {{ background: rgba(236, 72, 153, 0.2) !important; }}
            
            .tooltip {{
                position: absolute;
                bottom: 105%;
                left: 50%;
                transform: translateX(-50%);
                background: #000;
                color: #fff;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 9px;
                white-space: nowrap;
                visibility: hidden;
                pointer-events: none;
                opacity: 0.9;
                z-index: 100;
            }}
            .task-block:hover .tooltip {{ visibility: visible; }}
        </style>

        <h4 style="margin-top:0; color:#94a3b8;">📋 Task Pool</h4>
        <div id="pool" class="pool-container"></div>

        <h4 style="color:#94a3b8; display: flex; justify-content: space-between; align-items: center;">
            <span>📅 Timeline (Drag tasks to specific hours)</span>
            <span id="makespan-display" style="color: #00ffcc; font-size: 1.2em;">Makespan: 0h</span>
        </h4>
        <div class="timeline-container">
            <div id="ruler" class="ruler"></div>
            <div id="lanes" class="worker-lanes"></div>
        </div>

        <div style="margin-top: 20px; padding: 12px; background: rgba(255,255,255,0.03); border-radius: 8px; font-size: 0.75em; display: flex; gap: 20px;">
            <span><strong style="color: #ef4444;">Red Background:</strong> Overlap Warning</span>
            <span><strong style="color: #f59e0b;">Dashed Border:</strong> Precedence Error</span>
            <span><strong style="color: #ec4899;">Pink Background:</strong> Skill Mismatch</span>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/interactjs/dist/interact.min.js"></script>
        <script>
            const tasks = {tasks_json};
            const workers = {workers_json};
            const HOUR_WIDTH = 40;
            
            const projectColors = {{
                'Project Alpha': 'rgba(59, 130, 246, 0.2)',
                'Project Beta': 'rgba(16, 185, 129, 0.2)',
                'Project Gamma': 'rgba(139, 92, 246, 0.2)',
                'Default': 'rgba(107, 114, 128, 0.2)'
            }};
            const projectBorderColors = {{
                'Project Alpha': '#3b82f6',
                'Project Beta': '#10b981',
                'Project Gamma': '#8b5cf6',
                'Default': '#6b7280'
            }};

            const poolEl = document.getElementById('pool');
            const lanesEl = document.getElementById('lanes');
            const rulerEl = document.getElementById('ruler');

            function createTaskEl(task) {{
                const div = document.createElement('div');
                div.className = 'task-block';
                div.id = task.id;
                div.dataset.duration = task.duration;
                div.style.width = (task.duration * HOUR_WIDTH) + 'px';
                
                const bgColor = projectColors[task.project] || projectColors['Default'];
                const borderColor = projectBorderColors[task.project] || projectBorderColors['Default'];
                div.style.backgroundColor = bgColor;
                div.style.borderColor = borderColor;
                
                const skillNames = task.skills.join(', ');
                const skillHtml = `<div class="task-info" style="color: #60a5fa;">Skills: ${{skillNames}}</div>`;
                
                const predNames = task.predecessors.map(pId => tasks[pId] ? tasks[pId].name : pId).join(', ');
                const predHtml = predNames ? `<div class="task-info" style="color: #cbd5e1; font-style: italic;">Need: ${{predNames}}</div>` : '';

                div.innerHTML = `
                    <div class="task-name">${{task.name}}</div>
                    <div class="task-info">${{task.duration}}h | ${{task.project}}</div>
                    ${{skillHtml}}
                    ${{predHtml}}
                    <div class="tooltip" id="tooltip-${{task.id}}">Ready</div>
                `;
                return div;
            }}

            // Create Ruler
            for(let i=0; i<=24; i++) {{
                const hour = document.createElement('div');
                hour.className = 'ruler-hour';
                hour.innerText = i + 'h';
                rulerEl.appendChild(hour);
            }}

            // Create Tasks
            Object.values(tasks).forEach(t => {{
                const el = createTaskEl(t);
                if (!t.worker) {{
                    el.classList.add('pool-task');
                    poolEl.appendChild(el);
                }}
            }});

            // Create Workers and Lanes
            Object.values(workers).forEach(w => {{
                const row = document.createElement('div');
                row.className = 'lane-row';
                row.innerHTML = `<div class="worker-label">${{w.name}}<br><small style="color:#475569; font-weight:normal;">${{w.skills.slice(0,2).join(', ')}}</small></div>`;
                
                const lane = document.createElement('div');
                lane.className = 'lane';
                lane.id = `lane-${{w.id}}`;
                lane.dataset.workerId = w.id;
                
                row.appendChild(lane);
                lanesEl.appendChild(row);

                // Add existing tasks if any
                Object.values(tasks).filter(t => t.worker === w.id).forEach(t => {{
                    const el = createTaskEl(t);
                    el.style.left = (t.start_time || 0) * HOUR_WIDTH + 'px';
                    lane.appendChild(el);
                }});
            }});

            // Drag and Drop
            interact('.task-block').draggable({{
                listeners: {{
                    move(event) {{
                        const target = event.target;
                        const x = (parseFloat(target.getAttribute('data-x')) || 0) + event.dx;
                        const y = (parseFloat(target.getAttribute('data-y')) || 0) + event.dy;
                        target.style.transform = `translate(${{x}}px, ${{y}}px)`;
                        target.setAttribute('data-x', x);
                        target.setAttribute('data-y', y);
                    }},
                    end(event) {{
                        const target = event.target;
                        target.style.transform = 'none';
                        target.removeAttribute('data-x');
                        target.removeAttribute('data-y');
                    }}
                }}
            }});

            interact('.lane').dropzone({{
                accept: '.task-block',
                overlap: 0.1,
                ondrop(event) {{
                    const taskEl = event.relatedTarget;
                    const laneEl = event.target;
                    
                    const rect = laneEl.getBoundingClientRect();
                    const dropX = event.dragEvent.client.x - rect.left;
                    let startHour = Math.round(dropX / HOUR_WIDTH);
                    startHour = Math.max(0, Math.min(startHour, 24 - parseInt(taskEl.dataset.duration)));
                    
                    taskEl.classList.remove('pool-task');
                    taskEl.style.left = (startHour * HOUR_WIDTH) + 'px';
                    laneEl.appendChild(taskEl);
                    
                    tasks[taskEl.id].worker = laneEl.dataset.workerId;
                    tasks[taskEl.id].start_time = startHour;
                    tasks[taskEl.id].end_time = startHour + tasks[taskEl.id].duration;
                    
                    checkLogic();
                }}
            }});

            interact('.pool-container').dropzone({{
                accept: '.task-block',
                ondrop(event) {{
                    const taskEl = event.relatedTarget;
                    taskEl.classList.add('pool-task');
                    taskEl.style.left = 'auto';
                    event.target.appendChild(taskEl);
                    
                    tasks[taskEl.id].worker = null;
                    tasks[taskEl.id].start_time = null;
                    checkLogic();
                }}
            }});

            function checkLogic() {{
                const laneEls = document.querySelectorAll('.lane');
                
                Object.values(tasks).forEach(t => {{
                    const el = document.getElementById(t.id);
                    if(el) el.classList.remove('warning-overlap', 'warning-precedence', 'warning-skill');
                    const tooltip = document.getElementById('tooltip-' + t.id);
                    if(tooltip) tooltip.innerText = 'OK';
                }});

                laneEls.forEach(lane => {{
                    const worker = workers[lane.dataset.workerId];
                    const laneTasks = Array.from(lane.children).map(el => tasks[el.id]);
                    laneTasks.sort((a,b) => a.start_time - b.start_time);

                    for (let i = 0; i < laneTasks.length; i++) {{
                        const t = laneTasks[i];
                        const el = document.getElementById(t.id);
                        const tooltip = document.getElementById('tooltip-' + t.id);

                        if (!t.skills.some(s => worker.skills.includes(s))) {{
                            el.classList.add('warning-skill');
                            tooltip.innerText = 'Skill Mismatch';
                        }}

                        if (i > 0) {{
                            const prev = laneTasks[i-1];
                            if (t.start_time < prev.end_time) {{
                                el.classList.add('warning-overlap');
                                document.getElementById(prev.id).classList.add('warning-overlap');
                                tooltip.innerText = 'Time Overlap!';
                            }}
                        }}

                        t.predecessors.forEach(pId => {{
                            const pred = tasks[pId];
                            if (!pred.worker) {{
                                el.classList.add('warning-precedence');
                                tooltip.innerText = 'Pred. not assigned';
                            }} else if (pred.end_time > t.start_time) {{
                                el.classList.add('warning-precedence');
                                tooltip.innerText = 'Starts before Pred. ends';
                            }}
                        }});
                    }}
                }});
                
                updateMakespan();
            }}
            
            function updateMakespan() {{
                let maxEndTime = 0;
                Object.values(tasks).forEach(t => {{
                    if (t.end_time && t.end_time > maxEndTime) {{
                        maxEndTime = t.end_time;
                    }}
                }});
                document.getElementById('makespan-display').innerText = `Makespan: ${{maxEndTime}}h`;
            }}
            
            checkLogic();
        </script>
    </div>
    """
    return html_code

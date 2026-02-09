# Project Scheduling Simulation

An educational Streamlit application designed to help students understand the complexities of project scheduling, resource management, and the Critical Path Method (CPM).

## Features
- **Multiple Projects**: Manage tasks across "Project Alpha", "Project Beta", and shared tasks.
- **Precedence Constraints**: Tasks are linked; some cannot start until others are finished.
- **Skill-Based Assignment**: Workers have specific skills (Frontend, Backend, etc.). Tasks can only be assigned to qualified personnel.
- **Dynamic Scheduling**: The app automatically calculates the earliest possible start and finish times for every task.
- **Gantt Chart Visualization**: Real-time feedback on the team's load and project timeline.
- **Goal-Oriented**: Students strive to minimize the total makespan (completion time).

## How to Run
From the root directory:
```bash
streamlit run Project_Scheduling_App/app.py
```

## Setup
Ensure you have the following installed:
- streamlit
- pandas
- plotly
- dataclasses (Python 3.7+)

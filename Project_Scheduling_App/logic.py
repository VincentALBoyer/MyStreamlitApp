import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import datetime

@dataclass
class Task:
    id: str
    name: str
    project: str
    duration: int  # in hours or days
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
        # Sample Data
        self.workers = {
            "W1": Worker("W1", "Alice", ["Frontend", "Design"]),
            "W2": Worker("W2", "Bob", ["Backend", "Database"]),
            "W3": Worker("W3", "Charlie", ["Backend", "Frontend"]),
            "W4": Worker("W4", "Diana", ["Testing", "Documentation"]),
        }

        # Project A: Web App
        # Project B: Data Pipeline
        self.tasks = {
            "T1": Task("T1", "UI Design", "Project Alpha", 4, ["Design"]),
            "T2": Task("T2", "API Development", "Project Alpha", 6, ["Backend"], ["T1"]),
            "T3": Task("T3", "Frontend Integration", "Project Alpha", 5, ["Frontend"], ["T2"]),
            "T4": Task("T4", "Database Schema", "Project Beta", 3, ["Database"]),
            "T5": Task("T5", "Data Ingestion", "Project Beta", 8, ["Backend"], ["T4"]),
            "T6": Task("T6", "Unit Testing", "Shared", 4, ["Testing"], ["T3", "T5"]),
        }

    def assign_task(self, task_id: str, worker_id: str) -> bool:
        if task_id not in self.tasks or worker_id not in self.workers:
            return False
        
        task = self.tasks[task_id]
        worker = self.workers[worker_id]
        
        # Check if worker has required skills
        if not any(skill in worker.skills for skill in task.skills_required):
            return False
            
        task.assigned_worker = worker_id
        return True

    def deassign_task(self, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].assigned_worker = None

    def calculate_schedule(self):
        """
        Calculates the start and end times for all assigned tasks based on worker availability 
        and precedence constraints.
        """
        # Clear previous calculation
        for t in self.tasks.values():
            t.start_time = None
            t.end_time = None
            
        assigned_tasks = [t for t in self.tasks.values() if t.assigned_worker]
        
        # Simple simulation to find timelines
        # worker_busy_until tracks when each worker is free
        worker_busy_until: Dict[str, int] = {w_id: 0 for w_id in self.workers}
        
        # We need to process tasks in topological order based on predecessors
        # but also restricted by worker availability.
        
        pending = list(assigned_tasks)
        completed = set()
        
        # Add tasks with no predecessors or whose predecessors are not in the assigned list (e.g. they won't be completed in this session if not assigned)
        # Actually, for the simulation to work, all tasks in a chain SHOULD be assigned.
        # If a predecessor is NOT assigned, we assume it's NOT DONE and subsequent tasks can't start.
        
        # To simplify: only calculate for assigned tasks. If a task has an unassigned predecessor, it can't start.
        
        iteration_limit = 100
        while pending and iteration_limit > 0:
            iteration_limit -= 1
            changed = False
            
            for task in pending[:]:
                # Check if all predecessors are completed
                preds_ready = True
                max_pred_finish = 0
                for pred_id in task.predecessors:
                    if pred_id in self.tasks:
                        p = self.tasks[pred_id]
                        if p.end_time is not None:
                            max_pred_finish = max(max_pred_finish, p.end_time)
                        else:
                            # Predecessor not assigned or not yet scheduled
                            preds_ready = False
                            break
                
                if preds_ready:
                    # Task can start at the later of:
                    # 1. When all predecessors are finished
                    # 2. When the assigned worker is free
                    start = max(max_pred_finish, worker_busy_until[task.assigned_worker])
                    task.start_time = start
                    task.end_time = start + task.duration
                    
                    worker_busy_until[task.assigned_worker] = task.end_time
                    completed.add(task.id)
                    pending.remove(task)
                    changed = True
            
            if not changed:
                break # Circular dependency or unassigned predecessors
                
        return max(worker_busy_until.values()) if worker_busy_until else 0

    def get_makespan(self) -> int:
        return self.calculate_schedule()

    def get_unassigned_tasks(self) -> List[Task]:
        return [t for t in self.tasks.values() if t.assigned_worker is None]

    def get_worker_assignments(self, worker_id: str) -> List[Task]:
        assigned = [t for t in self.tasks.values() if t.assigned_worker == worker_id]
        # Sort by start time if available
        return sorted(assigned, key=lambda x: x.start_time if x.start_time is not None else 999)

    def get_project_stats(self) -> Dict:
        projects = {}
        for t in self.tasks.values():
            if t.project not in projects:
                projects[t.project] = {"total": 0, "done": 0}
            projects[t.project]["total"] += 1
            if t.assigned_worker:
                projects[t.project]["done"] += 1
        return projects

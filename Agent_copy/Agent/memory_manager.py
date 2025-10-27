import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class MemoryManager:
    def __init__(self, storage_file: str = "task_memory.json"):
        self.storage_file = storage_file
        self.tasks = self._load_tasks()
    
    def _load_tasks(self) -> List[Dict]:
        """Load tasks from storage file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
        return []
    
    def _save_tasks(self):
        """Save tasks to storage file"""
        with open(self.storage_file, 'w') as f:
            json.dump(self.tasks, f, indent=2, default=str)
    
    def store_task(self, task_input: str, result: Dict, complexity: str = "Medium", priority: str = "Medium"):
        """Store a new task and its result"""
        task_data = {
            'id': len(self.tasks) + 1,
            'input': task_input,
            'result': result,
            'complexity': complexity,
            'priority': priority,
            'timestamp': datetime.now().isoformat(),
            'status': 'Completed'
        }
        self.tasks.append(task_data)
        self._save_tasks()
    
    def get_recent_tasks(self, limit: int = 5) -> List[Dict]:
        """Get most recent tasks"""
        return sorted(self.tasks, key=lambda x: x['timestamp'], reverse=True)[:limit]
    
    def get_all_tasks(self) -> List[Dict]:
        """Get all stored tasks"""
        return self.tasks
    
    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """Get specific task by ID"""
        for task in self.tasks:
            if task['id'] == task_id:
                return task
        return None
    
    def is_recent(self, timestamp: str, days: int = 7) -> bool:
        """Check if timestamp is within specified days"""
        try:
            task_date = datetime.fromisoformat(timestamp)
            return datetime.now() - task_date <= timedelta(days=days)
        except:
            return False
    
    def clear_memory(self):
        """Clear all stored tasks"""
        self.tasks = []
        self._save_tasks()
    
    def get_memory_stats(self) -> Dict:
        """Get memory statistics"""
        total_tasks = len(self.tasks)
        recent_tasks = len([t for t in self.tasks if self.is_recent(t['timestamp'], 7)])
        
        complexity_counts = {}
        priority_counts = {}
        
        for task in self.tasks:
            complexity = task.get('complexity', 'Unknown')
            priority = task.get('priority', 'Unknown')
            
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        return {
            'total_tasks': total_tasks,
            'recent_tasks': recent_tasks,
            'complexity_distribution': complexity_counts,
            'priority_distribution': priority_counts
        }
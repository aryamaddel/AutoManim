import asyncio
from typing import Dict, Any, Callable, Awaitable, Optional
import uuid

class TaskQueue:
    def __init__(self):
        self.tasks = {}
        self.results = {}
        self.status = {}
        
    async def enqueue(self, task_func: Callable[..., Awaitable[Any]], *args, **kwargs) -> str:
        """Add a task to the queue and return task_id"""
        task_id = str(uuid.uuid4())
        self.status[task_id] = "queued"
        
        # Create and store the task
        task = asyncio.create_task(self._execute_task(task_id, task_func, *args, **kwargs))
        self.tasks[task_id] = task
        
        return task_id
    
    async def _execute_task(self, task_id: str, task_func: Callable[..., Awaitable[Any]], *args, **kwargs) -> None:
        """Execute the task and store the result"""
        try:
            self.status[task_id] = "running"
            result = await task_func(*args, **kwargs)
            self.results[task_id] = result
            self.status[task_id] = "completed"
        except Exception as e:
            self.results[task_id] = {"error": str(e)}
            self.status[task_id] = "failed"
            
    def get_status(self, task_id: str) -> Optional[str]:
        """Get the status of a task"""
        return self.status.get(task_id)
        
    def get_result(self, task_id: str) -> Optional[Any]:
        """Get the result of a completed task"""
        return self.results.get(task_id)

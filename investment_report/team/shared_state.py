"""
Agent Team 共享狀態
模擬 Claude Code Agent Teams 的核心機制：
  - Shared task list：任務佇列，teammates 自行認領
  - Mailbox：代理之間的直接訊息傳遞
  - Results：任務完成後的結果存放
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class Task:
    name: str
    data: Any = None
    status: str = "pending"       # pending | in_progress | completed | failed
    assigned_to: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class AgentSharedState:
    """
    Agent Team 共享狀態管理器

    模擬 Claude Code Agent Teams 的協作機制：
    - Team Lead 建立任務清單，Teammates 認領並完成
    - Teammates 之間可透過 Mailbox 直接溝通
    - 任何代理可隨時查詢任務進度
    """

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._results: Dict[str, Any] = {}
        self._mailbox: Dict[str, List[dict]] = {}
        self._lock = asyncio.Lock()
        self._result_events: Dict[str, asyncio.Event] = {}

    # ── Task List 管理 ─────────────────────────────────────

    async def add_task(self, name: str, data: Any = None) -> None:
        """Team Lead 新增任務到共享清單"""
        async with self._lock:
            self._tasks[name] = Task(name=name, data=data)
            self._result_events[name] = asyncio.Event()

    async def claim_task(self, agent_name: str, task_name: str) -> Optional[Task]:
        """Teammate 認領任務（pending → in_progress）"""
        async with self._lock:
            task = self._tasks.get(task_name)
            if task and task.status == "pending":
                task.status = "in_progress"
                task.assigned_to = agent_name
                return task
        return None

    async def complete_task(self, task_name: str, result: Any) -> None:
        """Teammate 完成任務，儲存結果並通知等待者"""
        async with self._lock:
            if task_name in self._tasks:
                self._tasks[task_name].status = "completed"
                self._tasks[task_name].completed_at = datetime.now()
            self._results[task_name] = result
        if task_name in self._result_events:
            self._result_events[task_name].set()

    async def fail_task(self, task_name: str, error: str) -> None:
        """標記任務失敗，同樣通知等待者避免永久阻塞"""
        async with self._lock:
            if task_name in self._tasks:
                self._tasks[task_name].status = "failed"
            self._results[task_name] = {"error": error}
        if task_name in self._result_events:
            self._result_events[task_name].set()

    async def wait_for(self, task_name: str, timeout: float = 600.0) -> Any:
        """等待特定任務完成（阻塞直到結果可用）"""
        event = self._result_events.get(task_name)
        if event:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        return self._results.get(task_name)

    async def get_result(self, task_name: str) -> Optional[Any]:
        """取得已完成任務的結果（非阻塞）"""
        return self._results.get(task_name)

    # ── Mailbox 通訊機制 ───────────────────────────────────

    async def send_message(self, from_agent: str, to_agent: str, message: str) -> None:
        """Teammate 發送直接訊息給另一位 Teammate"""
        async with self._lock:
            if to_agent not in self._mailbox:
                self._mailbox[to_agent] = []
            self._mailbox[to_agent].append({
                "from": from_agent,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            })

    async def check_messages(self, agent_name: str) -> List[dict]:
        """Teammate 查看並清空自己的收件匣"""
        async with self._lock:
            return self._mailbox.pop(agent_name, [])

    # ── 狀態查詢 ──────────────────────────────────────────

    def get_team_status(self) -> Dict[str, dict]:
        """Team Lead 查看所有任務的當前狀態"""
        return {
            name: {
                "status": task.status,
                "assigned_to": task.assigned_to,
                "elapsed_s": round(
                    ((task.completed_at or datetime.now()) - task.created_at).total_seconds(), 1
                ) if task.assigned_to else None,
            }
            for name, task in self._tasks.items()
        }

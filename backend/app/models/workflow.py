"""
工作流数据模型
"""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class NodeStatus:
    """节点状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"


class NodeResult(BaseModel):
    """节点执行结果"""
    node_id: str
    agent: str = ""
    status: str = "pending"
    summary: str = ""
    output_files: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class Checkpoint(BaseModel):
    """节点检查点"""
    node_id: str
    completed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: str = "success"
    output: dict[str, Any] = Field(default_factory=dict)
    can_resume_from: bool = True


class PendingApproval(BaseModel):
    """待审批状态记录"""
    node_id: str                                    # 当前等待审批的节点 ID
    artifact_path: str = ""                         # 审批产物文件路径
    waiting_since: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )                                               # 开始等待的时间
    prev_agent_node: str = ""                       # 上一个 agent 节点（驳回时回退目标）
    description: str = ""                           # 审批描述信息


class WorkflowState(BaseModel):
    """工作流执行状态"""
    workflow_id: str
    workflow_type: str  # novel-setup / chapter-production / revision / character-import
    book_id: str
    status: str = "pending"  # pending / running / completed / failed / waiting_approval
    current_node: str = ""
    nodes: dict[str, NodeResult] = Field(default_factory=dict)
    checkpoints: list[Checkpoint] = Field(default_factory=list)
    loop_count: int = 0  # 审核循环次数
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None
    pending_approval: Optional[PendingApproval] = None  # 待审批信息

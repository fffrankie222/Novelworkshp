"""
审批 API — 工作流审批接口
提供获取待审批信息、提交审批结果、查询完整状态等端点
"""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


class ApprovalSubmission(BaseModel):
    """审批提交请求体"""
    approved: bool                        # True=通过, False=驳回
    feedback: str = ""                    # 用户反馈意见
    modifications: dict[str, str] = {}    # 用户直接修改的产物 {"relative/path": "新内容"}


@router.get("/workflows/{workflow_id}/approval")
async def get_approval_info(workflow_id: str):
    """
    获取当前待审批的信息。

    返回：
    - 产物内容（文件文本）
    - 节点信息（哪个节点在等审批、等待时间）
    - 工作流类型、书籍 ID 等上下文
    """
    # 需要从所有可能的工作区中查找工作流
    state_info = _find_workflow_approval(workflow_id)
    if not state_info:
        raise HTTPException(
            status_code=404,
            detail=f"工作流 {workflow_id} 无待审批信息或不存在",
        )
    return state_info


@router.post("/workflows/{workflow_id}/approval")
async def submit_approval(
    workflow_id: str,
    submission: ApprovalSubmission,
    background_tasks: BackgroundTasks,
):
    """
    提交审批结果。

    Body:
    - approved: true/false
    - feedback: 用户反馈
    - modifications: 用户直接修改的产物内容（可选）

    行为：
    - approved=True：将 modifications 应用到文件（如有），然后继续执行下一个节点
    - approved=False：将 modifications 应用到文件（如有），回退到上一个 agent 节点重新执行
    """
    engine, state = _find_workflow_engine(workflow_id)
    if not engine or not state:
        raise HTTPException(
            status_code=404,
            detail=f"工作流 {workflow_id} 不存在",
        )

    if state.status != "waiting_approval":
        raise HTTPException(
            status_code=400,
            detail=f"工作流 {workflow_id} 当前状态为 {state.status}，不在等待审批",
        )

    # 在后台任务中执行恢复流程
    async def _resume():
        result = await engine.resume_workflow(
            workflow_id=workflow_id,
            approved=submission.approved,
            feedback=submission.feedback,
            modifications=submission.modifications if submission.modifications else None,
        )
        return result

    background_tasks.add_task(lambda: asyncio.run(_resume()))

    action = "通过" if submission.approved else "驳回"
    return {
        "message": f"审批已{action}，工作流正在恢复执行",
        "workflow_id": workflow_id,
        "approved": submission.approved,
        "feedback": submission.feedback,
        "has_modifications": bool(submission.modifications),
    }


@router.get("/workflows/{workflow_id}/status")
async def get_workflow_full_status(workflow_id: str):
    """
    查询工作流完整状态（增强版）。
    返回完整状态信息，包括 waiting_approval 状态和待审批产物摘要。
    """
    engine, state = _find_workflow_engine(workflow_id)
    if not state:
        return {
            "workflow_id": workflow_id,
            "status": "unknown",
            "message": "工作流状态未找到（可能尚未启动或已完成清理）",
        }

    result = {
        "workflow_id": state.workflow_id,
        "workflow_type": state.workflow_type,
        "book_id": state.book_id,
        "status": state.status,
        "current_node": state.current_node,
        "loop_count": state.loop_count,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
        "error": state.error,
        "nodes": {k: v.dict() for k, v in state.nodes.items()},
    }

    # 如果有待审批信息，附加审批详情
    if state.pending_approval:
        result["pending_approval"] = state.pending_approval.dict()
        # 附加产物摘要（仅列出文件名和内容长度，不传全文）
        if engine and state.pending_approval.artifact_path:
            artifact_path = engine.workspace_path / state.pending_approval.artifact_path
            if artifact_path.exists():
                import json
                try:
                    with open(artifact_path, "r", encoding="utf-8") as f:
                        artifact = json.load(f)
                    files_summary = {}
                    for fp, content in artifact.get("files_content", {}).items():
                        files_summary[fp] = {
                            "length": len(content),
                            "preview": content[:200] + "..." if len(content) > 200 else content,
                        }
                    result["artifact_summary"] = {
                        "sources": list(artifact.get("sources", {}).keys()),
                        "files": files_summary,
                        "created_at": artifact.get("created_at", ""),
                    }
                except Exception:
                    pass

    return result


# ============================================================
# 内部辅助函数
# ============================================================

def _scan_all_engines():
    """
    扫描所有书籍工作区，返回所有 WorkflowEngine 实例。
    由于工作流分布在各自的 workspace 下，需要遍历 workspace 目录。
    """
    from app.api.books import _get_workspaces_dir

    engines = []
    workspaces_dir = _get_workspaces_dir()
    if not workspaces_dir.exists():
        return engines

    for book_dir in workspaces_dir.iterdir():
        if book_dir.is_dir() and (book_dir / "runtime").exists():
            try:
                from app.workflows.engine import WorkflowEngine
                engine = WorkflowEngine(str(book_dir))
                engines.append(engine)
            except Exception as e:
                logger.warning(f"扫描工作区 {book_dir} 失败: {e}")

    return engines


def _find_workflow_approval(workflow_id: str) -> Optional[dict]:
    """在所有引擎中查找工作流的审批信息"""
    for engine in _scan_all_engines():
        info = engine.get_approval_info(workflow_id)
        if info:
            return info
    return None


def _find_workflow_engine(workflow_id: str):
    """在所有引擎中查找工作流所在的引擎和状态"""
    for engine in _scan_all_engines():
        state = engine.get_workflow_state(workflow_id)
        if state:
            return engine, state
    return None, None

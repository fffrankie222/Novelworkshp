"""
revision Workflow — 修订润色流程
humanizer → approval
支持修订模式：polish / spot-fix / rewrite / rework / anti-detect
"""
import logging
import time
from pathlib import Path

from app.workflows.engine import WorkflowEngine, WorkflowNode
from app.agents.humanizer_agent import HumanizerAgent

logger = logging.getLogger(__name__)


def build_revision_nodes(
    chapter_number: int = 1,
    revision_mode: str = "polish",
    instructions: str = "",
) -> list[WorkflowNode]:
    """
    构建修订润色工作流的节点列表。
    独立为函数，供 resume_workflow 重建节点结构时使用。

    Returns:
        节点列表（humanizer + approval）
    """
    humanizer = HumanizerAgent()

    return [
        WorkflowNode(
            node_id="humanize",
            node_type="agent",
            handler=humanizer,
            config={
                "mode": "embedded",
                "revision_mode": revision_mode,
                "instructions": instructions,
            },
        ),
        WorkflowNode(
            node_id="approval",
            node_type="approval",
            config={
                "description": "请审阅修订后的章节内容，确认或提出修改意见",
                "artifact_sources": [
                    {
                        "key": "revision_output",
                        "label": "修订后正文",
                        "files": [
                            f"chapters/chapter-{chapter_number:04d}.md",
                            f"chapters/chapter-{chapter_number:04d}/revised.md",
                        ],
                    },
                ],
            },
        ),
    ]


async def run_revision(
    workspace_path: str,
    book_id: str,
    chapter_number: int,
    revision_mode: str = "polish",
    instructions: str = "",
) -> dict:
    """
    执行修订润色工作流。

    Args:
        workspace_path: 书籍工作区路径
        book_id: 书籍 ID
        chapter_number: 章节号
        revision_mode: 修订模式（polish/spot-fix/rewrite/rework/anti-detect）
        instructions: 用户指定的修订方向
    Returns:
        执行结果（status 可能为 waiting_approval 表示暂停等待审批）
    """
    engine = WorkflowEngine(workspace_path)

    ch_id = f"chapter-{chapter_number:04d}"
    workflow_id = f"revision-{book_id}-{ch_id}-{int(time.time())}"

    nodes = build_revision_nodes(
        chapter_number=chapter_number,
        revision_mode=revision_mode,
        instructions=instructions,
    )

    state = await engine.execute_workflow(
        workflow_id=workflow_id,
        workflow_type="revision",
        book_id=book_id,
        nodes=nodes,
        initial_context={
            "book_id": book_id,
            "chapter_number": chapter_number,
            "workspace_path": workspace_path,
            "revision_mode": revision_mode,
            "instructions": instructions,
        },
    )

    result = {
        "workflow_id": workflow_id,
        "status": state.status,
        "nodes": {k: v.dict() for k, v in state.nodes.items()},
    }

    if state.status == "waiting_approval" and state.pending_approval:
        result["pending_approval"] = state.pending_approval.dict()

    return result

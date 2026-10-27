"""
chapter-production Workflow — 章节生产流水线（核心 12 节点）
plan → compose → write → observe → reflect → apply_state → normalize → audit → [revise → audit]* → approval → done
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional

from app.workflows.engine import WorkflowEngine, WorkflowNode
from app.agents.plot_architect import PlotArchitectAgent
from app.agents.chapter_writer import ChapterWriterAgent
from app.agents.consistency_checker import ConsistencyCheckerAgent
from app.agents.humanizer_agent import HumanizerAgent

logger = logging.getLogger(__name__)


async def _compose_context_script(context: dict, config: dict) -> dict:
    """上下文组装脚本节点"""
    from app.tools.compose_context import compose_context

    chapter_number = context.get("chapter_number", 1)
    workspace_path = context.get("workspace_path", "")
    involved_characters = context.get("involved_characters", [])
    relevant_hooks = context.get("relevant_hooks", [])

    result = await compose_context(
        chapter_number=chapter_number,
        workspace_path=workspace_path,
        target_model="deepseek-chat",
        involved_characters=involved_characters,
        relevant_hooks=relevant_hooks,
    )

    return {
        "summary": f"上下文组装完成，总 token: {result.get('total_tokens', 0)}",
        "context_text": result.get("context_text", ""),
        "token_usage": result.get("token_usage", {}),
    }


async def _apply_state_script(context: dict, config: dict) -> dict:
    """状态更新脚本节点"""
    from app.tools.apply_state import apply_state_update

    workspace_path = context.get("workspace_path", "")
    chapter_number = context.get("chapter_number", 1)
    parsed_data = context.get("parsed_data", {})

    result = apply_state_update(
        workspace_path=workspace_path,
        chapter_number=chapter_number,
        delta=parsed_data,
    )

    return {
        "summary": result.get("summary", "状态更新完成"),
    }


async def _finalize_chapter_script(context: dict, config: dict) -> dict:
    """章节定稿脚本节点"""
    from app.tools.finalize_chapter import finalize_chapter

    workspace_path = context.get("workspace_path", "")
    chapter_number = context.get("chapter_number", 1)
    content = context.get("content", "")

    result = finalize_chapter(
        workspace_path=workspace_path,
        chapter_number=chapter_number,
        content=content,
    )

    return {
        "summary": result.get("summary", "章节定稿完成"),
        "final_path": result.get("final_path", ""),
    }


def _audit_condition(context: dict, loop_count: int, max_loop: int) -> bool:
    """审核条件判断：是否有关键问题且未超过循环次数"""
    parsed_data = context.get("parsed_data", {})
    critical_count = parsed_data.get("critical_count", 0)

    should_loop = critical_count > 0 and loop_count < max_loop
    if should_loop:
        logger.info(f"审核发现 {critical_count} 个关键问题，触发修订循环 (第{loop_count + 1}次)")
    else:
        if critical_count > 0:
            logger.warning(f"审核仍有 {critical_count} 个关键问题，但已达最大循环次数 {max_loop}")

    return should_loop


def build_chapter_production_nodes(
    book_id: str = "",
    chapter_number: int = 1,
    target_words: int = 3000,
    involved_characters: list = None,
    relevant_hooks: list = None,
) -> list[WorkflowNode]:
    """
    构建章节生产工作流的节点列表。
    独立为函数，供 resume_workflow 重建节点结构时使用。

    Returns:
        12 节点流水线
    """
    plot_architect = PlotArchitectAgent()
    chapter_writer = ChapterWriterAgent()
    consistency_checker = ConsistencyCheckerAgent()
    humanizer = HumanizerAgent()

    return [
        # 节点 1: Planner — 生成章节意图
        WorkflowNode(
            node_id="plan",
            node_type="agent",
            handler=plot_architect,
            config={
                "sub_task": "chapter_intent",
                "chapter_number": chapter_number,
                "target_words": target_words,
            },
        ),

        # 节点 2: Composer — 上下文组装（脚本）
        WorkflowNode(
            node_id="compose",
            node_type="script",
            handler=_compose_context_script,
        ),

        # 节点 3: Writer — 正文生成
        WorkflowNode(
            node_id="write",
            node_type="agent",
            handler=chapter_writer,
            config={
                "mode": "write",
                "chapter_number": chapter_number,
                "target_words": target_words,
            },
        ),

        # 节点 4: Observer — 事实提取
        WorkflowNode(
            node_id="observe",
            node_type="agent",
            handler=consistency_checker,
            config={
                "mode": "observer",
                "chapter_number": chapter_number,
            },
        ),

        # 节点 5: Reflector — 状态 delta
        WorkflowNode(
            node_id="reflect",
            node_type="agent",
            handler=consistency_checker,
            config={
                "mode": "reflector",
                "chapter_number": chapter_number,
            },
        ),

        # 节点 6: Apply State — 应用状态更新（脚本）
        WorkflowNode(
            node_id="apply_state",
            node_type="script",
            handler=_apply_state_script,
        ),

        # 节点 7: Normalizer — 字数调整
        WorkflowNode(
            node_id="normalize",
            node_type="agent",
            handler=chapter_writer,
            config={
                "mode": "normalize",
                "target_words": target_words,
                "tolerance": 0.1,
            },
        ),

        # 节点 8: Auditor — 20 维审核
        WorkflowNode(
            node_id="audit",
            node_type="agent",
            handler=consistency_checker,
            config={
                "mode": "auditor",
                "chapter_number": chapter_number,
            },
        ),

        # 节点 9: Condition — 是否有关键问题需要修订
        WorkflowNode(
            node_id="check_audit",
            node_type="condition",
            config={
                "condition_fn": _audit_condition,
                "true_target": "revise",  # 循环回到 revise 节点
            },
        ),

        # 节点 10: Reviser — 去 AI 味 + 修复
        WorkflowNode(
            node_id="revise",
            node_type="agent",
            handler=humanizer,
            config={
                "mode": "revise",
            },
        ),

        # 节点 11: Approval — 用户审阅章节（真实审批，暂停等待）
        WorkflowNode(
            node_id="approval",
            node_type="approval",
            config={
                "description": "请审阅生成的章节内容，确认或提出修改意见",
                "artifact_sources": [
                    {
                        "key": "chapter_content",
                        "label": "章节正文",
                        "files": [
                            f"chapters/chapter-{chapter_number:04d}.md",
                            f"chapters/chapter-{chapter_number:04d}/draft.md",
                        ],
                    },
                    {
                        "key": "audit_result",
                        "label": "审核报告",
                        "files": [
                            f"chapters/chapter-{chapter_number:04d}/audit-report.md",
                        ],
                    },
                ],
            },
        ),

        # 节点 12: Done — 章节定稿
        WorkflowNode(
            node_id="done",
            node_type="script",
            handler=_finalize_chapter_script,
        ),
    ]


async def run_chapter_production(
    workspace_path: str,
    book_id: str,
    chapter_number: int,
    target_words: int = 3000,
    involved_characters: list[str] = None,
    relevant_hooks: list[str] = None,
) -> dict:
    """
    执行章节生产工作流。

    Args:
        workspace_path: 书籍工作区路径
        book_id: 书籍 ID
        chapter_number: 章节号
        target_words: 目标字数
        involved_characters: 本章涉及的角色
        relevant_hooks: 本章相关的伏笔
    Returns:
        执行结果（status 可能为 waiting_approval 表示暂停等待审批）
    """
    ws = Path(workspace_path)
    engine = WorkflowEngine(workspace_path)

    ch_id = f"chapter-{chapter_number:04d}"
    workflow_id = f"chapter-prod-{book_id}-{ch_id}-{int(time.time())}"

    nodes = build_chapter_production_nodes(
        book_id=book_id,
        chapter_number=chapter_number,
        target_words=target_words,
        involved_characters=involved_characters,
        relevant_hooks=relevant_hooks,
    )

    # 执行
    state = await engine.execute_workflow(
        workflow_id=workflow_id,
        workflow_type="chapter-production",
        book_id=book_id,
        nodes=nodes,
        initial_context={
            "book_id": book_id,
            "chapter_number": chapter_number,
            "target_words": target_words,
            "workspace_path": workspace_path,
            "involved_characters": involved_characters or [],
            "relevant_hooks": relevant_hooks or [],
        },
        max_loop_count=3,
    )

    result = {
        "workflow_id": workflow_id,
        "status": state.status,
        "loop_count": state.loop_count,
        "nodes": {k: v.dict() for k, v in state.nodes.items()},
    }

    if state.status == "waiting_approval" and state.pending_approval:
        result["pending_approval"] = state.pending_approval.dict()

    return result

"""
character-import Workflow — 角色蒸馏导入流程
从已有小说中提取角色：distill → materialize → export_graph
支持长篇分批蒸馏策略
"""
import json
import logging
import time
from pathlib import Path

from app.workflows.engine import WorkflowEngine, WorkflowNode
from app.agents.char_designer import CharDesignerAgent

logger = logging.getLogger(__name__)


async def _split_text_script(context: dict, config: dict) -> dict:
    """文本预处理脚本：按章节边界分割文本"""
    source_text = context.get("source_text", "")
    batch_size = config.get("batch_size_chars", 25000)
    overlap = config.get("overlap_chars", 3000)

    if len(source_text) <= batch_size:
        batches = [source_text]
    else:
        batches = []
        start = 0
        while start < len(source_text):
            end = min(start + batch_size, len(source_text))
            # 尝试在章节边界切割
            if end < len(source_text):
                # 向前查找章节标记
                for marker in ["\n第", "\nChapter", "\nCHAPTER"]:
                    pos = source_text.rfind(marker, start, end)
                    if pos > start + batch_size // 2:
                        end = pos
                        break
            batches.append(source_text[start:end])
            start = end - overlap if end < len(source_text) else end

    return {
        "summary": f"文本分割完成：{len(batches)} 个批次",
        "batches": batches,
        "total_batches": len(batches),
    }


async def _merge_batches_script(context: dict, config: dict) -> dict:
    """合并多批次蒸馏结果"""
    batch_results = context.get("batch_results", [])

    # 简单合并：后续批次覆盖前面批次的同名字段
    merged = {}
    for batch in batch_results:
        if isinstance(batch, dict):
            for char_name, char_data in batch.items():
                if char_name in merged:
                    # 合并：新批次覆盖旧批次
                    merged[char_name].update(char_data)
                else:
                    merged[char_name] = char_data

    return {
        "summary": f"合并完成：{len(merged)} 个角色",
        "merged_characters": merged,
    }


def build_character_import_nodes(batch_size: int = 25000) -> list[WorkflowNode]:
    """
    构建角色蒸馏导入工作流的节点列表。
    独立为函数，供 resume_workflow 重建节点结构时使用。

    Returns:
        节点列表
    """
    char_designer = CharDesignerAgent()

    return [
        # 节点 1: 文本分割
        WorkflowNode(
            node_id="split_text",
            node_type="script",
            handler=_split_text_script,
            config={"batch_size_chars": batch_size, "overlap_chars": 3000},
        ),
        # 节点 2: 角色蒸馏
        WorkflowNode(
            node_id="distill",
            node_type="agent",
            handler=char_designer,
            config={"sub_task": "distill"},
        ),
        # 节点 3: 合并结果
        WorkflowNode(
            node_id="merge",
            node_type="script",
            handler=_merge_batches_script,
        ),
        # 节点 4: 导出关系图
        WorkflowNode(
            node_id="export_graph",
            node_type="agent",
            handler=char_designer,
            config={"sub_task": "export_relations"},
        ),
    ]


async def run_character_import(
    workspace_path: str,
    book_id: str,
    source_text: str,
    batch_size: int = 25000,
) -> dict:
    """
    执行角色蒸馏导入工作流。

    Args:
        workspace_path: 书籍工作区路径
        book_id: 书籍 ID
        source_text: 源文本（已有小说内容）
        batch_size: 每批处理字符数
    Returns:
        执行结果
    """
    engine = WorkflowEngine(workspace_path)

    workflow_id = f"char-import-{book_id}-{int(time.time())}"

    nodes = build_character_import_nodes(batch_size=batch_size)

    state = await engine.execute_workflow(
        workflow_id=workflow_id,
        workflow_type="character-import",
        book_id=book_id,
        nodes=nodes,
        initial_context={
            "book_id": book_id,
            "workspace_path": workspace_path,
            "source_text": source_text,
        },
    )

    return {
        "workflow_id": workflow_id,
        "status": state.status,
        "nodes": {k: v.dict() for k, v in state.nodes.items()},
    }

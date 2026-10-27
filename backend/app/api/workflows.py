"""
工作流 API — 触发工作流、查询执行进度
支持状态持久化：内存 dict 作为缓存，磁盘作为持久层
"""
import asyncio
import json
import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.api.books import _get_book_dir

logger = logging.getLogger(__name__)

router = APIRouter()

# 内存中的工作流状态（作为缓存，磁盘为持久层）
_workflow_results: dict[str, dict] = {}


class ChapterProductionRequest(BaseModel):
    """章节生产请求"""
    chapter_number: int
    target_words: int = 3000
    involved_characters: list[str] = []
    relevant_hooks: list[str] = []


class RevisionRequest(BaseModel):
    """修订请求"""
    chapter_number: int
    revision_mode: str = "polish"
    instructions: str = ""


class NovelSetupRequest(BaseModel):
    """新书建立请求"""
    genre: str = "xuanhuan"
    description: str = ""
    character_ideas: list[dict] = []


@router.post("/books/{book_id}/workflow/novel-setup")
async def start_novel_setup(book_id: str, request: NovelSetupRequest, background_tasks: BackgroundTasks):
    """启动新书建立流程"""
    import time as _time
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    workflow_id = f"novel-setup-{book_id}-{int(_time.time())}"

    async def _run():
        from app.workflows.novel_setup import run_novel_setup
        result = await run_novel_setup(
            workspace_path=str(book_dir),
            book_id=book_id,
            genre=request.genre,
            description=request.description,
            character_ideas=request.character_ideas,
        )
        # 同步更新内存缓存
        _workflow_results[result["workflow_id"]] = result

    background_tasks.add_task(lambda: asyncio.run(_run()))

    return {
        "workflow_id": workflow_id,
        "status": "started",
        "book_id": book_id,
        "workflow_type": "novel-setup",
    }


@router.post("/books/{book_id}/workflow/chapter-production")
async def start_chapter_production(
    book_id: str,
    request: ChapterProductionRequest,
    background_tasks: BackgroundTasks,
):
    """启动章节生产流程"""
    import time as _time
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    ch_id = f"chapter-{request.chapter_number:04d}"
    workflow_id = f"chapter-prod-{book_id}-{ch_id}-{int(_time.time())}"

    async def _run():
        from app.workflows.chapter_production import run_chapter_production
        result = await run_chapter_production(
            workspace_path=str(book_dir),
            book_id=book_id,
            chapter_number=request.chapter_number,
            target_words=request.target_words,
            involved_characters=request.involved_characters,
            relevant_hooks=request.relevant_hooks,
        )
        _workflow_results[result["workflow_id"]] = result

    background_tasks.add_task(lambda: asyncio.run(_run()))

    return {
        "workflow_id": workflow_id,
        "status": "started",
        "book_id": book_id,
        "workflow_type": "chapter-production",
    }


@router.post("/books/{book_id}/workflow/revision")
async def start_revision(book_id: str, request: RevisionRequest, background_tasks: BackgroundTasks):
    """启动修订润色流程"""
    import time as _time
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    ch_id = f"chapter-{request.chapter_number:04d}"
    workflow_id = f"revision-{book_id}-{ch_id}-{int(_time.time())}"

    async def _run():
        from app.workflows.revision import run_revision
        result = await run_revision(
            workspace_path=str(book_dir),
            book_id=book_id,
            chapter_number=request.chapter_number,
            revision_mode=request.revision_mode,
            instructions=request.instructions,
        )
        _workflow_results[result["workflow_id"]] = result

    background_tasks.add_task(lambda: asyncio.run(_run()))

    return {
        "workflow_id": workflow_id,
        "status": "started",
        "book_id": book_id,
        "workflow_type": "revision",
    }


# 注：GET /api/workflows/{workflow_id}/status 的唯一实现位于 approvals.py
# （增强版，含 pending_approval / artifact_summary）。
# 旧版本端点曾定义为 /{workflow_id}/status（注册后遮蔽 approvals 版），已删除（R3 修复），
# 避免两套状态查询语义分叉。approvals 路由在 router.py 中紧随本路由注册。


@router.get("/workflows/list")
async def list_all_workflows():
    """
    列出所有工作流（从磁盘扫描所有工作区）。
    返回每个工作流的摘要信息。
    """
    all_workflows = []
    for engine in _get_all_engines():
        for state in engine.list_workflows():
            all_workflows.append({
                "workflow_id": state.workflow_id,
                "workflow_type": state.workflow_type,
                "book_id": state.book_id,
                "status": state.status,
                "current_node": state.current_node,
                "created_at": state.created_at,
                "updated_at": state.updated_at,
                "has_pending_approval": state.pending_approval is not None,
            })

    # 按更新时间倒序排列
    all_workflows.sort(key=lambda w: w.get("updated_at", ""), reverse=True)
    return {"workflows": all_workflows, "total": len(all_workflows)}


def _get_all_engines():
    """获取所有工作区的 WorkflowEngine 实例"""
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
                logger.warning(f"加载工作区引擎 {book_dir} 失败: {e}")

    return engines

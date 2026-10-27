"""
伏笔 API — 伏笔的创建、读取与更新
v4.0: 统一从 outline.json.foreshadowing 读写，废弃旧的 hooks.json / hook_ledger.json
保留原有 API 端点以兼容前端。
"""
import logging
import time

from fastapi import APIRouter, HTTPException

from app.api.books import _get_book_dir
from app.tools.file_ops import read_json, write_json

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_outline_path(book_dir):
    return str(book_dir / "outline" / "outline.json")


def _load_foreshadowing(book_dir) -> list[dict]:
    """从 outline.json 读取伏笔列表"""
    data = read_json(_get_outline_path(book_dir)) or {}
    return data.get("foreshadowing", [])


def _save_foreshadowing(book_dir, foreshadowing: list[dict]):
    """将伏笔列表写回 outline.json.foreshadowing"""
    outline_path = _get_outline_path(book_dir)
    existing = read_json(outline_path) or {}
    existing["foreshadowing"] = foreshadowing
    write_json(outline_path, existing)


@router.get("/{book_id}/hooks")
async def get_hooks(book_id: str):
    """获取伏笔列表（数据源: outline.json.foreshadowing）"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    hooks = _load_foreshadowing(book_dir)
    return {"hooks": hooks, "total": len(hooks)}


@router.post("/{book_id}/hooks")
async def create_hook(book_id: str, data: dict):
    """创建伏笔（写入 outline.json.foreshadowing）"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    hooks = _load_foreshadowing(book_dir)

    # 生成伏笔 ID
    hook_id = f"fs-{int(time.time())}"
    new_hook = {
        "id": hook_id,
        "purpose": data.get("description", data.get("purpose", "")),
        "description": data.get("description", data.get("notes", "")),
        "start_chapter": data.get("start_chapter", data.get("planted_chapter", 0)),
        "end_chapter": data.get("end_chapter", data.get("target_chapter", 0)),
        "characters": data.get("characters", []),
        "status": data.get("status", "planted"),
    }
    hooks.append(new_hook)
    _save_foreshadowing(book_dir, hooks)

    return {"message": "伏笔已创建", "hook": new_hook}


@router.put("/{book_id}/hooks/{hook_id}")
async def update_hook(book_id: str, hook_id: str, data: dict):
    """更新伏笔（写入 outline.json.foreshadowing）"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    hooks = _load_foreshadowing(book_dir)

    for i, hook in enumerate(hooks):
        if hook.get("id") == hook_id:
            hooks[i].update(data)
            hooks[i]["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            _save_foreshadowing(book_dir, hooks)
            return {"message": "伏笔已更新", "hook": hooks[i]}

    raise HTTPException(status_code=404, detail=f"伏笔 {hook_id} 不存在")

"""
世界观 API — 世界观数据的读取与更新
返回格式与前端 WorldBuilding 类型完全对齐
"""
import logging

from fastapi import APIRouter, HTTPException

from app.api.books import _get_book_dir
from app.tools.file_ops import read_json, write_json

logger = logging.getLogger(__name__)

router = APIRouter()

DEFAULT_WORLD = {
    "id": "",
    "book_id": "",
    "geography": "",
    "factions": "",
    "power_system": "",
    "history": "",
    "social_rules": "",
    "factions_graph": [],
    "timeline_events": [],
}


def _ensure_world_fields(data: dict, book_id: str = "") -> dict:
    """确保返回的世界观数据包含前端需要的所有字段"""
    result = DEFAULT_WORLD.copy()
    result.update({k: v for k, v in data.items() if k in result})
    if not result["id"]:
        result["id"] = f"world-{book_id}"
    if not result["book_id"]:
        result["book_id"] = book_id
    # factions 可能是 list（旧数据），转为字符串
    if isinstance(result.get("factions"), list):
        result["factions"] = "\n".join(
            f"- {f.get('name', f) if isinstance(f, dict) else f}"
            for f in result["factions"]
        )
    return result


@router.get("/{book_id}/world")
async def get_world(book_id: str):
    """获取世界观数据"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    data = read_json(str(book_dir / "world" / "world_data.json"))
    if not data:
        data = DEFAULT_WORLD.copy()
    return _ensure_world_fields(data, book_id)


@router.put("/{book_id}/world")
async def update_world(book_id: str, data: dict):
    """更新世界观数据 — 直接返回 WorldBuilding 对象"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    file_path = str(book_dir / "world" / "world_data.json")
    existing = read_json(file_path)
    existing.update(data)
    write_json(file_path, existing)

    # 直接返回世界观数据对象（前端期望 WorldBuilding 类型）
    return _ensure_world_fields(existing, book_id)

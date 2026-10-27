"""
时间线 API — 时间线事件的读取与添加
"""
import logging
import time

from fastapi import APIRouter, HTTPException

from app.api.books import _get_book_dir
from app.tools.file_ops import read_json, write_json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{book_id}/timeline")
async def get_timeline(book_id: str):
    """获取时间线事件"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    data = read_json(str(book_dir / "timeline" / "timeline.json"))
    events = data.get("events", [])
    return {"events": events, "total": len(events)}


@router.post("/{book_id}/timeline")
async def add_timeline_event(book_id: str, data: dict):
    """添加时间线事件"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    file_path = str(book_dir / "timeline" / "timeline.json")
    existing = read_json(file_path)
    if "events" not in existing:
        existing["events"] = []

    # 生成事件 ID
    event_id = f"evt-{int(time.time())}"
    new_event = {
        "id": event_id,
        "time": data.get("time", ""),
        "event": data.get("event", ""),
        "location": data.get("location", ""),
        "characters": data.get("characters", []),
        "chapter": data.get("chapter", ""),
        "description": data.get("description", ""),
        "significance": data.get("significance", ""),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    existing["events"].append(new_event)
    write_json(file_path, existing)

    return {"message": "时间线事件已添加", "event": new_event}

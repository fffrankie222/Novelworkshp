"""
角色 API — 角色的 CRUD 操作
"""
import logging
import time

from fastapi import APIRouter, HTTPException

from app.api.books import _get_book_dir
from app.tools.file_ops import read_json, write_json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{book_id}/characters")
async def get_characters(book_id: str):
    """获取角色列表"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    data = read_json(str(book_dir / "characters" / "characters.json"))
    characters = data.get("characters", [])
    return {"characters": characters, "total": len(characters)}


@router.post("/{book_id}/characters")
async def create_character(book_id: str, data: dict):
    """创建新角色"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    file_path = str(book_dir / "characters" / "characters.json")
    existing = read_json(file_path)
    if "characters" not in existing:
        existing["characters"] = []

    # 生成角色 ID
    char_id = f"char-{int(time.time())}"
    new_char = {
        "id": char_id,
        "book_id": book_id,
        "name": data.get("name", ""),
        "role": data.get("role", "待定"),
        "tag": data.get("tag", ""),
        "avatar_color": data.get("avatar_color", "#666666"),
        "portrait": data.get("portrait", data.get("description", "")),
        "personality": data.get("personality", ""),
        "background": data.get("background", ""),
        "motivation": data.get("motivation", ""),
        "abilities": data.get("abilities", ""),
        "catchphrase": data.get("catchphrase", ""),
        "growth_arc": data.get("growth_arc", []),
        "relationships": data.get("relationships", []),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    existing["characters"].append(new_char)
    write_json(file_path, existing)

    # 直接返回 Character 对象（前端期望 Character 类型）
    return new_char


@router.get("/{book_id}/characters/{char_id}")
async def get_character(book_id: str, char_id: str):
    """获取单个角色"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    data = read_json(str(book_dir / "characters" / "characters.json"))
    for char in data.get("characters", []):
        if char.get("id") == char_id:
            return char

    raise HTTPException(status_code=404, detail=f"角色 {char_id} 不存在")


@router.put("/{book_id}/characters/{char_id}")
async def update_character(book_id: str, char_id: str, data: dict):
    """更新角色"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    file_path = str(book_dir / "characters" / "characters.json")
    existing = read_json(file_path)

    for i, char in enumerate(existing.get("characters", [])):
        if char.get("id") == char_id:
            existing["characters"][i].update(data)
            existing["characters"][i]["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            write_json(file_path, existing)
            # 直接返回 Character 对象（前端期望 Character 类型）
            return existing["characters"][i]

    raise HTTPException(status_code=404, detail=f"角色 {char_id} 不存在")


@router.delete("/{book_id}/characters/{char_id}")
async def delete_character(book_id: str, char_id: str):
    """删除角色"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    file_path = str(book_dir / "characters" / "characters.json")
    existing = read_json(file_path)
    chars = existing.get("characters", [])

    new_chars = [c for c in chars if c.get("id") != char_id]
    if len(new_chars) == len(chars):
        raise HTTPException(status_code=404, detail=f"角色 {char_id} 不存在")

    existing["characters"] = new_chars
    write_json(file_path, existing)

    return {"ok": True, "deleted_id": char_id}

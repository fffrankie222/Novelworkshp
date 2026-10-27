"""
大纲 API — 大纲数据的读取、更新、写作上下文查询
"""
import logging

from fastapi import APIRouter, HTTPException

from app.api.books import _get_book_dir
from app.tools.file_ops import read_json, write_json
from app.utils.data_pipeline import generate_chapters_from_outline

logger = logging.getLogger(__name__)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# 内部工具函数
# ─────────────────────────────────────────────────────────────────────────────

def _load_outline_file(book_dir) -> dict:
    """加载 outline.json，兼容新旧格式"""
    data = read_json(str(book_dir / "outline" / "outline.json"))
    return data or {}


def _normalize_volumes(data: dict) -> list[dict]:
    """
    从 outline.json 提取 volumes 数组。
    兼容旧格式（outline 字段里的 OutlineNode[]）→ 转为新格式。
    """
    # 新格式直接有 volumes
    volumes = data.get("volumes", [])
    if volumes and isinstance(volumes, list):
        return volumes

    # 旧格式：outline 字段里是 OutlineNode[]（type=volume 的有 children）
    outline_nodes = data.get("outline", [])
    if outline_nodes and isinstance(outline_nodes, list):
        converted = []
        for i, node in enumerate(outline_nodes):
            if not isinstance(node, dict):
                continue
            # 有 children → 视为卷
            if node.get("type") == "volume" or (node.get("children") and len(node["children"]) > 0):
                children = []
                for j, child in enumerate(node.get("children", [])):
                    if isinstance(child, dict):
                        children.append({
                            "id": child.get("id", f"ch-{i}-{j}"),
                            "number": child.get("chapter_number", j + 1),
                            "title": child.get("title", f"第{j+1}章"),
                            "summary": child.get("summary", ""),
                            "characters": child.get("characters", []),
                        })
                converted.append({
                    "id": node.get("id", f"vol-{i}"),
                    "number": i + 1,
                    "title": node.get("title", f"第{i+1}卷"),
                    "story_arc": node.get("summary", ""),
                    "chapters": children,
                })
            elif node.get("type") == "chapter":
                # 没有卷结构的扁平章节 → 归入"第一卷"
                if not converted:
                    converted.append({
                        "id": "vol-auto",
                        "number": 1,
                        "title": "正文",
                        "story_arc": "",
                        "chapters": [],
                    })
                converted[0]["chapters"].append({
                    "id": node.get("id", f"ch-auto-{i}"),
                    "number": node.get("chapter_number", len(converted[0]["chapters"]) + 1),
                    "title": node.get("title", ""),
                    "summary": node.get("summary", ""),
                    "characters": node.get("characters", []),
                })
        if converted:
            return converted

    # chapters 字段（更旧的格式）
    chapters = data.get("chapters", [])
    if chapters and isinstance(chapters, list):
        ch_list = []
        for j, ch in enumerate(chapters):
            if isinstance(ch, dict):
                ch_list.append({
                    "id": ch.get("id", f"ch-{j}"),
                    "number": ch.get("number", ch.get("chapter_number", j + 1)),
                    "title": ch.get("title", f"第{j+1}章"),
                    "summary": ch.get("summary", ""),
                    "characters": ch.get("characters", []),
                })
        if ch_list:
            return [{
                "id": "vol-auto",
                "number": 1,
                "title": "正文",
                "story_arc": "",
                "chapters": ch_list,
            }]

    return []


def _find_chapter_in_volumes(volumes: list[dict], chapter_number: int):
    """在 volumes 中查找指定章节号，返回 (volume, chapter) 或 (None, None)"""
    for vol in volumes:
        for ch in vol.get("chapters", []):
            if ch.get("number") == chapter_number:
                return vol, ch
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# API 端点
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{book_id}/outline")
async def get_outline(book_id: str):
    """
    获取大纲
    返回: {outline: [...]}
    outline 数组是新格式的 volumes（每个 volume 含 chapters）
    """
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    data = _load_outline_file(book_dir)
    volumes = _normalize_volumes(data)

    # 如果有 volumes 就直接返回 volumes（前端按新格式解析）
    if volumes:
        return {"outline": volumes}

    # ── Fallback：volumes 为空时，从扁平字段构造默认内容 ──
    # 优先使用 chat_derived_summary，其次用 main_plot/core_conflict
    summary = data.get("chat_derived_summary", "")
    if not summary:
        parts = []
        core_conflict = data.get("core_conflict", "")
        main_plot = data.get("main_plot", "")
        pacing_notes = data.get("pacing_notes", "")
        if core_conflict:
            parts.append(f"核心冲突：{core_conflict}")
        if main_plot:
            parts.append(f"主线剧情：{main_plot}")
        if pacing_notes:
            parts.append(f"节奏安排：{pacing_notes}")
        summary = "\n".join(parts)

    if summary:
        return {
            "outline": [{
                "id": "vol-fallback",
                "number": 1,
                "title": "故事大纲",
                "story_arc": summary,
                "chapters": [],
            }],
            "summary": summary,  # 额外返回 summary 字段供前端纯文本显示
        }

    # 完全无数据
    return {"outline": []}


@router.put("/{book_id}/outline")
async def update_outline(book_id: str, data: dict):
    """
    更新大纲
    前端发送: {outline: [...]} — volumes 数组
    也兼容: {volumes: [...], foreshadowing: [...]}
    """
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    file_path = str(book_dir / "outline" / "outline.json")
    existing = read_json(file_path) or {}

    # 前端可能发送 {outline: [volumes...]} 或 {volumes: [...], foreshadowing: [...]}
    outline_data = data.get("outline", data)

    if isinstance(outline_data, list):
        # 列表格式 → 判断是 volumes 还是旧的 OutlineNode[]
        # 如果元素有 story_arc 或 chapters 字段 → 新格式 volumes
        first = outline_data[0] if outline_data else None
        if first and isinstance(first, dict) and ("story_arc" in first or "chapters" in first):
            existing["volumes"] = outline_data
        else:
            existing["outline"] = outline_data
    elif isinstance(outline_data, dict):
        # 字典格式 → 直接合并
        if "volumes" in outline_data:
            existing["volumes"] = outline_data["volumes"]
        if "foreshadowing" in outline_data:
            existing["foreshadowing"] = outline_data["foreshadowing"]
        # 也兼容旧字段
        for k in ("outline", "chapters", "acts"):
            if k in outline_data:
                existing[k] = outline_data[k]

    write_json(file_path, existing)
    generate_chapters_from_outline(book_dir, existing)
    return existing


@router.get("/{book_id}/writing-context/{chapter_number}")
async def get_writing_context_endpoint(book_id: str, chapter_number: int):
    """
    写作上下文 — 写第 N 章时一次拉取所有需要的数据（v4.0 统一使用 WritingContext Service）

    返回 10 项上下文数据 + Token 预算统计，详见 PRD 6.6 节。
    """
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    from app.services.writing_context import WritingContextService
    service = WritingContextService(book_id)
    return service.get_writing_context(chapter_number)

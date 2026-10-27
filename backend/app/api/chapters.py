"""
章节管理 API — 章节列表、查看、编辑、导出
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.books import _get_book_dir
from app.tools.file_ops import read_file, read_json, list_files, write_file

logger = logging.getLogger(__name__)

router = APIRouter()


class ChapterUpdateRequest(BaseModel):
    """章节更新请求"""
    content: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = "draft"  # draft / final


@router.get("/books/{book_id}/chapters")
async def list_chapters(book_id: str):
    """章节列表"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    chapters = []

    # 读取 config.json 获取 target_words_per_chapter
    config_path = book_dir / "config.json"
    target_words = 3000
    if config_path.exists():
        config = read_json(str(config_path))
        if config:
            target_words = config.get("target_words_per_chapter", 3000)

    # 从 chapter_states.json 获取章节状态
    states_path = book_dir / "state" / "chapter_states.json"
    states = read_json(str(states_path)) if states_path.exists() else {"chapters": {}}

    # 扫描 final 目录
    final_dir = book_dir / "chapters" / "final"
    if final_dir.exists():
        for f in sorted(final_dir.glob("chapter-*.md")):
            ch_id = f.stem
            content = f.read_text(encoding="utf-8")
            word_count = len(content.replace("\n", "").replace(" ", ""))
            ch_state = states.get("chapters", {}).get(ch_id, {})
            chapter_number = _extract_chapter_number(ch_id)

            chapters.append({
                "id": ch_id,
                "chapter_id": ch_id,
                "chapter_number": chapter_number,
                "title": _extract_title_from_content(content, chapter_number),
                "volume": f"第{(chapter_number - 1) // 30 + 1}卷",
                "status": ch_state.get("status", "finalized"),
                "word_count": word_count,
                "target_words": target_words,
                "finalized_at": ch_state.get("finalized_at", ""),
                "updated_at": _get_file_mtime(f),
            })

    # 也扫描 draft 目录（尚未定稿的）
    draft_dir = book_dir / "chapters" / "draft"
    if draft_dir.exists():
        finalized_ids = {c["chapter_id"] for c in chapters}
        for f in sorted(draft_dir.glob("chapter-*.md")):
            ch_id = f.stem
            if ch_id not in finalized_ids:
                content = f.read_text(encoding="utf-8")
                word_count = len(content.replace("\n", "").replace(" ", ""))
                chapter_number = _extract_chapter_number(ch_id)

                chapters.append({
                    "id": ch_id,
                    "chapter_id": ch_id,
                    "chapter_number": chapter_number,
                    "title": _extract_title_from_content(content, chapter_number),
                    "volume": f"第{(chapter_number - 1) // 30 + 1}卷",
                    "status": "draft",
                    "word_count": word_count,
                    "target_words": target_words,
                    "updated_at": _get_file_mtime(f),
                })

    # 也从 chapters.json 读取大纲生成的章节条目（含摘要）
    chapters_json_path = book_dir / "chapters" / "chapters.json"
    if chapters_json_path.exists():
        chapters_json_data = read_json(str(chapters_json_path))
        json_chapters = chapters_json_data.get("chapters", [])
        existing_ids = {c["chapter_id"] for c in chapters}
        for jc in json_chapters:
            jc_id = jc.get("chapter_id", "")
            if jc_id and jc_id not in existing_ids:
                # 该章节尚未有文件，但有大纲条目
                summary = jc.get("summary", "")
                if isinstance(summary, dict):
                    summary = summary.get("text", str(summary))
                chapters.append({
                    "id": jc_id,
                    "chapter_id": jc_id,
                    "chapter_number": jc.get("chapter_number", 0),
                    "title": jc.get("title", ""),
                    "volume": jc.get("volume", ""),
                    "status": jc.get("status", "outlined"),
                    "word_count": jc.get("word_count", 0),
                    "target_words": jc.get("target_words", target_words),
                    "summary": summary,
                    "updated_at": jc.get("updated_at", ""),
                })
            elif jc_id in existing_ids:
                # 已有文件条目，补充 summary 字段
                for c in chapters:
                    if c["chapter_id"] == jc_id and "summary" not in c:
                        summary = jc.get("summary", "")
                        if isinstance(summary, dict):
                            summary = summary.get("text", str(summary))
                        c["summary"] = summary

    chapters.sort(key=lambda x: x["chapter_number"])

    return {"chapters": chapters, "total": len(chapters)}


@router.get("/books/{book_id}/chapters/{chapter_id}")
async def get_chapter(book_id: str, chapter_id: str):
    """章节内容"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")
    
    # 优先读取定稿版本
    final_path = book_dir / "chapters" / "final" / f"{chapter_id}.md"
    draft_path = book_dir / "chapters" / "draft" / f"{chapter_id}.md"
    
    if final_path.exists():
        content = final_path.read_text(encoding="utf-8")
        version = "final"
    elif draft_path.exists():
        content = draft_path.read_text(encoding="utf-8")
        version = "draft"
    else:
        raise HTTPException(status_code=404, detail=f"章节 {chapter_id} 不存在")
    
    # 读取摘要（优先从独立摘要文件，其次从 chapters.json）
    summary_path = book_dir / "chapters" / "summaries" / f"{chapter_id}_summary.json"
    summary = read_json(str(summary_path)) if summary_path.exists() else {}
    
    # 如果独立摘要文件不存在，从 chapters.json 补充
    if not summary:
        chapters_json_path = book_dir / "chapters" / "chapters.json"
        if chapters_json_path.exists():
            chapters_json_data = read_json(str(chapters_json_path))
            for jc in chapters_json_data.get("chapters", []):
                if jc.get("chapter_id") == chapter_id and jc.get("summary"):
                    ch_summary = jc["summary"]
                    if isinstance(ch_summary, dict):
                        summary = ch_summary
                    else:
                        summary = {"text": str(ch_summary)}
                    break

    return {
        "chapter_id": chapter_id,
        "version": version,
        "content": content,
        "word_count": len(content.replace("\n", "").replace(" ", "")),
        "summary": summary,
    }


@router.put("/books/{book_id}/chapters/{chapter_id}")
async def update_chapter(book_id: str, chapter_id: str, request: ChapterUpdateRequest):
    """更新章节内容（保存草稿或定稿）"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    if request.content is None:
        raise HTTPException(status_code=400, detail="content 不能为空")

    # 根据 status 决定写入目录
    status = request.status or "draft"
    if status == "final":
        target_dir = book_dir / "chapters" / "final"
    else:
        target_dir = book_dir / "chapters" / "draft"

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{chapter_id}.md"

    # 如果提供了 title，在内容最前面加上标题行
    content = request.content
    if request.title:
        # 如果内容已有标题行，替换；否则添加
        lines = content.split("\n")
        if lines and lines[0].strip().startswith("#"):
            lines[0] = f"# {request.title}"
            content = "\n".join(lines)
        else:
            content = f"# {request.title}\n\n{content}"

    write_file(str(target_path), content)

    # 计算字数
    word_count = len(content.replace("\n", "").replace(" ", ""))

    # 读取 config 获取 target_words
    config_path = book_dir / "config.json"
    target_words = 3000
    if config_path.exists():
        config = read_json(str(config_path))
        if config:
            target_words = config.get("target_words_per_chapter", 3000)

    chapter_number = _extract_chapter_number(chapter_id)

    # v4.0: 同时更新章节元数据 .json 文件
    _update_chapter_metadata(book_dir, chapter_number, {
        "title": request.title or _extract_title_from_content(content, chapter_number),
        "word_count": word_count,
        "status": status,
    })

    logger.info(f"章节 {chapter_id} 已更新: status={status}, word_count={word_count}")

    return {
        "id": chapter_id,
        "chapter_id": chapter_id,
        "chapter_number": chapter_number,
        "title": request.title or _extract_title_from_content(content, chapter_number),
        "volume": f"第{(chapter_number - 1) // 30 + 1}卷",
        "status": status,
        "word_count": word_count,
        "target_words": target_words,
        "updated_at": _get_file_mtime(target_path),
    }


@router.get("/books/{book_id}/chapters/{chapter_id}/export")
async def export_chapter(book_id: str, chapter_id: str, format: str = "markdown"):
    """导出章节"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")
    
    final_path = book_dir / "chapters" / "final" / f"{chapter_id}.md"
    draft_path = book_dir / "chapters" / "draft" / f"{chapter_id}.md"
    
    content = ""
    if final_path.exists():
        content = final_path.read_text(encoding="utf-8")
    elif draft_path.exists():
        content = draft_path.read_text(encoding="utf-8")
    else:
        raise HTTPException(status_code=404, detail=f"章节 {chapter_id} 不存在")
    
    if format == "txt":
        # 简单去除 markdown 标记
        import re
        content = re.sub(r"^#+\s*", "", content, flags=re.MULTILINE)
        return {"content": content, "format": "txt"}
    
    return {"content": content, "format": format}


def _extract_chapter_number(chapter_id: str) -> int:
    """从 chapter-XXXX 提取章节号"""
    try:
        return int(chapter_id.replace("chapter-", ""))
    except (ValueError, AttributeError):
        return 0


def _extract_title_from_content(content: str, chapter_number: int) -> str:
    """从章节内容中提取标题（第一行 # 开头的文本）"""
    for line in content.split("\n")[:5]:
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return f"第{chapter_number}章"


def _get_file_mtime(file_path: Path) -> str:
    """获取文件修改时间，返回 ISO 格式字符串"""
    try:
        mtime = os.path.getmtime(str(file_path))
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(mtime))
    except OSError:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# v4.0: 章节元数据管理
# ─────────────────────────────────────────────────────────────────────────────

def _get_chapter_metadata_path(book_dir: Path, chapter_number: int) -> Path:
    """获取章节元数据 JSON 文件路径: chapters/chapter-NNNN.json"""
    chapters_dir = book_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    return chapters_dir / f"chapter-{chapter_number:04d}.json"


def _load_chapter_metadata(book_dir: Path, chapter_number: int) -> dict:
    """加载章节元数据，不存在则返回空 dict"""
    meta_path = _get_chapter_metadata_path(book_dir, chapter_number)
    if meta_path.exists():
        return read_json(str(meta_path)) or {}
    return {}


def _update_chapter_metadata(book_dir: Path, chapter_number: int, updates: dict) -> dict:
    """
    更新章节元数据（合并更新）。
    首次创建时自动生成 number、created_at 等字段。
    """
    meta_path = _get_chapter_metadata_path(book_dir, chapter_number)
    existing = {}
    if meta_path.exists():
        existing = read_json(str(meta_path)) or {}

    now_str = time.strftime("%Y-%m-%dT%H:%M:%S")

    # 首次创建时设置默认字段
    if "number" not in existing:
        existing["number"] = chapter_number
    if "created_at" not in existing:
        existing["created_at"] = now_str
    existing["updated_at"] = now_str

    # 合并更新字段
    for key, value in updates.items():
        if value is not None:
            existing[key] = value

    # 尝试关联 outline_chapter_id
    if "outline_chapter_id" not in existing:
        outline_chapter_id = _find_outline_chapter_id(book_dir, chapter_number)
        if outline_chapter_id:
            existing["outline_chapter_id"] = outline_chapter_id

    write_json(str(meta_path), existing)
    return existing


def _find_outline_chapter_id(book_dir: Path, chapter_number: int) -> str:
    """从 outline.json 中查找章节号对应的 chapter id"""
    outline_path = book_dir / "outline" / "outline.json"
    if not outline_path.exists():
        return ""
    outline_data = read_json(str(outline_path)) or {}
    volumes = outline_data.get("volumes", [])
    for vol in volumes:
        for ch in vol.get("chapters", []):
            if ch.get("number") == chapter_number:
                return ch.get("id", "")
    # 兼容旧格式
    outline_nodes = outline_data.get("outline", [])
    for node in outline_nodes:
        if isinstance(node, dict):
            for child in node.get("children", []):
                if isinstance(child, dict) and child.get("chapter_number") == chapter_number:
                    return child.get("id", "")
    chapters = outline_data.get("chapters", [])
    for ch in chapters:
        if isinstance(ch, dict) and ch.get("number", ch.get("chapter_number")) == chapter_number:
            return ch.get("id", "")
    return ""


def _scan_all_chapter_metadata(book_dir: Path) -> list[dict]:
    """扫描 chapters/ 目录下所有 .json 元数据文件"""
    chapters_dir = book_dir / "chapters"
    results = []
    if not chapters_dir.exists():
        return results
    for f in sorted(chapters_dir.glob("chapter-*.json")):
        meta = read_json(str(f))
        if meta:
            results.append(meta)
    results.sort(key=lambda m: m.get("number", 0))
    return results


@router.get("/books/{book_id}/chapter-metadata")
async def list_chapter_metadata(book_id: str):
    """
    获取所有章节元数据列表（v4.0 新增）
    GET /api/books/{id}/chapter-metadata
    """
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    metadata_list = _scan_all_chapter_metadata(book_dir)
    return {"chapters": metadata_list, "total": len(metadata_list)}


@router.get("/books/{book_id}/chapter-metadata/{chapter_number}")
async def get_chapter_metadata(book_id: str, chapter_number: int):
    """
    获取单个章节的元数据（v4.0 新增）
    GET /api/books/{id}/chapter-metadata/{number}
    """
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    meta = _load_chapter_metadata(book_dir, chapter_number)
    if not meta:
        # 尝试从 .md 文件生成基础元数据
        final_path = book_dir / "chapters" / "final" / f"chapter-{chapter_number:04d}.md"
        draft_path = book_dir / "chapters" / "draft" / f"chapter-{chapter_number:04d}.md"
        content = ""
        status = "draft"
        if final_path.exists():
            content = final_path.read_text(encoding="utf-8")
            status = "completed"
        elif draft_path.exists():
            content = draft_path.read_text(encoding="utf-8")

        if content:
            word_count = len(content.replace("\n", "").replace(" ", ""))
            title = _extract_title_from_content(content, chapter_number)
            now_str = time.strftime("%Y-%m-%dT%H:%M:%S")
            meta = {
                "number": chapter_number,
                "title": title,
                "word_count": word_count,
                "outline_chapter_id": _find_outline_chapter_id(book_dir, chapter_number),
                "created_at": now_str,
                "updated_at": now_str,
                "status": status,
            }
            # 保存生成的元数据
            _update_chapter_metadata(book_dir, chapter_number, meta)
        else:
            raise HTTPException(status_code=404, detail=f"章节 {chapter_number} 元数据不存在")

    return meta


@router.get("/books/{book_id}/chapters/{chapter_number}/full")
async def get_chapter_full(book_id: str, chapter_number: int):
    """
    获取章节完整信息：正文 + 元数据（v4.0 新增）
    GET /api/books/{id}/chapters/{number}/full
    """
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    # 查找正文文件
    final_path = book_dir / "chapters" / "final" / f"chapter-{chapter_number:04d}.md"
    draft_path = book_dir / "chapters" / "draft" / f"chapter-{chapter_number:04d}.md"
    # 也尝试 3 位数字格式（兼容旧数据）
    final_path_old = book_dir / "chapters" / "final" / f"chapter-{chapter_number:03d}.md"
    draft_path_old = book_dir / "chapters" / "draft" / f"chapter-{chapter_number:03d}.md"

    content = ""
    version = ""
    if final_path.exists():
        content = final_path.read_text(encoding="utf-8")
        version = "final"
    elif draft_path.exists():
        content = draft_path.read_text(encoding="utf-8")
        version = "draft"
    elif final_path_old.exists():
        content = final_path_old.read_text(encoding="utf-8")
        version = "final"
    elif draft_path_old.exists():
        content = draft_path_old.read_text(encoding="utf-8")
        version = "draft"

    if not content:
        raise HTTPException(status_code=404, detail=f"章节 {chapter_number} 正文不存在")

    # 读取元数据
    meta = _load_chapter_metadata(book_dir, chapter_number)
    if not meta:
        # 自动生成元数据
        word_count = len(content.replace("\n", "").replace(" ", ""))
        title = _extract_title_from_content(content, chapter_number)
        now_str = time.strftime("%Y-%m-%dT%H:%M:%S")
        meta = {
            "number": chapter_number,
            "title": title,
            "word_count": word_count,
            "outline_chapter_id": _find_outline_chapter_id(book_dir, chapter_number),
            "created_at": now_str,
            "updated_at": now_str,
            "status": version,
        }
        _update_chapter_metadata(book_dir, chapter_number, meta)

    return {
        "chapter_number": chapter_number,
        "version": version,
        "content": content,
        "word_count": len(content.replace("\n", "").replace(" ", "")),
        "metadata": meta,
    }

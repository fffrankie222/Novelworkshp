"""
数据管线工具 — 跨模块数据同步
"""
import logging
import time
from pathlib import Path

from app.tools.file_ops import read_json, write_json

logger = logging.getLogger(__name__)


def generate_chapters_from_outline(book_dir: Path, outline_data: dict):
    """从大纲数据自动生成章节条目到 chapters.json"""
    # 优先从 volumes 格式提取（新格式：v4.0 分析同步产出）
    chapters = []
    volumes = outline_data.get("volumes", [])
    if volumes and isinstance(volumes, list):
        for vol in volumes:
            if isinstance(vol, dict):
                for ch in vol.get("chapters", []):
                    if isinstance(ch, dict):
                        # 补充卷信息供后续使用
                        if "volume" not in ch and vol.get("title"):
                            ch["volume"] = vol["title"]
                        chapters.append(ch)
    
    # 回退到旧格式
    if not chapters:
        chapters = outline_data.get("chapters", [])
    if not chapters:
        acts = outline_data.get("acts", [])
        if not acts:
            return
        chapters = []
        for act in acts:
            if isinstance(act, dict) and "chapters" in act:
                chapters.extend(act["chapters"])
    
    if not chapters:
        return
    
    chapters_dir = book_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    chapters_path = chapters_dir / "chapters.json"
    
    existing = read_json(str(chapters_path)) or {"chapters": []}
    existing_chapters = existing.get("chapters", [])
    existing_numbers = {ch.get("chapter_number") for ch in existing_chapters}
    
    new_chapters = []
    auto_num = 1
    for ch in chapters:
        if not isinstance(ch, dict):
            continue
        ch_num = ch.get("number") or ch.get("chapter_number") or auto_num
        auto_num = max(auto_num, ch_num) + 1
        
        if ch_num in existing_numbers:
            for existing_ch in existing_chapters:
                if existing_ch.get("chapter_number") == ch_num:
                    if ch.get("summary") and not existing_ch.get("summary"):
                        existing_ch["summary"] = ch["summary"]
                    if ch.get("title") and not existing_ch.get("title"):
                        existing_ch["title"] = ch["title"]
                    break
            continue
        
        new_chapters.append({
            "id": f"ch-{ch_num:03d}",
            "chapter_id": f"ch-{ch_num:03d}",
            "chapter_number": ch_num,
            "title": ch.get("title", f"第{ch_num}章"),
            "status": "outlined",
            "word_count": 0,
            "volume": ch.get("act", ch.get("volume", "")),
            "summary": ch.get("summary", ""),
            "target_words": 3000,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
    
    if new_chapters:
        existing_chapters.extend(new_chapters)
        existing_chapters.sort(key=lambda c: c.get("chapter_number", 0))
        existing["chapters"] = existing_chapters
        write_json(str(chapters_path), existing)
        logger.info(f"从大纲生成了 {len(new_chapters)} 个章节条目")


def save_chapter_summary(book_dir: Path, chapter_number: int, chapter_title: str, summary: str):
    """将章节摘要写入 chapters/chapters.json"""
    if not summary:
        return
    
    chapters_dir = book_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    chapters_path = chapters_dir / "chapters.json"
    
    existing = read_json(str(chapters_path)) or {"chapters": []}
    chapters_list = existing.get("chapters", [])
    
    found = False
    for ch in chapters_list:
        if ch.get("chapter_number") == chapter_number:
            ch["summary"] = summary
            if chapter_title:
                ch["title"] = chapter_title
            found = True
            break
    
    if not found:
        chapters_list.append({
            "id": f"ch-{chapter_number:03d}",
            "chapter_id": f"ch-{chapter_number:03d}",
            "chapter_number": chapter_number,
            "title": chapter_title or f"第{chapter_number}章",
            "status": "outlined",
            "word_count": 0,
            "volume": "",
            "summary": summary,
            "target_words": 3000,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
    
    existing["chapters"] = chapters_list
    write_json(str(chapters_path), existing)
    logger.info(f"章节 {chapter_number} 摘要已保存")

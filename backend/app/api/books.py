"""
书籍管理 API — 书籍 CRUD、状态查询、配置管理
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config.settings import get_settings
from app.tools.file_ops import ensure_workspace_structure, read_json, write_json, write_file

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()


class CreateBookRequest(BaseModel):
    """创建书籍请求"""
    title: str
    genre: str = "xuanhuan"
    description: str = ""
    target_words_per_chapter: int = 3000
    total_target_chapters: int = 100


class UpdateConfigRequest(BaseModel):
    """更新配置请求"""
    style: Optional[dict] = None
    character_rules: Optional[dict] = None
    world_rules: Optional[dict] = None
    genre_conventions: Optional[dict] = None
    style_guide: Optional[dict] = None


def _default_style_guide() -> dict:
    """结构化写作规范默认值"""
    return {
        "narrative_pov": "",
        "tone": "",
        "dialogue_style": "",
        "chapter_ending_hook": True,
        "chapter_ending_hook_instruction": "每章结尾必须设置悬念钩子或情感锚点，让读者想继续看下一章",
        "pacing": {
            "overall_curve": "",
            "tension_density": "",
            "climax_frequency": "",
        },
        "webnovel_conventions": {
            "face_slapping_rhythm": "",
            "power_progression": "",
            "foreshadowing_rules": "",
        },
        "custom_rules": "",
    }


def get_style_guide_for_prompt(book_dir: Path) -> str:
    """
    读取书籍 style_guide，格式化为可注入 system prompt 的文本块。
    兼容旧格式：如果 style_guide 是字符串，直接返回。
    """
    config_path = book_dir / "config.json"
    if not config_path.exists():
        return ""
    config = read_json(str(config_path))
    sg = config.get("style_guide", "")

    # 向后兼容：旧格式为纯字符串
    if isinstance(sg, str):
        return sg

    if not isinstance(sg, dict):
        return ""

    # 检查是否所有字段为空
    has_content = False

    lines = ["【写作规范】"]

    # 文风语言
    pov = sg.get("narrative_pov", "")
    tone = sg.get("tone", "")
    dialogue = sg.get("dialogue_style", "")
    if pov:
        lines.append(f"- 叙事视角：{pov}")
        has_content = True
    if tone:
        lines.append(f"- 语言风格：{tone}")
        has_content = True
    if dialogue:
        lines.append(f"- 对话风格：{dialogue}")
        has_content = True

    # 章节结尾钩子
    hook_enabled = sg.get("chapter_ending_hook", False)
    hook_inst = sg.get("chapter_ending_hook_instruction", "")
    if hook_enabled or hook_inst:
        hook_text = hook_inst if hook_inst else "每章结尾必须设置悬念钩子或情感锚点"
        lines.append(f"- 章节结尾：{hook_text}")
        has_content = True

    # 节奏
    pacing = sg.get("pacing", {})
    if isinstance(pacing, dict):
        overall = pacing.get("overall_curve", "")
        density = pacing.get("tension_density", "")
        climax = pacing.get("climax_frequency", "")
        pace_parts = []
        if overall:
            pace_parts.append(overall)
        if density:
            pace_parts.append(density)
        if climax:
            pace_parts.append(climax)
        if pace_parts:
            lines.append(f"- 节奏要求：{'，'.join(pace_parts)}")
            has_content = True

    # 网文惯例
    wn = sg.get("webnovel_conventions", {})
    if isinstance(wn, dict):
        face = wn.get("face_slapping_rhythm", "")
        power = wn.get("power_progression", "")
        foreshadow = wn.get("foreshadowing_rules", "")
        wn_parts = []
        if face:
            wn_parts.append(face)
        if power:
            wn_parts.append(power)
        if foreshadow:
            lines.append(f"- 伏笔规则：{foreshadow}")
            has_content = True
        if wn_parts:
            lines.append(f"- 网文惯例：{'，'.join(wn_parts)}")
            has_content = True

    # 自定义规则
    custom = sg.get("custom_rules", "")
    if custom:
        lines.append(f"- 其他规则：{custom}")
        has_content = True

    if not has_content:
        return ""

    return "\n".join(lines)


def _get_workspaces_dir() -> Path:
    """获取工作区根目录"""
    return Path(settings.base_dir) / settings.data_dir / "workspaces"


def _get_book_dir(book_id: str) -> Path:
    """获取指定书籍的工作区路径"""
    return _get_workspaces_dir() / book_id


def _list_books() -> list[dict]:
    """列出所有书籍 — 返回与前端 Book 类型一致的字段"""
    ws_dir = _get_workspaces_dir()
    if not ws_dir.exists():
        return []
    
    books = []
    for book_dir in ws_dir.iterdir():
        if book_dir.is_dir():
            config_path = book_dir / "config.json"
            if config_path.exists():
                config = read_json(str(config_path))
                
                # Count chapters and words for stats
                total_chapters = 0
                total_words = 0
                draft_dir = book_dir / "chapters" / "draft"
                final_dir = book_dir / "chapters" / "final"
                if draft_dir.exists():
                    total_chapters += len(list(draft_dir.glob("*.md")))
                if final_dir.exists():
                    total_chapters += len(list(final_dir.glob("*.md")))
                    for f in final_dir.glob("*.md"):
                        content = read_file(str(f))
                        total_words += len(content)
                if draft_dir.exists():
                    for f in draft_dir.glob("*.md"):
                        content = read_file(str(f))
                        total_words += len(content)
                
                books.append({
                    "id": book_dir.name,
                    "title": config.get("book_title", book_dir.name),
                    "genre": config.get("genre", ""),
                    "description": config.get("description", ""),
                    "total_words": total_words,
                    "total_chapters": total_chapters,
                    "active_hooks": 0,
                    "created_at": config.get("created_at", ""),
                    "updated_at": config.get("updated_at", ""),
                })
    return books


@router.get("")
async def list_books():
    """书籍列表"""
    books = _list_books()
    return {"books": books, "total": len(books)}


@router.post("")
async def create_book(request: CreateBookRequest):
    """创建新书（初始化工作区目录结构）"""
    # 生成 book_id
    book_id = f"book-{int(time.time())}"
    book_dir = _get_book_dir(book_id)
    
    if book_dir.exists():
        raise HTTPException(status_code=400, detail=f"书籍 {book_id} 已存在")
    
    # 初始化目录结构
    ensure_workspace_structure(str(book_dir), book_id)
    
    # 写入配置
    config = {
        "book_id": book_id,
        "book_title": request.title,
        "genre": request.genre,
        "description": request.description,
        "target_words_per_chapter": request.target_words_per_chapter,
        "total_target_chapters": request.total_target_chapters,
        "status": "draft",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "style": {
            "narrative_pov": "third_person_limited",
            "narrative_tense": "past",
            "tone_tags": [],
            "language_level": "通俗白话",
            "forbidden_patterns": [],
            "preferred_techniques": [],
        },
        "character_rules": {"hard_constraints": [], "soft_preferences": []},
        "world_rules": {"hard_constraints": [], "soft_constraints": []},
        "genre_conventions": {
            "genre": request.genre,
            "reader_expectations": [],
            "pacing_rules": {
                "max_consecutive_calm_chapters": 2,
                "required_hooks_per_chapter": 1,
                "chapter_end_must_have_hook": True,
            },
        },
        "style_guide": _default_style_guide(),
    }
    
    write_json(str(book_dir / "config.json"), config)
    
    # Return full Book object matching frontend type
    return {
        "id": book_id,
        "title": request.title,
        "genre": request.genre,
        "description": request.description,
        "total_words": 0,
        "total_chapters": 0,
        "active_hooks": 0,
        "created_at": config["created_at"],
        "updated_at": config["updated_at"],
    }


@router.get("/{book_id}")
async def get_book(book_id: str):
    """书籍详情"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")
    
    config = read_json(str(book_dir / "config.json"))
    
    # 统计信息
    draft_count = len(list((book_dir / "chapters" / "draft").glob("*.md"))) if (book_dir / "chapters" / "draft").exists() else 0
    final_count = len(list((book_dir / "chapters" / "final").glob("*.md"))) if (book_dir / "chapters" / "final").exists() else 0
    
    return {
        "book_id": book_id,
        "config": config,
        "stats": {
            "draft_chapters": draft_count,
            "finalized_chapters": final_count,
        },
    }


@router.get("/{book_id}/config")
async def get_config(book_id: str):
    """获取写作配置"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")
    
    config = read_json(str(book_dir / "config.json"))
    return {
        "book_id": book_id,
        "style": config.get("style", {}),
        "character_rules": config.get("character_rules", {}),
        "world_rules": config.get("world_rules", {}),
        "genre_conventions": config.get("genre_conventions", {}),
        "style_guide": config.get("style_guide", {}),
    }


@router.put("/{book_id}/config")
async def update_config(book_id: str, request: UpdateConfigRequest):
    """更新写作配置"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")
    
    config = read_json(str(book_dir / "config.json"))
    
    if request.style is not None:
        config["style"].update(request.style)
    if request.character_rules is not None:
        config["character_rules"].update(request.character_rules)
    if request.world_rules is not None:
        config["world_rules"].update(request.world_rules)
    if request.genre_conventions is not None:
        config["genre_conventions"].update(request.genre_conventions)
    if request.style_guide is not None:
        # 确保 style_guide 存在且为 dict
        if not isinstance(config.get("style_guide"), dict):
            config["style_guide"] = _default_style_guide()
        # 深合并：顶层字段
        for key, value in request.style_guide.items():
            if isinstance(value, dict) and isinstance(config["style_guide"].get(key), dict):
                # 二级深合并（pacing, webnovel_conventions 等）
                config["style_guide"][key].update(value)
            else:
                config["style_guide"][key] = value
    
    config["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    write_json(str(book_dir / "config.json"), config)
    
    return {"message": "配置已更新", "updated_fields": list(request.dict(exclude_none=True).keys())}


@router.get("/{book_id}/state/characters")
async def get_character_states(book_id: str):
    """角色状态"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")
    
    states = read_json(str(book_dir / "state" / "character_states.json"))
    return states


@router.get("/{book_id}/state/hooks")
async def get_hook_ledger(book_id: str):
    """伏笔数据（v4.0: 统一从 outline.json.foreshadowing 读取）"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    outline_data = read_json(str(book_dir / "outline" / "outline.json")) or {}
    foreshadowing = outline_data.get("foreshadowing", [])
    return {"hooks": foreshadowing, "total": len(foreshadowing)}


@router.get("/{book_id}/state/timeline")
async def get_timeline(book_id: str):
    """时间线"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")
    
    timeline = read_json(str(book_dir / "timeline" / "timeline.json"))
    return timeline

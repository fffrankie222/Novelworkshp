"""
文件操作工具 — Agent 使用的 tool（读写书籍工作区中的文件）
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_file(file_path: str) -> str:
    """读取文件内容"""
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"文件不存在: {file_path}")
        return ""
    return path.read_text(encoding="utf-8")


def write_file(file_path: str, content: str) -> bool:
    """写入文件"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info(f"文件已写入: {file_path} ({len(content)} 字符)")
    return True


def read_json(file_path: str) -> dict:
    """读取 JSON 文件，对空文件/损坏文件自动修复"""
    path = Path(file_path)
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            logger.warning(f"JSON 文件为空，自动修复: {file_path}")
            return {}
        return json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"JSON 解析失败: {file_path} ({e})，尝试自动修复")
        # 尝试修复：备份损坏文件，写入空 JSON
        try:
            backup = path.with_suffix(".json.broken")
            path.rename(backup)
            path.write_text("{}", encoding="utf-8")
            logger.info(f"已备份损坏文件为 {backup}，重置为空 JSON")
        except Exception:
            pass
        return {}


def write_json(file_path: str, data: dict) -> bool:
    """写入 JSON 文件"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return True


def list_files(directory: str, pattern: str = "*") -> list[str]:
    """列出目录中的文件"""
    path = Path(directory)
    if not path.exists():
        return []
    return [str(f) for f in path.glob(pattern) if f.is_file()]


def ensure_workspace_structure(workspace_path: str, book_id: str):
    """确保书籍工作区目录结构完整"""
    ws = Path(workspace_path)
    dirs = [
        "world",
        "characters/relations",
        "outline/chapters",
        "timeline",
        "chapters/draft",
        "chapters/final",
        "chapters/summaries",
        "state",
        "runtime",
    ]
    for d in dirs:
        (ws / d).mkdir(parents=True, exist_ok=True)
    
    # 初始化 state 文件（如果不存在）
    # 注：伏笔已统一到 outline.json.foreshadowing（hooks.py 唯一数据源），
    # 不再创建 state/hook_ledger.json 空模板（审计 1.3/Y6 残留清理）。
    state_files = {
        "state/character_states.json": {"characters": {}},
        "state/world_state.json": {"faction_relations": {}, "active_events": [], "last_updated": ""},
        "state/chapter_states.json": {"chapters": {}},
        "timeline/timeline.json": {"events": [], "time_system": {}},
        "world/world_data.json": {
            "geography": "",
            "factions": [],
            "power_system": "",
            "history": "",
            "social_rules": "",
        },
        "characters/characters.json": {"characters": []},
        "outline/outline.json": {"acts": [], "chapters": []},
    }
    
    for rel_path, default_data in state_files.items():
        file_path = ws / rel_path
        needs_init = False
        if not file_path.exists():
            needs_init = True
        else:
            # 检查文件是否为空或内容无效
            try:
                content = file_path.read_text(encoding="utf-8").strip()
                if not content:
                    needs_init = True
                    logger.warning(f"文件为空，将重新初始化: {file_path}")
            except Exception:
                needs_init = True
        if needs_init:
            write_json(str(file_path), default_data)
    
    logger.info(f"工作区结构已初始化: {workspace_path}")

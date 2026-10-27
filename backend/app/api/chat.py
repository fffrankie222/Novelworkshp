"""
通用对话式写作 API — 支持多场景（世界观 / 角色 / 大纲 / 写作）的多轮对话
每个场景独立存储对话历史，writing 场景自动注入前序场景已确认的成果作为上下文
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config.settings import get_settings
from app.api.books import _get_book_dir, get_style_guide_for_prompt
from app.tools.file_ops import read_json, write_json, read_file
from app.utils.data_pipeline import generate_chapters_from_outline, save_chapter_summary
from app.llm.router import get_model_router, LLMError

logger = logging.getLogger(__name__)
router = APIRouter()

# ──────────────────────────────────────────────────────────────────────────────
# 常量
# ──────────────────────────────────────────────────────────────────────────────

VALID_CONTEXTS = ["worldbuilding", "character", "outline", "writing"]

# ── 结构化输出格式规范（所有场景共用） ──
STRUCTURED_OUTPUT_INSTRUCTION = """

---
【数据标记规范】
当你的回复涉及设定信息的新增或修改时，请在回复的合适位置（通常在相关讨论之后）添加一个简短的数据标记块：
<!--DATA:{"字段名": "字段值"}-->

注意：
- 数据标记只是你回复的一小部分，你的回复仍然应该包含充分的讨论、解释、建议等自然语言内容
- 标记块应简洁，只包含有实质变更的字段和值
- 字段值是该字段的完整最新内容
- 如果本次回复没有设定变更（只是讨论、提问或解释），不需要添加标记块
- 标记块内的 JSON 必须合法

"""

WORLD_STRUCTURED_FIELDS = """当前场景可标记字段：geography(地理环境)、factions(势力)、power_system(力量体系)、history(历史)、social_rules(社会规则)
示例：<!--DATA:{"factions": "天剑宗：正派第一大宗门，以剑道闻名...", "power_system": "修炼分为练气、筑基、金丹、元婴四个大境界..."}-->"""

CHARACTER_STRUCTURED_FIELDS = """当前场景可标记字段：characters(角色列表，JSON数组)
角色数组中每个角色包含：name(姓名)、role(身份)、personality(性格)、background(背景)、motivation(动机)、abilities(能力)
示例：<!--DATA:{"characters": [{"name": "李逍遥", "role": "主角", "personality": "洒脱不羁", "background": "渔村少年", "motivation": "寻找身世真相"}, {"name": "赵灵儿", "role": "女主", "personality": "温柔善良"}]}-->
重要：每次都要输出所有已知角色的完整信息，不要只输出新讨论的角色。"""

OUTLINE_STRUCTURED_FIELDS = """当前场景可标记字段：core_conflict(核心冲突)、main_plot(主线剧情)、volumes(卷章节结构，JSON数组)、foreshadowing(伏笔)、pacing_notes(节奏安排)
volumes 格式：[{"title": "卷名", "chapters": [{"number": 1, "title": "章名", "summary": "摘要"}]}]
示例：<!--DATA:{"core_conflict": "正邪对决", "volumes": [{"title": "第一卷·初入江湖", "chapters": [{"number": 1, "title": "渔村少年", "summary": "主角出场..."}]}]}-->
提及角色时请使用 @角色名 格式（如 @李逍遥），系统会自动关联角色信息。"""

WRITING_STRUCTURED_FIELDS = """当前场景可标记字段：chapter_title(章节标题)、chapter_summary(章节摘要)、chapter_content(正文内容)
提及角色时请使用 @角色名 格式（如 @李逍遥），系统会自动关联角色信息。"""

# 各场景的 System Prompt
CONTEXT_SYSTEM_PROMPTS = {
    "worldbuilding": (
        "你是一个资深网文世界观架构师。你正在和作者一起构建小说的世界设定。\n"
        "你需要帮助作者建立：地理环境、势力阵营、力量体系、历史背景、社会规则等。\n"
        "通过多轮对话逐步完善世界设定。每次回复简洁有建设性，一次只聚焦 1-2 个方面。\n"
        "当世界观基本成型时，建议作者确认当前设定并进入下一步。"
        + STRUCTURED_OUTPUT_INSTRUCTION + WORLD_STRUCTURED_FIELDS
    ),
    "character": (
        "你是一个专业的角色设计师。你正在帮作者设计立体的小说角色。\n"
        "你需要关注：外貌特征、性格特点、背景故事、行为动机、角色关系网。\n"
        "通过对话帮助作者让角色变得有血有肉、有辨识度。\n"
        "每次聚焦一个角色或一组关系，一次只问 1-2 个关键问题。"
        + STRUCTURED_OUTPUT_INSTRUCTION + CHARACTER_STRUCTURED_FIELDS
    ),
    "outline": (
        "你是一个资深的剧情策划。你正在帮作者规划大纲和剧情走向。\n"
        "你需要梳理：核心冲突、主线剧情、章节结构、节奏安排、伏笔布局。\n"
        "通过对话帮作者理清故事脉络。每次回复简洁有建设性。\n"
        "当大纲基本成型时，建议作者确认大纲。"
        + STRUCTURED_OUTPUT_INSTRUCTION + OUTLINE_STRUCTURED_FIELDS
    ),
    "writing": (
        "你是一个专业的网文写手。你正在基于已确认的设定、角色和大纲撰写正文。\n"
        "文风要求：画面感强、对话生动、节奏紧凑、情绪饱满。\n"
        "严格按照已确认的世界观、角色设定和大纲来写，不要自由发挥偏离设定。\n"
        "用户会提出修改意见，你要灵活响应。"
        + STRUCTURED_OUTPUT_INSTRUCTION + WRITING_STRUCTURED_FIELDS
    ),
}

# 各 context 对应的 LLM task_type
CONTEXT_TASK_TYPE = {
    "worldbuilding": "reasoning",
    "character": "reasoning",
    "outline": "reasoning",
    "writing": "creative_bulk",
}

# 各 context 默认建议
CONTEXT_DEFAULT_SUGGESTIONS = {
    "worldbuilding": [
        "聊聊力量体系",
        "设定主要势力",
        "描述地理环境",
        "梳理历史背景",
    ],
    "character": [
        "设计主角",
        "设定反派角色",
        "梳理角色关系",
        "完善角色背景",
    ],
    "outline": [
        "讨论核心冲突",
        "规划主线剧情",
        "安排章节结构",
        "设计伏笔布局",
    ],
    "writing": [
        "开始写第一章",
        "加入更多对话",
        "加快节奏",
        "这段改一下",
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
# 请求模型
# ──────────────────────────────────────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    """发送对话消息"""
    message: str
    context: str = "outline"  # worldbuilding | character | outline | writing
    suppress_auto_sync: bool = False  # 分析同步审核期间禁止自动写入结构化数据
    chapter_number: Optional[int] = None  # writing 场景：前端章节下拉选中的章节号，用于同步 stage_data.current_chapter


class ConfirmContextRequest(BaseModel):
    """确认当前 context 的成果"""
    context: str
    context_id: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# 内部工具函数 — 数据读写
# ──────────────────────────────────────────────────────────────────────────────

def _get_chat_path(book_dir: Path, context: str) -> Path:
    """获取指定 context 的对话数据文件路径"""
    runtime_dir = book_dir / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / f"chat_{context}.json"


def _load_chat_data(book_dir: Path, context: str) -> dict:
    """加载对话数据，不存在则初始化"""
    chat_path = _get_chat_path(book_dir, context)
    if chat_path.exists():
        data = read_json(str(chat_path))
        if "messages" not in data:
            data = _init_chat_data(context)
            write_json(str(chat_path), data)
        return data
    else:
        data = _init_chat_data(context)
        write_json(str(chat_path), data)
        return data


def _init_chat_data(context: str) -> dict:
    """初始化对话数据结构"""
    stage_data = _default_stage_data(context)
    return {
        "context": context,
        "messages": [],
        "confirmed": False,
        "stage_data": stage_data,
        "checkpoint": None,  # 断点：确认阶段后保存的历史压缩摘要
    }


def _default_stage_data(context: str) -> dict:
    """各 context 的默认 stage_data"""
    if context == "worldbuilding":
        return {"world_text": ""}
    elif context == "character":
        return {"character_id": "", "character_data": {}}
    elif context == "outline":
        return {"outline_text": ""}
    elif context == "writing":
        return {"current_chapter": 1, "chapter_summary": ""}
    return {}


def _save_chat_data(book_dir: Path, context: str, data: dict):
    """保存对话数据"""
    chat_path = _get_chat_path(book_dir, context)
    write_json(str(chat_path), data)


# ──────────────────────────────────────────────────────────────────────────────
# 内部工具函数 — 跨 context 成果注入
# ──────────────────────────────────────────────────────────────────────────────

def _collect_confirmed_data(book_dir: Path) -> dict:
    """
    收集所有 context 中已确认的成果，用于注入到 writing 的 system prompt。
    返回: {
        "world_text": "...",
        "characters_summary": "...",
        "outline_text": "...",
    }
    """
    result = {}

    # 1. 世界观
    world_data = read_json(str(book_dir / "world" / "world_data.json"))
    if world_data:
        parts = []
        if world_data.get("geography"):
            parts.append(f"地理环境：{world_data['geography']}")
        if world_data.get("power_system"):
            parts.append(f"力量体系：{world_data['power_system']}")
        if world_data.get("history"):
            parts.append(f"历史背景：{world_data['history']}")
        if world_data.get("social_rules"):
            parts.append(f"社会规则：{world_data['social_rules']}")
        if world_data.get("factions"):
            faction_names = []
            for f in world_data["factions"][:10]:
                if isinstance(f, dict):
                    faction_names.append(f.get("name", str(f)))
                else:
                    faction_names.append(str(f))
            parts.append(f"主要势力：{', '.join(faction_names)}")
        if parts:
            result["world_text"] = "\n".join(parts)

    # 同时从对话成果中读取（如果 worldbuilding 对话已确认）
    world_chat_path = _get_chat_path(book_dir, "worldbuilding")
    if world_chat_path.exists():
        world_chat = read_json(str(world_chat_path))
        if world_chat.get("confirmed") and world_chat.get("stage_data", {}).get("world_text"):
            if "world_text" not in result:
                result["world_text"] = world_chat["stage_data"]["world_text"]

    # 2. 角色
    char_data = read_json(str(book_dir / "characters" / "characters.json"))
    characters = char_data.get("characters", [])
    if characters:
        char_parts = []
        for c in characters[:15]:
            name = c.get("name", "未知")
            role = c.get("role", "")
            tag = c.get("tag", "")
            desc = c.get("description", "")
            personality = c.get("personality", "")
            background = c.get("background", "")
            motivation = c.get("motivation", "")
            abilities = c.get("abilities", "")
            catchphrase = c.get("catchphrase", "")
            entry = f"- {name}"
            if role:
                entry += f"（{role}）"
            if tag:
                entry += f" [{tag}]"
            if personality:
                entry += f"\n  性格：{personality}"
            if background:
                entry += f"\n  背景：{background}"
            if motivation:
                entry += f"\n  动机：{motivation}"
            if abilities:
                entry += f"\n  能力：{abilities}"
            if catchphrase:
                entry += f"\n  口头禅：{catchphrase}"
            if desc and not background:
                entry += f"\n  简介：{desc}"
            char_parts.append(entry)
        result["characters_summary"] = "\n".join(char_parts)

    # 3. 大纲
    outline_data = read_json(str(book_dir / "outline" / "outline.json"))
    if outline_data:
        outline_parts = []

        # ── 新格式：volumes 数组 ──
        volumes = outline_data.get("volumes", [])
        if volumes:
            for vol in volumes[:20]:
                if isinstance(vol, dict):
                    vol_title = vol.get("title", "")
                    vol_arc = vol.get("story_arc", "")
                    outline_parts.append(f"【第{vol.get('number', '')}卷】{vol_title}：{vol_arc}")
                    for ch in vol.get("chapters", [])[:30]:
                        if isinstance(ch, dict):
                            ch_summary = ch.get("summary", "")
                            summary_text = f" — {ch_summary}" if ch_summary else ""
                            outline_parts.append(f"  第{ch.get('number', '')}章 {ch.get('title', '')}{summary_text}")

        # ── 伏笔 ──
        foreshadows = outline_data.get("foreshadowing", [])
        if foreshadows:
            outline_parts.append("\n[伏笔]")
            for fs in foreshadows[:20]:
                if isinstance(fs, dict):
                    chars = ", ".join(fs.get("characters", [])) or "未知"
                    outline_parts.append(
                        f"  - {fs.get('purpose', '')} | 第{fs.get('start_chapter', '?')}章→第{fs.get('end_chapter', '?')}章 "
                        f"| 人物: {chars} | 状态: {fs.get('status', 'planted')}"
                    )

        # ── 兼容旧格式：outline 字段 ──
        if not volumes:
            outline_nodes = outline_data.get("outline", [])
            chapters = outline_data.get("chapters", [])
            acts = outline_data.get("acts", [])

            if acts:
                for act in acts[:10]:
                    if isinstance(act, dict):
                        outline_parts.append(f"幕：{act.get('title', '')} — {act.get('description', '')}")
                    else:
                        outline_parts.append(str(act))

            if outline_nodes:
                for node in outline_nodes[:30]:
                    if isinstance(node, dict):
                        if node.get("type") == "volume":
                            outline_parts.append(f"【卷】{node.get('title', '')}")
                            for child in node.get("children", [])[:20]:
                                if isinstance(child, dict) and child.get("type") == "chapter":
                                    ch_summary = child.get("summary", "")
                                    summary_text = f"：{ch_summary}" if ch_summary else ""
                                    outline_parts.append(f"  第{child.get('chapter_number', '')}章 {child.get('title', '')}{summary_text}")
                        elif node.get("type") == "chapter":
                            ch_summary = node.get("summary", "")
                            summary_text = f"：{ch_summary}" if ch_summary else ""
                            outline_parts.append(f"第{node.get('chapter_number', '')}章 {node.get('title', '')}{summary_text}")

            if chapters:
                for ch in chapters[:20]:
                    if isinstance(ch, dict):
                        ch_summary = ch.get("summary", "")
                        summary_text = f"：{ch_summary}" if ch_summary else ""
                        outline_parts.append(f"第{ch.get('number', ch.get('chapter_number', ''))}章 {ch.get('title', '')}{summary_text}")

        if outline_parts:
            result["outline_text"] = "\n".join(outline_parts)

    # 同时从对话成果中读取
    outline_chat_path = _get_chat_path(book_dir, "outline")
    if outline_chat_path.exists():
        outline_chat = read_json(str(outline_chat_path))
        if outline_chat.get("confirmed") and outline_chat.get("stage_data", {}).get("outline_text"):
            if "outline_text" not in result:
                result["outline_text"] = outline_chat["stage_data"]["outline_text"]

    # 补充：即使 chat 未 confirmed，也从 data files 读取 chat_derived 数据
    # 这样对话提取的结构化数据也能被 writing 使用
    if "world_text" not in result:
        world_data = read_json(str(book_dir / "world" / "world_data.json")) or {}
        chat_derived = world_data.get("chat_derived_summary", "")
        if chat_derived:
            result["world_text"] = chat_derived

    if "characters_summary" not in result:
        char_data = read_json(str(book_dir / "characters" / "characters.json")) or {}
        chat_derived = char_data.get("chat_derived_summary", "")
        if chat_derived:
            result["characters_summary"] = chat_derived

    if "outline_text" not in result:
        outline_data = read_json(str(book_dir / "outline" / "outline.json")) or {}
        chat_derived = outline_data.get("chat_derived_summary", "")
        # 同时检查结构化的章节数据（兼容多种格式）
        chapters = outline_data.get("chapters", [])
        chapter_parts = []
        for ch in chapters[:30]:
            if isinstance(ch, dict):
                ch_summary = ch.get("summary", "")
                summary_text = f"：{ch_summary}" if ch_summary else ""
                chapter_parts.append(f"第{ch.get('number', ch.get('chapter_number', ''))}章 {ch.get('title', '')}{summary_text}")
        if chapter_parts:
            derived_text = chat_derived + "\n\n--- 章节列表 ---\n" + "\n".join(chapter_parts) if chat_derived else "\n".join(chapter_parts)
            result["outline_text"] = derived_text
        elif chat_derived:
            result["outline_text"] = chat_derived

    return result


def _get_book_info_for_prompt(book_dir: Path) -> str:
    """读取书籍配置，生成注入到 system prompt 的书籍基本信息（不含 style_guide，由 _build_system_prompt 单独注入）"""
    config_path = book_dir / "config.json"
    if not config_path.exists():
        return ""
    config = read_json(str(config_path))
    title = config.get("book_title", "未知")
    genre = config.get("genre", "未知")
    description = config.get("description", "")
    parts = [f"书名：{title}", f"题材：{genre}"]
    if description:
        parts.append(f"简介：{description}")
    return "\n".join(parts)


# ──────────────────────────────────────────────────────────────────────────────
# 内部工具函数 — LLM 调用
# ──────────────────────────────────────────────────────────────────────────────

def _build_system_prompt(book_dir: Path, context: str, chat_data: dict) -> str:
    """构建完整的 system prompt"""
    prompt_parts = [CONTEXT_SYSTEM_PROMPTS.get(context, CONTEXT_SYSTEM_PROMPTS["outline"])]

    # 注入书籍基本信息
    book_info = _get_book_info_for_prompt(book_dir)
    if book_info:
        prompt_parts.append(f"\n\n--- 书籍基本信息 ---\n{book_info}")

    # 注入结构化写作规范（所有 context 都注入，writing 尤其重要）
    style_guide_text = get_style_guide_for_prompt(book_dir)
    if style_guide_text:
        prompt_parts.append(f"\n\n{style_guide_text}")

    # writing 场景：使用 WritingContext Service 统一注入上下文（v4.0）
    if context == "writing":
        from app.services.writing_context import WritingContextService

        stage_data = chat_data.get("stage_data", {})
        current_ch = stage_data.get("current_chapter", 1)

        # 提取 book_id（从 book_dir 路径解析）
        book_id = book_dir.name if hasattr(book_dir, 'name') else str(book_dir).rsplit('/', 1)[-1]

        # 调用 WritingContext Service 获取 10 项上下文
        wc_service = WritingContextService(book_id)
        ctx = wc_service.get_writing_context(current_ch)

        # 遍历 10 项上下文，按名称注入到 system prompt
        for item in ctx.get("items", []):
            content = item.get("content", "")
            name = item.get("name", "")
            if not content or content.startswith("（"):
                continue
            if name == "世界观精简版":
                prompt_parts.append(f"\n\n--- 世界观设定 ---\n{content}")
            elif name == "当前卷故事线":
                prompt_parts.append(f"\n\n{content}")
            elif name == "当前章信息":
                prompt_parts.append(f"\n\n{content}")
            elif name == "前 10 章摘要":
                prompt_parts.append(f"\n\n{content}")
            elif name == "后 5 章预告":
                prompt_parts.append(f"\n\n{content}")
            elif name == "出场角色详细卡":
                prompt_parts.append(f"\n\n{content}")
            elif name == "活跃伏笔":
                prompt_parts.append(f"\n\n{content}")
            # 风格指南和写作规则已在外层统一注入，不重复

    # character 场景：注入已有角色列表 + 世界观数据
    elif context == "character":
        char_data = read_json(str(book_dir / "characters" / "characters.json"))
        characters = char_data.get("characters", [])
        if characters:
            char_parts = []
            for c in characters[:10]:
                name = c.get("name", "未知")
                role = c.get("role", "")
                entry = f"- {name}"
                if role:
                    entry += f"（{role}）"
                char_parts.append(entry)
            prompt_parts.append(f"\n\n--- 已有角色 ---\n" + "\n".join(char_parts))
        # 注入世界观数据，让角色对话知道世界设定（截断防止 prompt 过长）
        confirmed = _collect_confirmed_data(book_dir)
        if confirmed.get("world_text"):
            world_text = confirmed['world_text'][:2000]
            prompt_parts.append(f"\n\n--- 已确认的世界观设定 ---\n{world_text}")

    # outline 场景：注入世界观和角色信息（截断防止 prompt 过长导致超时）
    elif context == "outline":
        confirmed = _collect_confirmed_data(book_dir)
        if confirmed.get("world_text"):
            world_text = confirmed['world_text'][:2000]
            prompt_parts.append(f"\n\n--- 已确认的世界观设定 ---\n{world_text}")
        if confirmed.get("characters_summary"):
            chars_text = confirmed['characters_summary'][:2000]
            prompt_parts.append(f"\n\n--- 已确认的角色设定 ---\n{chars_text}")
        # 【新增】注入角色名列表，让 AI 知道可以用 @角色名 引用
        char_path = book_dir / "characters" / "characters.json"
        if char_path.exists():
            char_data = read_json(str(char_path))
            char_names = [c.get("name", "") for c in char_data.get("characters", []) if c.get("name")]
            if char_names:
                prompt_parts.append(f"\n\n--- 可用角色（可在大纲中用 @角色名 引用） ---\n" + "、".join(f"@{n}" for n in char_names))

    # worldbuilding 场景：注入角色和大纲信息（同样截断）
    elif context == "worldbuilding":
        confirmed = _collect_confirmed_data(book_dir)
        if confirmed.get("characters_summary"):
            chars_text = confirmed['characters_summary'][:2000]
            prompt_parts.append(f"\n\n--- 已确认的角色设定 ---\n{chars_text}")
        if confirmed.get("outline_text"):
            outline_text = confirmed['outline_text'][:2000]
            prompt_parts.append(f"\n\n--- 已确认的大纲设定 ---\n{outline_text}")

    return "\n".join(prompt_parts)


def _build_llm_messages(book_dir: Path, context: str, chat_data: dict, user_message: str) -> list[dict]:
    """
    构建发送给 LLM 的消息列表。
    支持断点机制：如果存在 checkpoint，则注入压缩摘要 + 仅发送断点后的新消息；
    否则回退到最近 20 条历史。
    """
    system_content = _build_system_prompt(book_dir, context, chat_data)

    # 如果有断点，将压缩摘要注入 system prompt
    checkpoint = chat_data.get("checkpoint")
    if checkpoint and checkpoint.get("summary"):
        system_content += (
            "\n\n--- 历史对话摘要（断点前） ---\n"
            "以下是之前对话的压缩摘要，包含了已确定的关键决策和设定：\n"
            f"{checkpoint['summary']}\n"
            "--- 摘要结束 ---\n"
            "请基于以上摘要继续与作者对话，不要重复已经确定的内容。"
        )

    messages = [{"role": "system", "content": system_content}]

    all_messages = chat_data.get("messages", [])

    if checkpoint:
        # 只取断点之后的消息
        checkpoint_idx = checkpoint.get("message_index", 0)
        history = all_messages[checkpoint_idx:]
        logger.debug(f"使用断点模式: 跳过前 {checkpoint_idx} 条消息，发送 {len(history)} 条新消息")
    else:
        # 无断点：取最近 20 条
        history = all_messages[-20:]

    for msg in history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"],
        })

    # 用户新消息
    messages.append({"role": "user", "content": user_message})
    return messages


# ──────────────────────────────────────────────────────────────────────────────
# 内部工具函数 — 断点（Checkpoint）机制
# ──────────────────────────────────────────────────────────────────────────────

async def _create_checkpoint(book_dir: Path, context: str, chat_data: dict) -> dict:
    """
    在确认阶段时创建断点：将当前对话历史压缩为摘要，
    后续对话只需注入摘要 + 断点之后的新消息，避免上下文过长。
    返回 checkpoint 字典。
    """
    messages = chat_data.get("messages", [])
    if not messages:
        return None

    # 将对话历史格式化为文本供 LLM 总结
    conversation_text = ""
    for msg in messages:
        role_label = "作者" if msg["role"] == "user" else "AI助手"
        content = msg.get("content", "")[:1000]  # 截断过长的单条消息
        conversation_text += f"[{role_label}]: {content}\n\n"

    context_labels = {
        "worldbuilding": "世界观设定",
        "character": "角色设计",
        "outline": "大纲规划",
        "writing": "正文写作",
    }
    context_label = context_labels.get(context, context)

    summarize_messages = [
        {
            "role": "system",
            "content": (
                "你是一个专业的信息压缩助手。你需要将一段关于小说创作的对话历史压缩为简洁的摘要。\n"
                "摘要应保留所有关键决策、已确定的设定、重要的讨论结论。\n"
                "去掉寒暄、重复内容、无意义的追问。\n"
                "输出应为结构化的 Markdown 格式，方便后续作为上下文注入。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"以下是关于「{context_label}」的对话历史，共 {len(messages)} 条消息。\n"
                f"请压缩为简洁的摘要：\n\n{conversation_text}"
            ),
        },
    ]

    try:
        model_router = get_model_router()
        summary, _ = await model_router.call_with_fallback(
            messages=summarize_messages,
            task_type="reasoning",
            temperature=0.3,
            max_tokens=2000,
        )
    except Exception as e:
        logger.warning(f"创建断点摘要失败，将使用简单截断: {e}")
        # 降级：简单截取最后几条消息的关键内容
        last_msgs = messages[-6:]
        summary_parts = []
        for msg in last_msgs:
            role_label = "作者" if msg["role"] == "user" else "AI"
            summary_parts.append(f"[{role_label}]: {msg.get('content', '')[:200]}")
        summary = "（自动压缩失败，以下为最近对话节选）\n" + "\n".join(summary_parts)

    # 读取当前已确认的结构化数据作为 checkpoint 的一部分
    confirmed_data = _collect_confirmed_data(book_dir)

    checkpoint = {
        "message_index": len(messages),  # 断点位置：当前消息总数
        "summary": summary,
        "confirmed_data": confirmed_data,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    logger.info(f"断点已创建: context={context}, messages_compressed={len(messages)}")
    return checkpoint


# ──────────────────────────────────────────────────────────────────────────────
# 内部工具函数 — 建议生成
# ──────────────────────────────────────────────────────────────────────────────

def _generate_suggestions(context: str, chat_data: dict) -> list[str]:
    """根据当前 context 和对话状态生成快捷操作建议"""
    msg_count = len(chat_data.get("messages", []))
    defaults = CONTEXT_DEFAULT_SUGGESTIONS.get(context, [])

    suggestions = list(defaults)

    # 如果对话已经足够多，追加"确认成果"的建议
    if msg_count >= 6 and not chat_data.get("confirmed"):
        label_map = {
            "worldbuilding": "确认世界观设定",
            "character": "确认角色设定",
            "outline": "确认大纲",
            "writing": "继续下一章",
        }
        suggestions.append(label_map.get(context, "确认当前成果"))

    return suggestions


# ──────────────────────────────────────────────────────────────────────────────
# 内部工具函数 — 结构化数据提取
# ──────────────────────────────────────────────────────────────────────────────

def _extract_structured_updates_field_map(context: str) -> tuple[list[str], str]:
    """返回 (字段列表, 字段描述) 用于提取"""
    if context == "worldbuilding":
        return (
            ["geography", "factions", "power_system", "history", "social_rules"],
            "地理环境、势力分布、力量体系、历史年表、社会规则"
        )
    elif context == "character":
        return (
            ["name", "role", "personality", "background", "motivation", "abilities"],
            "角色姓名、身份定位、性格特点、背景故事、行为动机、能力特长"
        )
    elif context == "outline":
        return (
            ["core_conflict", "main_plot", "volumes", "foreshadowing", "pacing_notes"],
            "核心冲突、主线剧情、卷章节结构(volumes JSON数组)、伏笔布局、节奏安排"
        )
    elif context == "writing":
        return (
            ["chapter_title", "chapter_summary", "chapter_content"],
            "章节标题、章节摘要、章节正文内容"
        )
    return [], ""


import re as _re_module  # 避免与已有的 import re as _re 冲突

def _parse_structured_from_reply(reply_text: str) -> dict:
    """
    从 AI 回复中解析 <!--DATA:{...}--> 标记块。
    返回解析后的 dict，如果解析失败返回空 dict。
    """
    # 匹配所有 <!--DATA:...--> 标记块
    pattern = r'<!--DATA:(.*?)-->'
    matches = _re_module.findall(pattern, reply_text, _re_module.DOTALL)

    if not matches:
        return {}

    result = {}
    for match in matches:
        try:
            parsed = json.loads(match.strip())
            if isinstance(parsed, dict):
                result.update(parsed)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"DATA 标记块解析失败: {e}, content={match[:200]}")
            continue

    return result


async def _extract_structured_updates(book_dir: Path, context: str, chat_data: dict, latest_reply: str) -> dict:
    """
    从对话中提取结构化数据更新。
    优先从 AI 回复中解析 <!--DATA:...--> 标记块，失败时回退到 LLM 提取。
    """
    fields, fields_desc = _extract_structured_updates_field_map(context)
    if not fields:
        return {}

    # === 优先：正则解析 AI 回复中的 DATA 标记块 ===
    parsed = _parse_structured_from_reply(latest_reply)
    if parsed:
        # 验证字段有效性
        valid_fields, _ = _extract_structured_updates_field_map(context)
        filtered = {}
        for k, v in parsed.items():
            if k in valid_fields:
                if isinstance(v, str) and len(v.strip()) > 5:
                    filtered[k] = v
                elif isinstance(v, (list, dict)) and v:
                    filtered[k] = v
        if filtered:
            logger.info(f"[DATA标记] 从回复中成功解析: context={context}, fields={list(filtered.keys())}")
            return filtered

    # === 回退：LLM 提取（原有逻辑） ===
    # 构建提取消息：系统指令 + 最近对话
    extract_system = (
        f"你是一个信息提取助手。根据以下关于小说{fields_desc}的对话，"
        f"提取应该更新到对应字段的完整内容。\n"
        f"只输出有实质性内容更新的字段，不要输出空字符串或占位符。\n"
        f"如果对话没有涉及任何具体设定内容（只是闲聊或提问），返回空对象 {{}}。\n"
        f"重要：每个字段的值应该是该字段截至目前讨论的完整内容，而不是增量。"
    )

    fields_json = json.dumps(fields, ensure_ascii=False)
    extract_user = (
        f"可更新字段：{fields_json}\n\n"
        f"最近对话内容：\n"
    )
    # 取最近6条消息
    recent = chat_data.get("messages", [])[-6:]
    for msg in recent:
        role_label = "作者" if msg["role"] == "user" else "AI助手"
        content = msg["content"][:800]  # 截断避免太长
        extract_user += f"[{role_label}]: {content}\n\n"
    extract_user += "\n请输出 JSON 对象，key 是字段名，value 是该字段的完整内容。"

    extract_messages = [
        {"role": "system", "content": extract_system},
        {"role": "user", "content": extract_user},
    ]

    try:
        model_router = get_model_router()
        result = await model_router.call_with_fallback_json(
            messages=extract_messages,
            task_type="reasoning",
            temperature=0.3,
            max_tokens=2000,
        )
        if isinstance(result, dict):
            # 过滤掉空值（允许字符串和非字符串类型如 list/dict）
            filtered = {}
            for k, v in result.items():
                if isinstance(v, str):
                    if len(v.strip()) > 10:
                        filtered[k] = v
                elif isinstance(v, (list, dict)):
                    if v:  # non-empty list/dict
                        filtered[k] = v
            return filtered
    except Exception as e:
        logger.warning(f"结构化提取失败: {e}", exc_info=True)

    return {}


async def _match_character_by_ai(existing_chars: list[dict], new_char_info: dict) -> int:
    """
    让 AI 判断新提取的角色信息是否对应某个已有角色。
    返回匹配的已有角色索引，-1 表示应创建新角色。
    判断依据：描述、身份、关系等特征，不仅仅是名字。
    """
    if not existing_chars:
        return -1

    # 构建已有角色摘要列表
    char_descriptions = []
    for idx, c in enumerate(existing_chars[:20]):
        parts = []
        name = c.get("name", "未知")
        role = c.get("role", "")
        personality = c.get("personality", "")
        background = c.get("background", "")
        motivation = c.get("motivation", "")
        desc = f"[{idx}] 名字={name}"
        if role:
            desc += f", 身份={role}"
        if personality:
            desc += f", 性格={personality[:80]}"
        if background:
            desc += f", 背景={background[:80]}"
        if motivation:
            desc += f", 动机={motivation[:80]}"
        char_descriptions.append(desc)

    # 构建新角色信息摘要
    new_parts = []
    for k, v in new_char_info.items():
        if v and isinstance(v, str) and len(v.strip()) > 0:
            new_parts.append(f"{k}={v[:100]}")
    new_desc = ", ".join(new_parts)

    prompt = (
        "你是一个角色匹配助手。请判断新提取的角色信息是否对应已有角色列表中的某个角色。\n"
        "判断时综合考虑：名字相似度、身份定位、性格特征、背景故事、行为动机等。\n"
        "注意：角色可能没有名字，或名字有变化，但其他特征相似则应视为同一角色。\n\n"
        f"已有角色列表：\n" + "\n".join(char_descriptions) + "\n\n"
        f"新提取的角色信息：{new_desc}\n\n"
        "请只输出一个数字：匹配的已有角色编号，或 -1 表示应创建新角色。\n"
        "只输出数字，不要输出其他内容。"
    )

    try:
        model_router = get_model_router()
        result = await asyncio.wait_for(
            model_router.call_with_fallback(
                messages=[{"role": "user", "content": prompt}],
                task_type="reasoning",
                temperature=0.0,
                max_tokens=20,
            ),
            timeout=15,
        )
        response_text = result[0].strip()
        # 解析返回的数字
        match_idx = int(response_text)
        if -1 <= match_idx < len(existing_chars):
            logger.info(f"AI 角色匹配结果: new_char='{new_char_info.get('name', '?')}' → idx={match_idx}")
            return match_idx
        return -1
    except asyncio.TimeoutError:
        logger.warning("AI 角色匹配超时，默认创建新角色")
        return -1
    except Exception as e:
        logger.warning(f"AI 角色匹配失败: {e}，回退到名称匹配")
        return -2  # -2 表示 AI 匹配失败，回退到名称匹配


def _apply_updates_to_data_files_sync(book_dir: Path, context: str, updates: dict, matched_char_idx: int = -1, char_match_map: dict = None):
    """
    将提取到的结构化更新写入对应的数据文件（同步版本，角色匹配由调用方预处理）
    matched_char_idx: AI 匹配结果，>=0 表示更新该索引的角色，-1 表示新建，-2 表示用名称匹配
    char_match_map: 批量角色 AI 匹配结果 {新角色索引int -> 已有角色索引int}
    """
    if not updates:
        return

    if context == "worldbuilding":
        world_path = book_dir / "world" / "world_data.json"
        if world_path.parent.exists():
            existing = read_json(str(world_path)) or {}
            for key, value in updates.items():
                if key in ("geography", "factions", "power_system", "history", "social_rules"):
                    existing[key] = value
            write_json(str(world_path), existing)
            logger.info(f"世界观数据已更新: {list(updates.keys())}")

    elif context == "character":
        char_path = book_dir / "characters" / "characters.json"
        if char_path.parent.exists():
            existing = read_json(str(char_path)) or {"characters": []}
            chars = existing.get("characters", [])

            # === 批量角色处理：characters 数组（来自 DATA 标记块） ===
            if "characters" in updates and isinstance(updates["characters"], list):
                for i, char_info in enumerate(updates["characters"]):
                    if not isinstance(char_info, dict):
                        continue
                    name = char_info.get("name", "").strip()
                    if not name and not any(char_info.get(f) for f in ["role", "personality", "background"]):
                        continue  # 跳过无实质内容的条目

                    # 使用调用方预计算的 AI 匹配结果
                    if char_match_map and i in char_match_map:
                        matched_idx = char_match_map[i]
                    else:
                        # 名称匹配 fallback
                        matched_idx = -1
                        if name and chars:
                            for idx, c in enumerate(chars):
                                if c.get("name") == name:
                                    matched_idx = idx
                                    break

                    if matched_idx >= 0 and matched_idx < len(chars):
                        # 更新已有角色
                        target = chars[matched_idx]
                        for k, v in char_info.items():
                            if v and isinstance(v, str) and len(v.strip()) > 0:
                                target[k] = v
                        logger.info(f"角色批量更新: idx={matched_idx}, name={target.get('name')}")
                    else:
                        # 创建新角色
                        _book_id = book_dir.name if hasattr(book_dir, 'name') else str(book_dir).rsplit('/', 1)[-1]
                        new_char = {
                            "id": f"char-{int(time.time())}-{len(chars)}",
                            "book_id": _book_id,
                            "name": char_info.get("name", "未命名"),
                            "role": char_info.get("role", "待定"),
                            "tag": "",
                            "avatar_color": "#666666",
                            "portrait": "",
                            "personality": char_info.get("personality", ""),
                            "background": char_info.get("background", ""),
                            "motivation": char_info.get("motivation", ""),
                            "abilities": char_info.get("abilities", ""),
                            "catchphrase": "",
                            "growth_arc": [],
                            "relationships": [],
                            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        }
                        chars.append(new_char)
                        logger.info(f"角色批量创建: name={new_char['name']}")

                existing["characters"] = chars
                # 生成 chat_derived_summary
                char_summary_parts = []
                for c in chars:
                    parts = [c.get("name", "未知")]
                    if c.get("role"): parts.append(f"身份:{c['role']}")
                    if c.get("personality"): parts.append(f"性格:{c['personality']}")
                    if c.get("background"): parts.append(f"背景:{c['background'][:50]}")
                    char_summary_parts.append(" | ".join(parts))
                existing["chat_derived_summary"] = "\n".join(char_summary_parts)
                write_json(str(char_path), existing)
                logger.info(f"角色批量数据已更新: {len(chars)} 个角色")
                return

            # === 原有单角色逻辑（兼容 LLM 回退提取的 name 字段） ===
            # 对于角色，把提取内容存为 chat_derived 字段
            char_summary_parts = []
            for key, value in updates.items():
                char_summary_parts.append(f"{key}: {value}")
            existing["chat_derived_summary"] = "\n".join(char_summary_parts)
            # 如果提取到了 name，尝试创建/更新角色
            if "name" in updates:
                found = False

                # 使用 AI 预匹配结果
                if matched_char_idx >= 0 and matched_char_idx < len(chars):
                    # AI 判断是同一角色，直接更新
                    target = chars[matched_char_idx]
                    for k, v in updates.items():
                        if k in target and v and isinstance(v, str) and len(v.strip()) > 0:
                            target[k] = v
                    found = True
                    logger.info(f"角色通过 AI 匹配更新: idx={matched_char_idx}, name='{target.get('name', '?')}'")
                elif matched_char_idx == -2:
                    # AI 匹配失败，回退到名称匹配
                    for c in chars:
                        if c.get("name") == updates["name"]:
                            for k, v in updates.items():
                                if k != "name" and k in c:
                                    c[k] = v
                            found = True
                            break

                if not found:
                    # Extract book_id from book_dir path
                    _book_id = book_dir.name if hasattr(book_dir, 'name') else str(book_dir).rsplit('/', 1)[-1]
                    new_char = {
                        "id": f"char-{int(time.time())}",
                        "book_id": _book_id,
                        "name": updates.get("name", "未命名"),
                        "role": updates.get("role", "待定"),
                        "tag": "",
                        "avatar_color": "#666666",
                        "portrait": "",
                        "personality": updates.get("personality", ""),
                        "background": updates.get("background", ""),
                        "motivation": updates.get("motivation", ""),
                        "abilities": updates.get("abilities", ""),
                        "catchphrase": "",
                        "growth_arc": [],
                        "relationships": [],
                        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    }
                    chars.append(new_char)
                existing["characters"] = chars
            write_json(str(char_path), existing)
            logger.info(f"角色数据已更新: {list(updates.keys())}")

    elif context == "outline":
        outline_path = book_dir / "outline" / "outline.json"
        if outline_path.parent.exists():
            existing = read_json(str(outline_path)) or {}
            for key, value in updates.items():
                # 特殊处理 volumes：确保写入的是结构化数组
                if key == "volumes":
                    if isinstance(value, str):
                        try:
                            parsed = json.loads(value)
                            if isinstance(parsed, list):
                                value = parsed
                        except (json.JSONDecodeError, TypeError):
                            # 如果无法解析为 JSON，跳过 volumes 字段
                            logger.warning(f"volumes 字段无法解析为 JSON，跳过")
                            continue
                    if isinstance(value, list):
                        existing["volumes"] = value
                else:
                    existing[key] = value
            write_json(str(outline_path), existing)
            logger.info(f"大纲数据已更新: {list(updates.keys())}")
            # 自动生成分章
            generate_chapters_from_outline(book_dir, existing)

    elif context == "writing":
        chapter_summary = updates.get("chapter_summary", "")
        chapter_title = updates.get("chapter_title", "")
        if chapter_summary:
            # 获取当前章节号
            chat_data = _load_chat_data(book_dir, "writing")
            current_ch = chat_data.get("stage_data", {}).get("current_chapter", 1)
            save_chapter_summary(book_dir, current_ch, chapter_title, chapter_summary)


# ──────────────────────────────────────────────────────────────────────────────
# 内部工具函数 — @mention 解析
# ──────────────────────────────────────────────────────────────────────────────

import re as _re

def _resolve_mentions(book_dir: Path, user_message: str) -> str:
    """
    解析 user_message 中的 @角色名 / @势力名，返回注入到 LLM 的上下文文本。
    如果没有 @mention，返回空字符串。
    """
    # 提取所有 @xxx（支持中英文名称）
    mentions = _re.findall(r'@([\w\u4e00-\u9fff\u3400-\u4dbf]+)', user_message)
    if not mentions:
        return ""

    parts = []

    # 查找角色
    char_path = book_dir / "characters" / "characters.json"
    char_map = {}
    if char_path.exists():
        char_data = read_json(str(char_path))
        for c in char_data.get("characters", []):
            char_map[c.get("name", "")] = c

    # 查找世界观势力
    world_path = book_dir / "world" / "world_data.json"
    faction_map = {}
    if world_path.exists():
        world_data = read_json(str(world_path))
        for f in world_data.get("factions", []):
            if isinstance(f, dict):
                faction_map[f.get("name", "")] = f
            elif isinstance(f, str):
                faction_map[f] = {"name": f}
        # Also check factions_graph
        for f in world_data.get("factions_graph", []):
            if isinstance(f, dict):
                faction_map[f.get("name", "")] = f

    for name in mentions:
        if name in char_map:
            c = char_map[name]
            detail_parts = []
            if c.get("role"):
                detail_parts.append(f"身份={c['role']}")
            if c.get("personality"):
                detail_parts.append(f"性格={c['personality']}")
            if c.get("background"):
                detail_parts.append(f"背景={c['background'][:200]}")
            if c.get("motivation"):
                detail_parts.append(f"动机={c['motivation']}")
            if c.get("abilities"):
                detail_parts.append(f"能力={c['abilities']}")
            if c.get("portrait"):
                detail_parts.append(f"外貌={c['portrait'][:200]}")
            if detail_parts:
                parts.append(f"[@{name}] 角色数据：{', '.join(detail_parts)}")
        elif name in faction_map:
            f = faction_map[name]
            detail_parts = []
            if f.get("description"):
                detail_parts.append(f"描述={f['description'][:200]}")
            if f.get("power"):
                detail_parts.append(f"实力={f['power']}")
            if f.get("headquarters"):
                detail_parts.append(f"据点={f['headquarters']}")
            if detail_parts:
                parts.append(f"[@{name}] 势力数据：{', '.join(detail_parts)}")

    if parts:
        return "--- @引用实体 ---\n" + "\n".join(parts) + "\n--- 引用结束 ---"
    return ""


# ──────────────────────────────────────────────────────────────────────────────
# 跨模块同步通知
# ──────────────────────────────────────────────────────────────────────────────

_CONTEXT_LABELS = {
    "worldbuilding": "世界观",
    "character": "角色",
    "outline": "大纲",
    "writing": "写作",
}


def _generate_sync_summary(context: str, stage_data: dict) -> str:
    """生成模块确认后的变更摘要，供其他模块感知"""
    parts = []

    if context == "character":
        char_data = stage_data.get("character_data", {})
        name = char_data.get("name") or stage_data.get("data_updates", {}).get("name", "")
        role = char_data.get("role", "")
        background = char_data.get("background", "")
        personality = char_data.get("personality", "")
        motivation = char_data.get("motivation", "")
        abilities = char_data.get("abilities", "")

        # 如果 stage_data 里没有详细信息，从 characters.json 读取最新数据
        if name:
            entry = f"角色「{name}」"
            if role:
                entry += f"（{role}）"
            details = []
            if background:
                details.append(f"身世背景：{background[:150]}")
            if personality:
                details.append(f"性格：{personality[:80]}")
            if motivation:
                details.append(f"核心动机：{motivation[:80]}")
            if abilities:
                details.append(f"能力：{abilities[:80]}")
            if details:
                entry += "：" + "；".join(details)
            parts.append(entry)

    elif context == "worldbuilding":
        world_text = stage_data.get("world_text", "")
        if world_text:
            # 截取前 200 字作为摘要
            summary = world_text[:200]
            if len(world_text) > 200:
                summary += "..."
            parts.append(f"世界观设定已更新：{summary}")

    elif context == "outline":
        outline_text = stage_data.get("outline_text", "")
        if outline_text:
            summary = outline_text[:200]
            if len(outline_text) > 200:
                summary += "..."
            parts.append(f"大纲已更新：{summary}")

    return "\n".join(parts) if parts else ""


def _record_sync_notification(book_dir: Path, source_context: str, summary: str):
    """记录跨模块同步通知到 sync_log.json"""
    sync_log_path = book_dir / "sync_log.json"
    sync_log = read_json(str(sync_log_path)) if sync_log_path.exists() else {"notifications": []}

    notification = {
        "source": source_context,
        "source_label": _CONTEXT_LABELS.get(source_context, source_context),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "summary": summary,
        "read_by": [],
    }
    sync_log["notifications"].append(notification)

    # 只保留最近 20 条通知
    if len(sync_log["notifications"]) > 20:
        sync_log["notifications"] = sync_log["notifications"][-20:]

    write_json(str(sync_log_path), sync_log)
    logger.info(f"跨模块同步通知已记录: {source_context} -> {summary[:50]}...")


@router.get("/{book_id}/chat/sync-notifications")
async def get_sync_notifications(book_id: str, for_context: str = ""):
    """
    获取当前模块未读的跨模块同步通知
    GET /books/{book_id}/chat/sync-notifications?for_context=worldbuilding
    响应: { "notifications": [...] }
    """
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    sync_log_path = book_dir / "sync_log.json"
    if not sync_log_path.exists():
        return {"notifications": []}

    sync_log = read_json(str(sync_log_path))
    notifications = sync_log.get("notifications", [])

    # 过滤：不属于当前模块 + 当前模块还没读过
    unread = [
        n for n in notifications
        if n.get("source") != for_context
        and for_context not in n.get("read_by", [])
    ]

    # 标记为已读
    if unread and for_context:
        for n in unread:
            if "read_by" not in n:
                n["read_by"] = []
            if for_context not in n["read_by"]:
                n["read_by"].append(for_context)
        write_json(str(sync_log_path), sync_log)

    return {"notifications": unread}


# ──────────────────────────────────────────────────────────────────────────────
# API 端点
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{book_id}/chat")
async def send_chat_message(book_id: str, request: ChatMessageRequest):
    """
    发送对话消息（通用）
    POST /books/{book_id}/chat
    请求: { "message": "...", "context": "worldbuilding|character|outline|writing" }
    响应: { "reply": "...", "context": "...", "stage_data": {...}, "suggestions": [...] }
    """
    # 校验 context
    context = request.context
    if context not in VALID_CONTEXTS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 context: {context}，可选值: {', '.join(VALID_CONTEXTS)}",
        )

    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    # 加载对话数据
    chat_data = _load_chat_data(book_dir, context)
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    # 保存用户消息
    user_msg_record = {
        "role": "user",
        "content": user_message,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "context": context,
    }
    chat_data["messages"].append(user_msg_record)

    # writing 场景：用前端章节下拉传入的 chapter_number 同步 stage_data.current_chapter
    # 必须在构建 prompt 之前完成，保证 WritingContext 按用户选中的章节注入（R1 修复）
    if context == "writing" and request.chapter_number is not None and request.chapter_number > 0:
        stage_data = chat_data.get("stage_data", {})
        if stage_data.get("current_chapter") != request.chapter_number:
            logger.info(f"[writing] 章节切换: {stage_data.get('current_chapter')} → {request.chapter_number}")
        stage_data["current_chapter"] = request.chapter_number
        chat_data["stage_data"] = stage_data

    _save_chat_data(book_dir, context, chat_data)

    # === @mention 解析：检测 user_message 中的 @xxx 并注入实体上下文 ===
    mention_context = _resolve_mentions(book_dir, user_message)

    # 构建 LLM 消息并调用
    llm_messages = _build_llm_messages(book_dir, context, chat_data, user_message)

    # 如果有 @mention 上下文，插入到 user 消息前面
    if mention_context:
        llm_messages.append({"role": "system", "content": mention_context})

    task_type = CONTEXT_TASK_TYPE.get(context, "reasoning")

    # outline/writing 场景给予更长超时（240s），其他场景 180s
    llm_timeout = 240 if context in ("outline", "writing") else 180

    try:
        model_router = get_model_router()
        response_text, model_used = await asyncio.wait_for(
            model_router.call_with_fallback(
                messages=llm_messages,
                task_type=task_type,
                temperature=0.7,
                max_tokens=4000,
            ),
            timeout=llm_timeout,
        )
    except asyncio.TimeoutError:
        logger.error(f"LLM 调用超时 (context={context}, timeout={llm_timeout}s)")
        raise HTTPException(
            status_code=504,
            detail=f"AI 响应超时（已等待 {llm_timeout} 秒），请简化请求或稍后重试。",
        )
    except LLMError as e:
        logger.error(f"LLM 调用失败 (context={context}): {e}")
        raise HTTPException(status_code=502, detail=f"AI 服务暂时不可用: {str(e)[:200]}")

    # 保存 AI 回复
    assistant_msg_record = {
        "role": "assistant",
        "content": response_text,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "context": context,
    }
    chat_data["messages"].append(assistant_msg_record)
    _save_chat_data(book_dir, context, chat_data)

    # === 从对话中提取结构化数据更新（所有 context 都执行） ===
    # 用 try/except 包裹，避免提取失败导致整个对话请求崩溃
    data_updates = {}
    if request.suppress_auto_sync:
        # 分析同步审核进行中：保留对话记录，但跳过自动提取与写入，避免在用户审核期间抢先改动设定
        logger.info(f"[auto-sync] suppressed for context={context} (分析同步审核中)")
    else:
        try:
            data_updates = await asyncio.wait_for(
                _extract_structured_updates(book_dir, context, chat_data, response_text),
                timeout=30,
            )
        except asyncio.TimeoutError:
            logger.warning(f"结构化数据提取超时 (context={context})，跳过本次提取")
        except Exception as e:
            logger.warning(f"结构化数据提取失败（不影响对话回复）: {e}", exc_info=True)
    if data_updates:
        if context in ("worldbuilding", "character", "outline"):
            # 角色场景：先让 AI 判断新角色是否对应已有角色
            matched_char_idx = -1
            char_match_map = None
            if context == "character":
                if "characters" in data_updates and isinstance(data_updates["characters"], list):
                    # 批量角色：预先 AI 匹配
                    char_path = book_dir / "characters" / "characters.json"
                    if char_path.parent.exists():
                        existing_chars_data = read_json(str(char_path)) or {"characters": []}
                        existing_chars = existing_chars_data.get("characters", [])
                        if existing_chars:
                            # 为每个新角色做 AI 匹配
                            char_match_map = {}  # index -> matched_existing_idx
                            for ci, char_info in enumerate(data_updates["characters"]):
                                if isinstance(char_info, dict):
                                    matched = await _match_character_by_ai(existing_chars, char_info)
                                    if matched >= 0:
                                        char_match_map[ci] = matched
                            _apply_updates_to_data_files_sync(book_dir, context, data_updates, matched_char_idx=-1, char_match_map=char_match_map)
                        else:
                            _apply_updates_to_data_files_sync(book_dir, context, data_updates)
                    else:
                        _apply_updates_to_data_files_sync(book_dir, context, data_updates)
                elif "name" in data_updates:
                    # 单角色模式（LLM 回退）：先让 AI 判断是否对应已有角色
                    char_path = book_dir / "characters" / "characters.json"
                    if char_path.parent.exists():
                        existing_chars_data = read_json(str(char_path)) or {"characters": []}
                        existing_chars = existing_chars_data.get("characters", [])
                        if existing_chars:
                            matched_char_idx = await _match_character_by_ai(existing_chars, data_updates)
                    _apply_updates_to_data_files_sync(book_dir, context, data_updates, matched_char_idx)
                else:
                    _apply_updates_to_data_files_sync(book_dir, context, data_updates, matched_char_idx)
            else:
                # 非角色场景：直接应用更新
                _apply_updates_to_data_files_sync(book_dir, context, data_updates, matched_char_idx)
            # 如果是 outline context，自动从大纲生成分章
            if context == "outline":
                outline_data = read_json(str(book_dir / "outline" / "outline.json")) or {}
                generate_chapters_from_outline(book_dir, outline_data)
        
        # === writing context：保存摘要和正文到章节文件 ===
        if context == "writing":
            stage_data = chat_data.get("stage_data", {})
            current_ch = stage_data.get("current_chapter", 1)
            chapter_summary = data_updates.get("chapter_summary", "")
            chapter_title = data_updates.get("chapter_title", "")
            
            if chapter_summary:
                save_chapter_summary(book_dir, current_ch, chapter_title, chapter_summary)
                stage_data["chapter_summary"] = chapter_summary
                chat_data["stage_data"] = stage_data
                _save_chat_data(book_dir, context, chat_data)
        
        # 更新 stage_data 以便前端知道有新数据
        stage_data = chat_data.get("stage_data", {})
        stage_data["data_updates"] = data_updates
        chat_data["stage_data"] = stage_data
        _save_chat_data(book_dir, context, chat_data)

    # 生成建议
    suggestions = _generate_suggestions(context, chat_data)

    # === writing context：保存正文到章节文件 ===
    if context == "writing" and data_updates.get("chapter_content"):
        current_ch = chat_data.get("stage_data", {}).get("current_chapter", 1)
        chapter_title = data_updates.get("chapter_title", f"第{current_ch}章")
        ch_content_text = data_updates["chapter_content"]
        
        # 确保 chapters/final 目录存在
        final_dir = book_dir / "chapters" / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入章节文件
        ch_filename = f"chapter-{current_ch:03d}.md"
        ch_path = final_dir / ch_filename
        ch_file_content = f"# {chapter_title}\n\n{ch_content_text}"
        from app.tools.file_ops import write_file
        write_file(str(ch_path), ch_file_content)
        logger.info(f"章节 {current_ch} 正文已保存到 {ch_path}")
        
        # 更新 chapters.json 中的状态和字数
        chapters_json_path = book_dir / "chapters" / "chapters.json"
        if chapters_json_path.exists():
            chapters_data = read_json(str(chapters_json_path))
            for ch in chapters_data.get("chapters", []):
                if ch.get("chapter_number") == current_ch:
                    ch["status"] = "draft"
                    ch["word_count"] = len(ch_content_text)
                    ch["title"] = chapter_title
                    break
            write_json(str(chapters_json_path), chapters_data)

    return {
        "reply": response_text,
        "context": context,
        "stage_data": chat_data.get("stage_data", {}),
        "data_updates": data_updates,
        "suggestions": suggestions,
        "model_used": model_used,
    }


@router.get("/{book_id}/chat/history")
async def get_chat_history(book_id: str, context: str = "outline"):
    """
    获取对话历史
    GET /books/{book_id}/chat/history?context=outline
    响应: { "messages": [...], "context": "...", "confirmed": false, "stage_data": {...} }
    """
    if context not in VALID_CONTEXTS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 context: {context}，可选值: {', '.join(VALID_CONTEXTS)}",
        )

    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    chat_data = _load_chat_data(book_dir, context)

    return {
        "messages": chat_data.get("messages", []),
        "context": context,
        "confirmed": chat_data.get("confirmed", False),
        "stage_data": chat_data.get("stage_data", {}),
        "checkpoint": chat_data.get("checkpoint"),
    }


@router.get("/{book_id}/chat/all-contexts")
async def get_all_contexts_status(book_id: str):
    """
    获取所有 context 的对话状态概览
    GET /books/{book_id}/chat/all-contexts
    响应: { "contexts": { "worldbuilding": {...}, "character": {...}, ... } }
    """
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    result = {}
    for ctx in VALID_CONTEXTS:
        chat_data = _load_chat_data(book_dir, ctx)
        result[ctx] = {
            "message_count": len(chat_data.get("messages", [])),
            "confirmed": chat_data.get("confirmed", False),
            "stage_data": chat_data.get("stage_data", {}),
        }

    return {"contexts": result}


@router.post("/{book_id}/chat/confirm-stage")
async def confirm_context(book_id: str, request: ConfirmContextRequest):
    """
    确认当前 context 的对话成果
    POST /books/{book_id}/chat/confirm-stage
    请求: { "context": "worldbuilding|character|outline|writing" }
    响应: { "success": true, "context": "...", "stage_data": {...}, "message": "..." }
    """
    context = request.context
    if context not in VALID_CONTEXTS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 context: {context}，可选值: {', '.join(VALID_CONTEXTS)}",
        )

    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    chat_data = _load_chat_data(book_dir, context)

    if chat_data.get("confirmed"):
        # 允许重新确认：清除旧断点，重新提取成果
        logger.info(f"context '{context}' 重新确认（已有旧确认）")

    # 从对话历史中提取成果，固化到 stage_data
    confirmed_text = _finalize_context(book_id, book_dir, context, chat_data)

    # 标记为已确认
    chat_data["confirmed"] = True

    # 如果有确认文本，更新 stage_data
    if confirmed_text:
        stage_data = chat_data.get("stage_data", {})
        if context in ("worldbuilding", "outline"):
            text_key = "world_text" if context == "worldbuilding" else "outline_text"
            stage_data[text_key] = confirmed_text
        elif context == "character":
            stage_data["confirmed_text"] = confirmed_text
        elif context == "writing":
            stage_data["chapter_summary"] = confirmed_text
        chat_data["stage_data"] = stage_data

    # 同时把确认成果写入对应的结构化数据文件，方便跨 context 读取
    _sync_confirmed_to_data_files(book_dir, context, chat_data.get("stage_data", {}))

    # ── 跨模块同步通知：记录变更摘要，供其他模块感知 ──
    sync_summary = _generate_sync_summary(context, chat_data.get("stage_data", {}))
    if sync_summary:
        _record_sync_notification(book_dir, context, sync_summary)

    # ── 创建断点：压缩当前对话历史，后续对话只需注入摘要 ──
    try:
        checkpoint = await _create_checkpoint(book_dir, context, chat_data)
        chat_data["checkpoint"] = checkpoint
    except Exception as e:
        logger.warning(f"创建断点失败（不影响确认流程）: {e}")

    # 追加系统消息
    confirm_msg = {
        "role": "assistant",
        "content": _confirm_message(context),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "context": context,
    }
    chat_data["messages"].append(confirm_msg)
    _save_chat_data(book_dir, context, chat_data)

    # 建议下一步
    suggestions = _next_context_suggestions(context)

    return {
        "success": True,
        "context": context,
        "stage_data": chat_data.get("stage_data", {}),
        "message": confirm_msg["content"],
        "suggestions": suggestions,
        "checkpoint_created": chat_data.get("checkpoint") is not None,
    }


class CheckpointRequest(BaseModel):
    """手动创建断点请求"""
    context: str


@router.post("/{book_id}/chat/checkpoint")
async def create_checkpoint_endpoint(book_id: str, request: CheckpointRequest):
    """
    手动创建对话断点：压缩当前对话历史为摘要，
    后续对话将只注入摘要 + 断点后的新消息。
    POST /books/{book_id}/chat/checkpoint
    请求: { "context": "worldbuilding|character|outline|writing" }
    响应: { "success": true, "message": "...", "checkpoint": {...} }
    """
    context = request.context
    if context not in VALID_CONTEXTS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 context: {context}，可选值: {', '.join(VALID_CONTEXTS)}",
        )

    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    chat_data = _load_chat_data(book_dir, context)
    messages = chat_data.get("messages", [])

    if len(messages) < 2:
        raise HTTPException(status_code=400, detail="对话历史太短，无需创建断点")

    # 创建断点
    checkpoint = await _create_checkpoint(book_dir, context, chat_data)
    chat_data["checkpoint"] = checkpoint
    _save_chat_data(book_dir, context, chat_data)

    context_labels = {
        "worldbuilding": "世界观设定",
        "character": "角色设计",
        "outline": "大纲规划",
        "writing": "正文写作",
    }

    return {
        "success": True,
        "message": f"已为「{context_labels.get(context, context)}」创建对话断点，"
                   f"压缩了 {checkpoint['message_index']} 条历史消息。"
                   f"后续对话将基于摘要继续，不再重复发送旧消息。",
        "checkpoint": {
            "message_index": checkpoint["message_index"],
            "created_at": checkpoint["created_at"],
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# 内部工具函数 — 确认 & 同步
# ──────────────────────────────────────────────────────────────────────────────

def _finalize_context(book_id: str, book_dir: Path, context: str, chat_data: dict) -> str:
    """
    从对话历史中提取当前 context 的成果摘要。
    策略：取最后一条 assistant 消息作为成果文本。
    """
    messages = chat_data.get("messages", [])
    assistant_msgs = [m for m in messages if m["role"] == "assistant" and m.get("context") == context]

    if not assistant_msgs:
        return ""

    # 取最后一条 AI 回复作为成果摘要
    last_reply = assistant_msgs[-1]["content"]
    return last_reply


def _sync_confirmed_to_data_files(book_dir: Path, context: str, stage_data: dict):
    """
    将对话确认的成果同步到对应的结构化数据文件，
    这样其他模块（world API、outline API 等）和跨 context 注入都能读到。
    """
    if context == "worldbuilding":
        world_text = stage_data.get("world_text", "")
        if world_text:
            world_path = book_dir / "world" / "world_data.json"
            existing = read_json(str(world_path))
            existing["chat_derived_summary"] = world_text
            write_json(str(world_path), existing)

    elif context == "outline":
        outline_text = stage_data.get("outline_text", "")
        if outline_text:
            outline_path = book_dir / "outline" / "outline.json"
            existing = read_json(str(outline_path))
            existing["chat_derived_summary"] = outline_text
            # 如果没有 volumes，尝试把扁平字段组合成默认单卷结构
            if not existing.get("volumes"):
                main_plot = existing.get("main_plot", "")
                core_conflict = existing.get("core_conflict", "")
                chapter_structure = existing.get("chapter_structure", "")
                # 用 chat_derived_summary + main_plot 构造一个默认 volume
                summary_parts = []
                if core_conflict:
                    summary_parts.append(f"核心冲突：{core_conflict}")
                if main_plot:
                    summary_parts.append(f"主线剧情：{main_plot}")
                if chapter_structure:
                    summary_parts.append(f"章节结构：{chapter_structure}")
                story_arc = "\n".join(summary_parts) if summary_parts else outline_text
                existing["volumes"] = [{
                    "id": "vol-auto-derived",
                    "number": 1,
                    "title": "故事大纲",
                    "story_arc": story_arc,
                    "chapters": [],
                }]
            write_json(str(outline_path), existing)

    elif context == "character":
        # Mark all characters in characters.json as confirmed
        char_path = book_dir / "characters" / "characters.json"
        if char_path.exists():
            existing = read_json(str(char_path))
            if "characters" not in existing:
                existing["characters"] = []
            for c in existing["characters"]:
                c["confirmed"] = True
            # Also save chat_derived_summary if available
            char_data = stage_data.get("character_data", {})
            if char_data:
                existing["chat_derived_summary"] = json.dumps(char_data, ensure_ascii=False)
            write_json(str(char_path), existing)


def _confirm_message(context: str) -> str:
    """各 context 确认后的提示消息"""
    msgs = {
        "worldbuilding": (
            "世界观设定已确认！后续写作将严格遵循这套设定。"
            "你可以去「角色设计」或「大纲规划」继续推进了。"
        ),
        "character": (
            "角色设定已确认！角色的性格、背景和关系已经固定。"
            "你可以继续完善其他角色，或去「大纲规划」推进剧情。"
        ),
        "outline": (
            "大纲已确认！故事脉络已经清晰。"
            "现在可以进入「正文写作」开始创作了。"
        ),
        "writing": (
            "本章内容已确认！可以开始写下一章了。"
        ),
    }
    return msgs.get(context, "成果已确认！")


def _next_context_suggestions(context: str) -> list[str]:
    """确认当前 context 后，建议下一步可以做什么"""
    suggestions_map = {
        "worldbuilding": [
            "去设计角色",
            "去规划大纲",
            "继续完善世界观",
        ],
        "character": [
            "去规划大纲",
            "继续设计其他角色",
            "去讨论世界观",
        ],
        "outline": [
            "开始写正文",
            "回去调整大纲",
            "补充角色设定",
        ],
        "writing": [
            "开始写下一章",
            "修改当前内容",
            "调整大纲",
        ],
    }
    return suggestions_map.get(context, [])



# ──────────────────────────────────────────────────────────────────────────────
# 对话 → 结构化数据 同步分析
# ──────────────────────────────────────────────────────────────────────────────

# 各场景可同步的结构化字段
SYNC_FIELD_MAP = {
    "worldbuilding": {
        "fields": ["geography", "factions", "power_system", "history", "social_rules"],
        "labels": {
            "geography": "地理环境",
            "factions": "势力分布",
            "power_system": "力量体系",
            "history": "历史年表",
            "social_rules": "社会规则",
        },
    },
    "character": {
        "fields": ["characters"],
        "labels": {
            "characters": "角色列表",
        },
    },
    "outline": {
        "fields": ["volumes", "foreshadowing"],
        "labels": {
            "volumes": "卷章结构",
            "foreshadowing": "伏笔管理",
        },
    },
    "writing": {
        "fields": ["chapter_title", "chapter_content", "chapter_summary", "writing_notes"],
        "labels": {
            "chapter_title": "章节标题",
            "chapter_content": "章节正文",
            "chapter_summary": "章节摘要",
            "writing_notes": "写作笔记",
        },
    },
}


class AnalyzeSyncRequest(BaseModel):
    context: str


class AnalyzeSyncFieldResult(BaseModel):
    field: str
    label: str
    change_description: str
    proposed_value: str
    current_value: str


class AnalyzeSyncResponse(BaseModel):
    context: str
    fields: list[AnalyzeSyncFieldResult]
    analyzed_message_count: int


@router.post("/{book_id}/chat/analyze-sync")
async def analyze_sync(book_id: str, request: AnalyzeSyncRequest):
    """
    分析对话内容，提取可同步到结构化数据的变更建议（不自动应用）
    POST /books/{book_id}/chat/analyze-sync
    请求: { "context": "worldbuilding|character|outline|writing" }
    响应: { "context": "...", "fields": [{field, label, change_description, proposed_value, current_value}, ...] }
    """
    context = request.context
    if context not in VALID_CONTEXTS:
        raise HTTPException(status_code=400, detail=f"无效的 context: {context}")

    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    chat_data = _load_chat_data(book_dir, context)
    messages = chat_data.get("messages", [])
    if len(messages) < 2:
        return AnalyzeSyncResponse(context=context, fields=[], analyzed_message_count=0)

    field_info = SYNC_FIELD_MAP[context]
    fields_list = field_info["fields"]
    labels = field_info["labels"]

    # 取最近 16 条消息供 LLM 分析
    recent = messages[-16:]
    recent_text = ""
    for msg in recent:
        role_label = "作者" if msg["role"] == "user" else "AI助手"
        recent_text += f"[{role_label}]: {msg['content'][:800]}\n\n"

    # 加载当前数据文件
    current_data = _load_context_data_file(book_dir, context)

    # 构建当前状态描述
    current_state_parts = []
    for field in fields_list:
        current_val = current_data.get(field, "")
        if isinstance(current_val, list):
            current_val = str(current_val)
        if current_val and len(str(current_val).strip()) > 0:
            preview = str(current_val)[:200]
            if len(str(current_val)) > 200:
                preview += "..."
            current_state_parts.append(f"- {labels[field]}（当前有内容，{len(str(current_val))}字）: {preview}")
        else:
            current_state_parts.append(f"- {labels[field]}（当前为空）")
    current_state_text = "\n".join(current_state_parts)

    fields_json = json.dumps(fields_list, ensure_ascii=False)
    labels_json = json.dumps(labels, ensure_ascii=False)

    analyze_system = (
        "你是一个专业的信息分析助手。你的任务是从小说创作对话中提取结构化数据更新。\n\n"
        f"当前场景: {context}\n"
        f"需要同步的字段: {fields_json}\n"
        f"字段中文名称: {labels_json}\n\n"
        "分析规则:\n"
        "1. 仔细阅读对话内容，理解作者和AI讨论的设定细节\n"
        "2. 对于每个字段，判断对话中是否产生了该字段相关的新内容或修改\n"
        "3. 如果有新内容，输出完整的更新后文本（不是增量，是完整内容）\n"
        "4. 同时生成简洁的 change_description 说明做了哪些变更\n"
        "5. 如果某字段未被讨论或内容与当前一致，不要包含在输出中\n"
        "6. 内容应该是高质量的、结构化的设定文本，适合展示在面板中\n"
        "7. 使用 Markdown 格式组织内容，使其清晰可读\n"
        "8. 即使对话只涉及零散细节，也要整合成完整连贯的设定文本\n"
        "9. 对于 character 场景，proposed_value 必须是一个 JSON 数组字符串，"
        "每个元素是一个角色对象，包含 name/role/personality/background/motivation/abilities/catchphrase/portrait 字段\n"
        "10. 角色必须从对话中提取所有出现的角色，每个角色单独一个对象\n"
        "11. 对于 outline 场景的 volumes 字段，proposed_value 必须是一个 JSON 数组字符串，"
        "每个元素是一个卷对象：{id, number, title, story_arc, chapters: [{id, number, title, summary, characters: []}]}\n"
        "12. 对于 outline 场景的 foreshadowing 字段，proposed_value 必须是一个 JSON 数组字符串，"
        "每个元素是一个伏笔对象：{id, purpose, description, start_chapter, end_chapter, characters: [], status: planted/active/resolved}\n"
        "13. 章节的 characters 字段应列出该章节出场/涉及的角色名"
    )

    analyze_user = (
        f"当前各字段状态:\n{current_state_text}\n\n"
        f"最近对话内容:\n{recent_text}\n"
        f"请分析对话内容，输出需要更新的字段。\n"
        f"输出 JSON 格式: {{\"fields\": [{{\"field\": \"字段名\", \"change_description\": \"变更说明\", \"proposed_value\": \"完整新内容\"}}]}}"
    )

    analyze_messages = [
        {"role": "system", "content": analyze_system},
        {"role": "user", "content": analyze_user},
    ]

    try:
        model_router = get_model_router()
        result, _ = await model_router.call_with_fallback_json(
            messages=analyze_messages,
            task_type="reasoning",
            temperature=0.3,
            max_tokens=4000,
        )
    except Exception as e:
        logger.error(f"分析同步 LLM 调用失败: {e}")
        raise HTTPException(status_code=502, detail=f"AI 分析失败: {str(e)[:200]}")

    # 解析 LLM 返回
    raw_fields = result.get("fields", []) if isinstance(result, dict) else []

    # 构建响应，补齐 current_value
    response_fields = []
    seen_fields = set()
    for rf in raw_fields:
        field_name = rf.get("field", "")
        if field_name not in fields_list or field_name in seen_fields:
            continue
        seen_fields.add(field_name)

        proposed = rf.get("proposed_value", "")
        if not proposed or len(str(proposed).strip()) < 5:
            continue

        current_val = current_data.get(field_name, "")
        if isinstance(current_val, list):
            current_val = "\n".join(
                f"- {f.get('name', str(f))}" if isinstance(f, dict) else str(f)
                for f in current_val
            )

        response_fields.append(AnalyzeSyncFieldResult(
            field=field_name,
            label=labels.get(field_name, field_name),
            change_description=rf.get("change_description", ""),
            proposed_value=str(proposed),
            current_value=str(current_val) if current_val else "",
        ))

    return AnalyzeSyncResponse(
        context=context,
        fields=response_fields,
        analyzed_message_count=len(recent),
    )


def _load_context_data_file(book_dir: Path, context: str) -> dict:
    """根据 context 加载对应的数据文件"""
    if context == "worldbuilding":
        return read_json(str(book_dir / "world" / "world_data.json")) or {}
    elif context == "character":
        raw = read_json(str(book_dir / "characters" / "characters.json")) or {}
        # 转为 {characters: "现有角色列表文本"} 格式，便于 LLM 理解当前状态
        chars = raw.get("characters", [])
        if chars:
            chars_text = "\n".join(
                f"- {c.get('name', '未知')}: {c.get('role', '')} | {c.get('personality', '')[:50]}"
                for c in chars
            )
        else:
            chars_text = "(尚无角色)"
        return {"characters": chars_text}
    elif context == "outline":
        return read_json(str(book_dir / "outline" / "outline.json")) or {}
    elif context == "writing":
        return {}
    return {}


class ApplySyncRequest(BaseModel):
    context: str
    selected_fields: dict  # {field_name: new_value}


@router.post("/{book_id}/chat/apply-sync")
async def apply_sync(book_id: str, request: ApplySyncRequest):
    """
    将用户确认的结构化变更写入数据文件
    POST /books/{book_id}/chat/apply-sync
    请求: { "context": "...", "selected_fields": {"geography": "...", "power_system": "..."} }
    """
    context = request.context
    selected = request.selected_fields
    if context not in VALID_CONTEXTS:
        raise HTTPException(status_code=400, detail=f"无效的 context: {context}")
    if not selected:
        raise HTTPException(status_code=400, detail="没有选择要同步的字段")

    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    allowed_fields = set(SYNC_FIELD_MAP.get(context, {}).get("fields", []))
    # 过滤：只写入当前 context 允许的字段
    filtered = {k: v for k, v in selected.items() if k in allowed_fields}
    if not filtered:
        raise HTTPException(status_code=400, detail="所选字段与当前场景不匹配")

    applied_fields = []

    if context == "worldbuilding":
        world_path = book_dir / "world" / "world_data.json"
        existing = read_json(str(world_path)) or {}
        for key, value in filtered.items():
            existing[key] = value
        write_json(str(world_path), existing)
        applied_fields = list(filtered.keys())

    elif context == "character":
        char_path = book_dir / "characters" / "characters.json"
        existing = read_json(str(char_path)) or {"characters": []}
        chars = existing.get("characters", [])

        # filtered 里是 {"characters": "[json string of character array]"}
        raw_chars_str = filtered.get("characters", "[]")
        try:
            raw_chars = json.loads(raw_chars_str) if isinstance(raw_chars_str, str) else raw_chars_str
        except json.JSONDecodeError:
            raw_chars = []

        if not isinstance(raw_chars, list):
            raw_chars = []

        # Merge mode: 智能匹配合并
        now_str = time.strftime("%Y-%m-%dT%H:%M:%S")

        def _personality_similarity(p1: str, p2: str) -> float:
            """计算两个性格描述的关键词重合率"""
            if not p1 or not p2:
                return 0.0
            # 分词：按逗号、顿号、空格、换行分割
            import re
            tokens1 = set(re.split(r'[,，、\s\n]+', p1.lower())) - {''}
            tokens2 = set(re.split(r'[,，、\s\n]+', p2.lower())) - {''}
            if not tokens1 or not tokens2:
                return 0.0
            overlap = tokens1 & tokens2
            return len(overlap) / min(len(tokens1), len(tokens2))

        for rc in raw_chars:
            if not isinstance(rc, dict):
                continue
            name = rc.get("name", "").strip()
            if not name:
                continue

            # 策略1: 精确名称匹配
            found = None
            for c in chars:
                if c.get("name", "").strip() == name:
                    found = c
                    break

            # 策略2: role 相同 + personality 相似度 >= 50%
            if not found:
                rc_role = rc.get("role", "").strip()
                rc_personality = rc.get("personality", "").strip()
                for c in chars:
                    c_role = c.get("role", "").strip()
                    c_personality = c.get("personality", "").strip()
                    if rc_role and c_role and rc_role == c_role:
                        sim = _personality_similarity(rc_personality, c_personality)
                        if sim >= 0.5:
                            found = c
                            break

            if found:
                for k, v in rc.items():
                    if k in found and k not in ("id", "book_id", "created_at"):
                        found[k] = v
                found["updated_at"] = now_str
            else:
                chars.append({
                    "id": f"char-{int(time.time())}-{name}",
                    "book_id": book_id,
                    "name": name,
                    "role": rc.get("role", "待定"),
                    "tag": rc.get("tag", ""),
                    "avatar_color": rc.get("avatar_color", "#666666"),
                    "portrait": rc.get("portrait", ""),
                    "personality": rc.get("personality", ""),
                    "background": rc.get("background", ""),
                    "motivation": rc.get("motivation", ""),
                    "abilities": rc.get("abilities", ""),
                    "catchphrase": rc.get("catchphrase", ""),
                    "growth_arc": rc.get("growth_arc", []),
                    "relationships": rc.get("relationships", []),
                    "created_at": now_str,
                    "updated_at": now_str,
                })

        existing["characters"] = chars
        write_json(str(char_path), existing)
        applied_fields = list(filtered.keys())

    elif context == "outline":
        outline_path = book_dir / "outline" / "outline.json"
        existing = read_json(str(outline_path)) or {}

        # 处理 volumes（卷章结构）
        if "volumes" in filtered:
            raw = filtered["volumes"]
            try:
                volumes = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError:
                volumes = []
            if isinstance(volumes, list):
                existing["volumes"] = volumes
                applied_fields.append("volumes")

        # 处理 foreshadowing（伏笔列表）
        if "foreshadowing" in filtered:
            raw = filtered["foreshadowing"]
            try:
                foreshadows = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError:
                foreshadows = []
            if isinstance(foreshadows, list):
                # 合并：按 purpose + start_chapter 匹配更新，否则新增
                existing_fs = existing.get("foreshadowing", [])
                for fs in foreshadows:
                    if not isinstance(fs, dict):
                        continue
                    purpose = fs.get("purpose", "")
                    start = fs.get("start_chapter", 0)
                    found = None
                    for ef in existing_fs:
                        if ef.get("purpose") == purpose and ef.get("start_chapter") == start:
                            found = ef
                            break
                    if found:
                        for k, v in fs.items():
                            found[k] = v
                    else:
                        existing_fs.append(fs)
                existing["foreshadowing"] = existing_fs
                applied_fields.append("foreshadowing")

        write_json(str(outline_path), existing)
        generate_chapters_from_outline(book_dir, existing)

    elif context == "writing":
        # 读取当前写作进度，确定目标章节
        chat_data = _load_chat_data(book_dir, "writing")
        current_ch = chat_data.get("stage_data", {}).get("current_chapter", 1)
        if "chapter_title" in filtered or "chapter_content" in filtered or "chapter_summary" in filtered:
            title = filtered.get("chapter_title", f"第{current_ch}章")
            content = filtered.get("chapter_content", "")
            summary = filtered.get("chapter_summary", "")

            # 写入章节正文
            if content:
                final_dir = book_dir / "chapters" / "final"
                final_dir.mkdir(parents=True, exist_ok=True)
                ch_path = final_dir / f"chapter-{current_ch:03d}.md"
                from app.tools.file_ops import write_file
                write_file(str(ch_path), f"# {title}\n\n{content}")

            # 更新章节摘要
            if summary:
                save_chapter_summary(book_dir, current_ch, title, summary)

            # 更新 chapters.json 的状态
            chapters_json_path = book_dir / "chapters" / "chapters.json"
            if chapters_json_path.exists():
                chapters_data = read_json(str(chapters_json_path))
                for ch in chapters_data.get("chapters", []):
                    if ch.get("chapter_number") == current_ch:
                        if title:
                            ch["title"] = title
                        if content:
                            ch["status"] = "draft"
                            ch["word_count"] = len(content)
                        break
                write_json(str(chapters_json_path), chapters_data)

        # 写作笔记存到 chat stage_data
        if "writing_notes" in filtered:
            stage_data = chat_data.get("stage_data", {})
            stage_data["writing_notes"] = filtered["writing_notes"]
            chat_data["stage_data"] = stage_data
            _save_chat_data(book_dir, "writing", chat_data)

        applied_fields = list(filtered.keys())

    return {
        "success": True,
        "context": context,
        "applied_fields": applied_fields,
        "message": f"已同步 {len(applied_fields)} 个字段到结构化数据",
    }


# ──────────────────────────────────────────────────────────────────────────────
# PRD §6.2 契约路径别名（R2 修复）
# 说明：v4.x 实际实现为 /chat/history?context=xxx 与 /chat/all-contexts，
# 以下两个别名转发到同一逻辑，保持 PRD 契约路径可达。
# 注意：动态路径 /chat/{context} 必须在所有静态 /chat/* 路径之后注册，
# 否则会遮蔽 history / all-contexts / status 等静态路由（FastAPI 按注册顺序匹配）。
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{book_id}/chat/status")
async def get_chat_status_alias(book_id: str):
    """
    PRD 契约别名：GET /books/{book_id}/chat/status
    转发到 all-contexts 逻辑，返回所有场景的对话状态概览。
    """
    return await get_all_contexts_status(book_id)


@router.get("/{book_id}/chat/{context}")
async def get_chat_history_by_path(book_id: str, context: str):
    """
    PRD 契约别名：GET /books/{book_id}/chat/{context}
    路径参数式获取对话历史，转发到 /chat/history 同一逻辑。
    """
    return await get_chat_history(book_id, context)

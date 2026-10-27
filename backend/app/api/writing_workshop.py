"""
写作工坊 API — 三步式协作写作：上下文 → 大纲 → 写作 → 审核
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.books import _get_book_dir

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== 数据模型 ==========

class ScenePlan(BaseModel):
    """场景规划"""
    id: str = ""
    index: int = 0
    title: str = ""
    purpose: str = ""  # 场景目标/作用
    location: str = ""
    time: str = ""
    pov: str = ""  # POV角色
    conflict: str = ""  # 核心冲突
    outcome: str = ""  # 结果（是...但是.../不，而且...）
    emotional_beat: str = ""  # 情绪节拍
    word_target: int = 800  # 目标字数
    written: bool = False  # 是否已写
    content: str = ""  # 场景正文


class ChapterOutline(BaseModel):
    """章节大纲（第二步产出）"""
    chapter_number: int = 1
    chapter_title: str = ""
    core_conflict: str = ""  # 本章核心冲突
    chapter_purpose: str = ""  # 本章在全书中的作用
    rhythm_type: str = ""  # 铺垫/发展/高潮/转折/过渡
    emotional_arc: str = ""  # 情绪曲线描述
    ending_hook: str = ""  # 章末钩子
    characters: list[str] = []  # 出场角色列表
    character_roles: dict[str, str] = {}  # 每个角色的剧情作用
    active_foreshadows: list[str] = []  # 本章推进的伏笔
    new_foreshadows: list[str] = []  # 本章新埋下的伏笔
    scenes: list[ScenePlan] = []  # 场景列表
    target_words: int = 3000


class WritingContextData(BaseModel):
    """写作上下文（第一步，可编辑）"""
    chapter_number: int = 1
    chapter_title: str = ""
    volume_info: str = ""
    previous_chapter_summary: str = ""
    recent_chapters_summary: str = ""  # 前3-5章摘要
    world_summary: str = ""
    active_characters: str = ""  # 出场角色详情
    active_foreshadows: str = ""  # 活跃伏笔
    timeline_context: str = ""  # 时间线上下文
    custom_notes: str = ""  # 用户自定义补充
    total_tokens: int = 0


class AuditIssue(BaseModel):
    """审核问题"""
    id: str = ""
    type: str = ""  # consistency / quality / ai_style / pacing / other
    severity: str = "low"  # high / medium / low
    location: str = ""  # 位置描述
    description: str = ""
    suggestion: str = ""


class AuditResult(BaseModel):
    """审核结果"""
    chapter_number: int = 1
    total_words: int = 0
    target_words: int = 0
    scores: dict[str, float] = {}  # 各维度评分
    overall_score: float = 0.0
    issues: list[AuditIssue] = []
    summary: str = ""


# ========== 工具函数 ==========

def _workshop_dir(book_dir, chapter_number: int):
    """获取某章的写作工坊数据目录"""
    d = book_dir / "workshop" / f"chapter-{chapter_number:04d}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_json(file_path, default):
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def _save_json(file_path, data):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_text(file_path, default: str = "") -> str:
    if file_path.exists():
        try:
            return file_path.read_text(encoding="utf-8")
        except Exception:
            return default
    return default


def _write_text(file_path, content: str):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


# ========== Step 1: 写作上下文 ==========

@router.get("/books/{book_id}/workshop/context/{chapter_number}")
async def get_writing_workshop_context(book_id: str, chapter_number: int):
    """获取章节写作上下文（可编辑版）"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    ws_dir = _workshop_dir(book_dir, chapter_number)
    context_file = ws_dir / "context.json"

    # 如果已有用户编辑过的上下文，直接返回
    saved = _load_json(context_file, None)
    if saved:
        return saved

    # 否则从已有数据组装
    context = _assemble_context_from_workspace(book_dir, chapter_number)
    _save_json(context_file, context)

    return context


@router.put("/books/{book_id}/workshop/context/{chapter_number}")
async def update_writing_workshop_context(book_id: str, chapter_number: int, data: dict):
    """保存（用户编辑后的）写作上下文"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    ws_dir = _workshop_dir(book_dir, chapter_number)
    context_file = ws_dir / "context.json"
    _save_json(context_file, data)

    return {"success": True, "message": "上下文已保存"}


def _assemble_context_from_workspace(book_dir, chapter_number: int) -> dict:
    """从工作区已有数据组装写作上下文（读取 v4.x/v5.0 真实数据源）"""
    context = {
        "chapter_number": chapter_number,
        "chapter_title": f"第 {chapter_number} 章",
        "volume_info": "",
        "previous_chapter_summary": "",
        "recent_chapters_summary": "",
        "world_summary": "",
        "active_characters": "",
        "active_foreshadows": "",
        "timeline_context": "",
        "custom_notes": "",
        "total_tokens": 0,
    }

    # ── 世界观 + 卷纲（world/world_data.json + outline/outline.json）──
    world_data = _load_json(book_dir / "world" / "world_data.json", {}) or {}
    outline_data = _load_json(book_dir / "outline" / "outline.json", {}) or {}
    parts = []
    if world_data:
        w_lines = []
        if world_data.get("geography"):
            w_lines.append(f"地理：{world_data['geography']}")
        if world_data.get("power_system"):
            w_lines.append(f"力量体系：{world_data['power_system']}")
        if world_data.get("history"):
            w_lines.append(f"历史：{world_data['history']}")
        if world_data.get("social_rules"):
            w_lines.append(f"社会规则：{world_data['social_rules']}")
        if world_data.get("factions"):
            fac = [f.get("name", "") if isinstance(f, dict) else str(f) for f in world_data["factions"]]
            fac = [x for x in fac if x]
            if fac:
                w_lines.append("主要势力：" + "、".join(fac))
        if w_lines:
            parts.append("## 世界观设定\n" + "\n".join(w_lines))
    volumes = outline_data.get("volumes") or outline_data.get("acts") or []
    if volumes:
        v_lines = []
        for v in volumes[:5]:
            if isinstance(v, dict):
                no = v.get("volume_number", v.get("act_number", "?"))
                v_lines.append(f"- 第{no}卷 {v.get('title', '')}：{str(v.get('description', ''))[:150]}")
        if v_lines:
            parts.append("## 卷纲\n" + "\n".join(v_lines))
    if parts:
        context["world_summary"] = "\n\n".join(parts)[:2000]

    # ── 章节摘要（chapters/chapters.json 的 summary 字段）──
    chapters_data = _load_json(book_dir / "chapters" / "chapters.json", {}) or {}
    ch_entries = {}
    for c in chapters_data.get("chapters", []):
        if isinstance(c, dict):
            try:
                ch_entries[int(c.get("chapter_number", 0))] = c
            except (TypeError, ValueError):
                continue
    prev_num = chapter_number - 1
    if prev_num >= 1 and prev_num in ch_entries:
        context["previous_chapter_summary"] = str(ch_entries[prev_num].get("summary", ""))[:1000]
    recent = []
    for i in range(max(1, chapter_number - 3), chapter_number):
        if i in ch_entries:
            s = str(ch_entries[i].get("summary", ""))[:500]
            if s:
                recent.append(f"## 第 {i} 章\n{s}")
    if recent:
        context["recent_chapters_summary"] = "\n\n".join(recent)

    # ── 角色（characters/characters.json）──
    chars_data = _load_json(book_dir / "characters" / "characters.json", {}) or {}
    chars = [c for c in chars_data.get("characters", []) if isinstance(c, dict)]
    if chars:
        c_lines = []
        for c in chars[:8]:
            role = c.get("role", "")
            head = f"### {c.get('name', '未命名')}" + (f"（{role}）" if role else "")
            body = str(c.get("background", c.get("personality", "")))[:300]
            c_lines.append(head + "\n" + body if body else head)
        context["active_characters"] = "\n\n".join(c_lines)

    # ── 伏笔（outline.json.foreshadowing，唯一数据源）──
    foreshadowing = outline_data.get("foreshadowing", []) or []
    if foreshadowing:
        active = [h for h in foreshadowing if h.get("status") in ("planted", "active", "advancing")]
        if active:
            context["active_foreshadows"] = json.dumps(active[:20], ensure_ascii=False, indent=2)

    # ── token 估算（粗略：中文字数 × 1.5）──
    all_text = " ".join([
        context.get("previous_chapter_summary", ""),
        context.get("recent_chapters_summary", ""),
        context.get("world_summary", ""),
        context.get("active_characters", ""),
        context.get("active_foreshadows", ""),
    ])
    context["total_tokens"] = int(len(all_text) * 1.5)

    return context


# ========== Step 2: 章节大纲 ==========

@router.post("/books/{book_id}/workshop/outline/generate")
async def generate_chapter_outline(book_id: str, data: dict):
    """AI 生成章节大纲（场景拆解+出场角色+情绪曲线）"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    chapter_number = data.get("chapter_number", 1)
    target_words = data.get("target_words", 3000)

    # 读取上下文
    ws_dir = _workshop_dir(book_dir, chapter_number)
    context = _load_json(ws_dir / "context.json", {})

    # 调用 Plot Architect Agent
    from app.agents.plot_architect import PlotArchitectAgent
    agent = PlotArchitectAgent()

    prompt_input = {
        "sub_task": "chapter_detailed_outline",
        "chapter_number": chapter_number,
        "target_words": target_words,
        "previous_summary": context.get("previous_chapter_summary", ""),
        "recent_summary": context.get("recent_chapters_summary", ""),
        "world_summary": context.get("world_summary", ""),
        "characters": context.get("active_characters", ""),
        "foreshadows": context.get("active_foreshadows", ""),
        "custom_notes": context.get("custom_notes", ""),
    }

    result = await agent.run(prompt_input)

    # 解析结果为结构化大纲（Agent 返回的是 markdown，这里做简化存储）
    outline_data = _parse_chapter_outline(result.get("raw", ""), chapter_number, target_words)

    # 保存
    _save_json(ws_dir / "outline.json", outline_data)

    return outline_data


@router.get("/books/{book_id}/workshop/outline/{chapter_number}")
async def get_chapter_outline(book_id: str, chapter_number: int):
    """获取章节大纲"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    ws_dir = _workshop_dir(book_dir, chapter_number)
    outline_file = ws_dir / "outline.json"

    saved = _load_json(outline_file, None)
    if saved:
        return saved

    return {"chapter_number": chapter_number, "scenes": [], "characters": []}


@router.put("/books/{book_id}/workshop/outline/{chapter_number}")
async def update_chapter_outline(book_id: str, chapter_number: int, data: dict):
    """保存（用户编辑后的）章节大纲"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    ws_dir = _workshop_dir(book_dir, chapter_number)
    _save_json(ws_dir / "outline.json", data)

    return {"success": True, "message": "章节大纲已保存"}


def _parse_chapter_outline(raw: str, chapter_number: int, target_words: int) -> dict:
    """简易解析 agent 返回的 markdown 为大纲结构"""
    # 结构化大纲的基础骨架
    outline = {
        "chapter_number": chapter_number,
        "chapter_title": f"第 {chapter_number} 章",
        "core_conflict": "",
        "chapter_purpose": "",
        "rhythm_type": "",
        "emotional_arc": "",
        "ending_hook": "",
        "characters": [],
        "character_roles": {},
        "active_foreshadows": [],
        "new_foreshadows": [],
        "scenes": [],
        "target_words": target_words,
        "raw_response": raw,
    }

    lines = raw.strip().split("\n")
    current_section = ""
    current_scene = None
    scene_index = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 标题识别
        if line.startswith("# "):
            title = line[2:].strip()
            if "第" in title and "章" in title:
                outline["chapter_title"] = title
            current_section = "title"
            continue

        # 二级标题 → section 切换
        if line.startswith("## "):
            section_name = line[3:].strip().lower()
            if "核心冲突" in section_name:
                current_section = "core_conflict"
            elif "本章作用" in section_name or "章节作用" in section_name:
                current_section = "chapter_purpose"
            elif "节奏" in section_name:
                current_section = "rhythm_type"
            elif "情绪" in section_name:
                current_section = "emotional_arc"
            elif "结尾" in section_name or "钩子" in section_name:
                current_section = "ending_hook"
            elif "角色" in section_name:
                current_section = "characters"
            elif "伏笔" in section_name:
                current_section = "foreshadows"
            elif "场景" in section_name and ("拆解" in section_name or "列表" in section_name or "规划" in section_name):
                current_section = "scenes"
            else:
                current_section = "other"
            continue

        # 三级标题 → 场景
        if line.startswith("### "):
            scene_title = line[4:].strip()
            scene_index += 1
            current_scene = {
                "id": f"scene-{scene_index}",
                "index": scene_index,
                "title": scene_title,
                "purpose": "",
                "location": "",
                "time": "",
                "pov": "",
                "conflict": "",
                "outcome": "",
                "emotional_beat": "",
                "word_target": target_words // 4 if target_words else 800,
                "written": False,
                "content": "",
            }
            outline["scenes"].append(current_scene)
            continue

        # 列表项 / 内容行
        if current_section == "core_conflict":
            outline["core_conflict"] += line + "\n"
        elif current_section == "chapter_purpose":
            outline["chapter_purpose"] += line + "\n"
        elif current_section == "rhythm_type":
            outline["rhythm_type"] += line + "\n"
        elif current_section == "emotional_arc":
            outline["emotional_arc"] += line + "\n"
        elif current_section == "ending_hook":
            outline["ending_hook"] += line + "\n"
        elif current_section == "characters" and (line.startswith("- ") or line.startswith("* ")):
            char_name = line[2:].strip().split("：")[0].split(":")[0].strip()
            if char_name and char_name not in outline["characters"]:
                outline["characters"].append(char_name)
        elif current_section == "scenes" and current_scene:
            if line.startswith("- ") or line.startswith("* "):
                content = line[2:].strip()
                if "地点" in content or "location" in content.lower():
                    current_scene["location"] = content.split("：", 1)[-1].split(":", 1)[-1].strip()
                elif "时间" in content:
                    current_scene["time"] = content.split("：", 1)[-1].split(":", 1)[-1].strip()
                elif "POV" in content or "视角" in content:
                    current_scene["pov"] = content.split("：", 1)[-1].split(":", 1)[-1].strip()
                elif "冲突" in content:
                    current_scene["conflict"] = content.split("：", 1)[-1].split(":", 1)[-1].strip()
                elif "结果" in content or "结局" in content:
                    current_scene["outcome"] = content.split("：", 1)[-1].split(":", 1)[-1].strip()
                elif "目标" in content or "作用" in content:
                    current_scene["purpose"] = content.split("：", 1)[-1].split(":", 1)[-1].strip()
                elif "情绪" in content:
                    current_scene["emotional_beat"] = content.split("：", 1)[-1].split(":", 1)[-1].strip()
                elif "字数" in content:
                    import re
                    m = re.search(r"(\d+)", content)
                    if m:
                        current_scene["word_target"] = int(m.group(1))

    # 如果没解析出场景，就生成4个默认场景占位
    if len(outline["scenes"]) == 0:
        default_scene_count = 4
        per_scene_words = target_words // default_scene_count
        for i in range(default_scene_count):
            outline["scenes"].append({
                "id": f"scene-{i+1}",
                "index": i + 1,
                "title": f"场景 {i+1}",
                "purpose": "",
                "location": "",
                "time": "",
                "pov": "",
                "conflict": "",
                "outcome": "",
                "emotional_beat": "",
                "word_target": per_scene_words,
                "written": False,
                "content": "",
            })

    # 清理多余换行
    for key in ["core_conflict", "chapter_purpose", "rhythm_type", "emotional_arc", "ending_hook"]:
        outline[key] = outline[key].strip()

    return outline


# ========== Step 3: 逐场景写作 ==========

@router.post("/books/{book_id}/workshop/write-scene")
async def write_scene(book_id: str, data: dict):
    """写单个场景正文"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    chapter_number = data.get("chapter_number", 1)
    scene_index = data.get("scene_index", 1)
    instructions = data.get("instructions", "")  # 用户补充指令/修改指令

    ws_dir = _workshop_dir(book_dir, chapter_number)

    # 读取上下文和大纲
    context = _load_json(ws_dir / "context.json", {})
    outline = _load_json(ws_dir / "outline.json", {})
    scenes = outline.get("scenes", [])

    # 找到目标场景
    target_scene = None
    for s in scenes:
        if s.get("index") == scene_index:
            target_scene = s
            break

    if not target_scene:
        raise HTTPException(status_code=404, detail=f"场景 {scene_index} 不存在")

    # 获取前面已写场景的内容（作为前情）
    prev_scenes_content = ""
    for s in scenes:
        if s.get("index", 0) < scene_index and s.get("content"):
            prev_scenes_content += f"### {s.get('title', '')}\n{s.get('content', '')}\n\n"

    # 调用章节写手
    from app.agents.chapter_writer import ChapterWriterAgent
    agent = ChapterWriterAgent()

    prompt_input = {
        "mode": "write_scene",
        "chapter_number": chapter_number,
        "scene_data": target_scene,
        "target_words": target_scene.get("word_target", 800),
        "context": context.get("world_summary", "") + "\n\n" + context.get("active_characters", ""),
        "previous_chapter_summary": context.get("previous_chapter_summary", ""),
        "previous_scenes": prev_scenes_content,
        "chapter_outline": json.dumps(outline, ensure_ascii=False),
        "instructions": instructions,
    }

    result = await agent.run(prompt_input)

    # 提取正文（去掉标题行）
    content = result.get("raw", "")
    # 如果第一行是标题，去掉
    lines = content.split("\n", 1)
    if lines and lines[0].strip().startswith("#"):
        content = lines[1].strip() if len(lines) > 1 else content
    else:
        content = content.strip()

    # 更新场景状态
    target_scene["content"] = content
    target_scene["written"] = True
    outline["scenes"] = scenes
    _save_json(ws_dir / "outline.json", outline)

    # 同步更新全文
    _update_full_chapter_text(ws_dir, outline)

    return {
        "success": True,
        "scene_index": scene_index,
        "content": content,
        "word_count": len(content),
    }


@router.post("/books/{book_id}/workshop/rewrite-scene")
async def rewrite_scene(book_id: str, data: dict):
    """重写/修改某个场景"""
    # 复用 write_scene 的逻辑，instructions 里带修改意见
    return await write_scene(book_id, data)


@router.get("/books/{book_id}/workshop/full-chapter/{chapter_number}")
async def get_full_chapter(book_id: str, chapter_number: int):
    """获取整章正文（所有场景拼接）"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    ws_dir = _workshop_dir(book_dir, chapter_number)
    full_text_file = ws_dir / "full_chapter.md"

    content = _read_text(full_text_file, "")
    word_count = len(content)

    return {
        "chapter_number": chapter_number,
        "content": content,
        "word_count": word_count,
    }


def _update_full_chapter_text(ws_dir, outline: dict):
    """根据所有场景的内容更新整章正文"""
    parts = []
    chapter_title = outline.get("chapter_title", f"第 {outline.get('chapter_number', 1)} 章")
    parts.append(f"# {chapter_title}\n")

    for scene in outline.get("scenes", []):
        if scene.get("content"):
            if scene.get("title"):
                parts.append(f"\n## {scene['title']}\n")
            parts.append(scene["content"].strip())
            parts.append("")

    full_text = "\n\n".join(parts)
    _write_text(ws_dir / "full_chapter.md", full_text)


# ========== Step 4: 审核 ==========

@router.post("/books/{book_id}/workshop/audit/{chapter_number}")
async def audit_chapter(book_id: str, chapter_number: int):
    """AI 审核章节内容（一致性+质量+AI味）"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    ws_dir = _workshop_dir(book_dir, chapter_number)
    full_text_file = ws_dir / "full_chapter.md"

    if not full_text_file.exists():
        raise HTTPException(status_code=400, detail="章节尚未完成写作，无法审核")

    content = _read_text(full_text_file, "")
    context = _load_json(ws_dir / "context.json", {})
    outline = _load_json(ws_dir / "outline.json", {})

    # 调用一致性审查员
    from app.agents.consistency_checker import ConsistencyCheckerAgent
    agent = ConsistencyCheckerAgent()

    prompt_input = {
        "mode": "auditor",
        "chapter_number": chapter_number,
        "content": content,
        "context": json.dumps(context, ensure_ascii=False),
        "outline": json.dumps(outline, ensure_ascii=False),
    }

    result = await agent.run(prompt_input)

    # 解析审核结果
    audit_result = _parse_audit_result(result.get("raw", ""), chapter_number, len(content))

    # 保存
    _save_json(ws_dir / "audit.json", audit_result)

    return audit_result


@router.get("/books/{book_id}/workshop/audit/{chapter_number}")
async def get_audit_result(book_id: str, chapter_number: int):
    """获取审核结果"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    ws_dir = _workshop_dir(book_dir, chapter_number)
    audit_file = ws_dir / "audit.json"

    saved = _load_json(audit_file, None)
    if saved:
        return saved

    return {"chapter_number": chapter_number, "issues": [], "scores": {}, "overall_score": 0}


def _parse_audit_result(raw: str, chapter_number: int, word_count: int) -> dict:
    """简易解析审核结果"""
    audit = {
        "chapter_number": chapter_number,
        "total_words": word_count,
        "target_words": 3000,
        "scores": {},
        "overall_score": 0.0,
        "issues": [],
        "summary": "",
        "raw_response": raw,
    }

    lines = raw.strip().split("\n")
    current_issue = None
    issue_id = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 评分行：一致性: 8/10
        if "：" in line and any(kw in line for kw in ["一致性", "节奏", "文笔", "AI味", "人设", "逻辑", "综合"]):
            parts = line.split("：", 1)
            score_label = parts[0].strip()
            score_val = parts[1].strip()
            # 提取数字
            import re
            m = re.search(r"(\d+(?:\.\d+)?)", score_val)
            if m:
                score = float(m.group(1))
                if "综合" in score_label:
                    audit["overall_score"] = score
                else:
                    audit["scores"][score_label] = score

        # 问题项
        elif line.startswith("- ") or line.startswith("* "):
            issue_id += 1
            desc = line[2:].strip()
            severity = "medium"
            issue_type = "other"

            # 判断严重程度
            if any(kw in desc for kw in ["严重", "重大", "必须"]):
                severity = "high"
            elif any(kw in desc for kw in ["轻微", "建议", "可选"]):
                severity = "low"

            # 判断类型
            if any(kw in desc for kw in ["人设", "性格", "角色"]):
                issue_type = "consistency"
            elif any(kw in desc for kw in ["节奏", "拖沓", "紧凑"]):
                issue_type = "pacing"
            elif any(kw in desc for kw in ["AI", "模板", "生硬", "陈词滥调"]):
                issue_type = "ai_style"
            elif any(kw in desc for kw in ["逻辑", "合理", "矛盾"]):
                issue_type = "consistency"
            elif any(kw in desc for kw in ["文笔", "描写", "语言"]):
                issue_type = "quality"

            audit["issues"].append({
                "id": f"issue-{issue_id}",
                "type": issue_type,
                "severity": severity,
                "location": "",
                "description": desc,
                "suggestion": "",
            })

    # 总结
    if "总结" in raw or "总体" in raw or "综述" in raw:
        idx = raw.find("总结")
        if idx < 0:
            idx = raw.find("总体")
        if idx < 0:
            idx = raw.find("综述")
        if idx >= 0:
            audit["summary"] = raw[idx:idx + 300]

    # 如果没有评分，给个默认
    if audit["overall_score"] == 0 and audit["scores"]:
        audit["overall_score"] = sum(audit["scores"].values()) / len(audit["scores"])

    return audit


# ========== 状态查询 ==========

@router.get("/books/{book_id}/workshop/status/{chapter_number}")
async def get_workshop_status(book_id: str, chapter_number: int):
    """获取写作工坊的整体状态（当前在哪一步、完成度等）"""
    book_dir = _get_book_dir(book_id)
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail=f"书籍 {book_id} 不存在")

    ws_dir = _workshop_dir(book_dir, chapter_number)
    context_file = ws_dir / "context.json"
    outline_file = ws_dir / "outline.json"
    full_chapter_file = ws_dir / "full_chapter.md"
    audit_file = ws_dir / "audit.json"

    context_done = context_file.exists()
    outline_done = outline_file.exists()

    # 计算写作完成度
    writing_progress = 0
    total_words = 0
    if outline_file.exists():
        outline = _load_json(outline_file, {})
        scenes = outline.get("scenes", [])
        if scenes:
            written = sum(1 for s in scenes if s.get("written"))
            writing_progress = int(written / len(scenes) * 100)
            total_words = sum(len(s.get("content", "")) for s in scenes)

    audit_done = audit_file.exists()

    # 判断当前步骤
    current_step = "context"
    if outline_done and writing_progress > 0:
        current_step = "writing"
    elif outline_done:
        current_step = "outline"
    if audit_done:
        current_step = "audit"

    return {
        "chapter_number": chapter_number,
        "current_step": current_step,
        "context_done": context_done,
        "outline_done": outline_done,
        "writing_progress": writing_progress,
        "total_words": total_words,
        "audit_done": audit_done,
    }

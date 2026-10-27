"""
章节定稿 — draft → final + 触发摘要生成
"""
import json
import logging
import time
from pathlib import Path

from app.tools.file_ops import read_file, write_file, write_json
from app.llm.client import create_deepseek_client

logger = logging.getLogger(__name__)


def finalize_chapter(
    workspace_path: str,
    chapter_number: int,
    content: str = "",
) -> dict:
    """
    章节定稿流程：
    1. 将 draft 内容复制到 final
    2. 更新章节状态
    3. 生成章节摘要（简化版，不依赖 LLM）
    
    Args:
        workspace_path: 工作区路径
        chapter_number: 章节号
        content: 章节内容（如果为空则从 draft 读取）
    Returns:
        {"summary": str, "final_path": str, "word_count": int}
    """
    ws = Path(workspace_path)
    ch_id = f"chapter-{chapter_number:04d}"
    
    # 1. 确定内容来源
    if not content:
        draft_path = ws / "chapters" / "draft" / f"{ch_id}.md"
        content = read_file(str(draft_path))
    
    if not content:
        return {"summary": "无内容可定稿", "final_path": "", "word_count": 0}
    
    # 2. 写入 final 目录
    final_path = ws / "chapters" / "final" / f"{ch_id}.md"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    write_file(str(final_path), content)
    
    # 3. 统计字数
    word_count = len(content.replace("\n", "").replace(" ", ""))
    
    # 4. 生成结构化摘要（优先 LLM，失败则回退到简化版）
    summary_data = _generate_llm_summary(ch_id, content, word_count, str(ws))

    summary_path = ws / "chapters" / "summaries" / f"{ch_id}_summary.json"
    write_json(str(summary_path), summary_data)
    
    # 5. 更新章节状态
    chapter_states_path = ws / "state" / "chapter_states.json"
    if chapter_states_path.exists():
        try:
            states = json.loads(chapter_states_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            states = {"chapters": {}}
    else:
        states = {"chapters": {}}
    
    states["chapters"][ch_id] = {
        "status": "finalized",
        "word_count": word_count,
        "finalized_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    write_json(str(chapter_states_path), states)
    
    logger.info(f"章节 {ch_id} 定稿完成: {word_count} 字")
    
    return {
        "summary": f"章节 {ch_id} 定稿完成，{word_count} 字",
        "final_path": str(final_path),
        "word_count": word_count,
    }


def _generate_llm_summary(ch_id: str, content: str, word_count: int, workspace_path: str) -> dict:
    """
    调用 LLM 生成结构化摘要。
    如果 LLM 调用失败，回退到最小摘要（不阻断定稿流程）。
    """
    title = _extract_title(content, ch_id)

    try:
        import asyncio

        client = create_deepseek_client()

        # 截断过长内容，避免超出 token 限制（取前 6000 字）
        truncated = content[:6000] if len(content) > 6000 else content

        system_prompt = (
            "你是一个专业的小说编辑助手。请阅读以下章节内容，生成结构化摘要。\n"
            "请严格以 JSON 格式返回，不要包含任何其他文字。JSON 格式如下：\n"
            "{\n"
            '  "chapter": "章节ID",\n'
            '  "title": "章节标题",\n'
            '  "word_count": 字数,\n'
            '  "summary": "一段话摘要（200字以内）",\n'
            '  "character_changes": [{"name": "角色名", "change": "变化描述"}],\n'
            '  "new_facts": ["新事实1", "新事实2"],\n'
            '  "hook_changes": [{"hook_id": "hook_xxx", "action": "advance/resolve/introduce", "note": "说明"}],\n'
            '  "timeline_event": {"absolute_time": "绝对时间", "location": "地点", "duration": "持续时间"},\n'
            '  "tone": "基调",\n'
            '  "pov_character": "POV角色"\n'
            "}\n"
            "如果某个字段在内容中无法判断，请填空字符串或空数组。"
        )

        user_prompt = f"章节ID: {ch_id}\n章节标题: {title}\n字数: {word_count}\n\n章节内容：\n{truncated}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # 在同步上下文中调用异步 LLM
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 已经在事件循环中（被工作流调用时），创建新线程运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, client.chat_json(messages=messages, temperature=0.3, max_tokens=2000))
                result = future.result()
        else:
            result = asyncio.run(client.chat_json(messages=messages, temperature=0.3, max_tokens=2000))

        # 用 LLM 返回结果构造摘要，补充缺失字段
        summary_data = {
            "chapter": result.get("chapter", ch_id),
            "title": result.get("title", title),
            "word_count": result.get("word_count", word_count),
            "summary": result.get("summary", _generate_simple_summary(content)),
            "character_changes": result.get("character_changes", []),
            "new_facts": result.get("new_facts", []),
            "hook_changes": result.get("hook_changes", []),
            "timeline_event": result.get("timeline_event", None),
            "tone": result.get("tone", ""),
            "pov_character": result.get("pov_character", ""),
            "finalized_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        logger.info(f"LLM 摘要生成成功: {ch_id}")
        return summary_data

    except Exception as e:
        logger.warning(f"LLM 摘要生成失败，回退到简化摘要: {ch_id}, 错误: {e}")
        # 最小摘要 — 不阻断定稿流程
        return {
            "chapter": ch_id,
            "title": title,
            "word_count": word_count,
            "summary": _generate_simple_summary(content),
            "character_changes": [],
            "new_facts": [],
            "hook_changes": [],
            "timeline_event": None,
            "tone": "",
            "pov_character": "",
            "finalized_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }


def _extract_title(content: str, default: str) -> str:
    """从内容中提取标题（第一行 # 开头的文本）"""
    for line in content.split("\n")[:5]:
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return default


def _generate_simple_summary(content: str) -> str:
    """
    生成简化版摘要（不依赖 LLM，提取前 200 字作为临时摘要）。
    真正的摘要应由 summarize 节点调用 LLM 生成。
    """
    # 跳过标题行
    lines = content.split("\n")
    text_lines = []
    for line in lines:
        if line.strip() and not line.startswith("#"):
            text_lines.append(line.strip())
    
    text = "".join(text_lines)
    if len(text) > 200:
        # 在句号处截断
        cut = text[:200].rfind("。")
        if cut > 100:
            text = text[:cut + 1]
        else:
            text = text[:200] + "..."
    
    return text

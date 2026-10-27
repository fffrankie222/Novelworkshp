"""
上下文组装 — PRD §11.3 的完整实现
4 级优先级 + token 预算 + 相关性评分 + 降级策略
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 粗略 token 估算：中文约 1.5 字符/token
CHARS_PER_TOKEN = 1.5


def estimate_tokens(text: str) -> int:
    """估算 token 数（简单估算：字符数 / 1.5）"""
    if not text:
        return 0
    return int(len(text) / CHARS_PER_TOKEN)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """截断文本到指定 token 数"""
    max_chars = int(max_tokens * CHARS_PER_TOKEN)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


async def compose_context(
    chapter_number: int,
    workspace_path: str,
    target_model: str = "deepseek-chat",
    involved_characters: list[str] = None,
    relevant_hooks: list[str] = None,
    budget_tokens: int = 10500,
) -> dict:
    """
    组装章节生成所需的上下文。
    
    优先级：
    1. 必须注入（~3000 token）— 世界圣经摘要 + 角色状态 + 硬规则
    2. 近期前文（~4000 token）— 最近 2 章全文/摘要
    3. 早期摘要（~2000 token）— 按相关性选取
    4. 本章规划（~1500 token）— 章节意图 + 活跃伏笔
    
    Args:
        chapter_number: 当前章节号
        workspace_path: 工作区路径
        target_model: 目标模型
        involved_characters: 本章涉及的角色
        relevant_hooks: 本章相关伏笔 ID
        budget_tokens: 总 token 预算
    Returns:
        {"context_text": str, "token_usage": dict, "total_tokens": int, "truncated_warnings": list}
    """
    ws = Path(workspace_path)
    involved_characters = involved_characters or []
    relevant_hooks = relevant_hooks or []
    
    token_usage = {}
    truncated_warnings = []
    context_parts = []
    
    # ===== 优先级 1: 必须注入 (~3000 token) =====
    p1_budget = 3000
    
    # 1a. 世界圣经摘要 (≤1000 token)
    world_bible_path = ws / "world" / "world_bible.md"
    world_text = ""
    if world_bible_path.exists():
        world_text = world_bible_path.read_text(encoding="utf-8")
        world_text = truncate_to_tokens(world_text, 1000)
    token_usage["world_bible"] = estimate_tokens(world_text)
    context_parts.append(f"## 世界设定摘要\n{world_text}\n")
    
    # 1b. 活跃角色当前状态 (≤1000 token)
    char_states_path = ws / "state" / "character_states.json"
    char_text = ""
    if char_states_path.exists():
        try:
            char_states = json.loads(char_states_path.read_text(encoding="utf-8"))
            # 筛选涉及的角色
            filtered = {}
            for name in involved_characters:
                if name in char_states.get("characters", {}):
                    filtered[name] = char_states["characters"][name]
            if not filtered:
                filtered = char_states.get("characters", {})
            char_text = json.dumps(filtered, ensure_ascii=False, indent=2)
            char_text = truncate_to_tokens(char_text, 1000)
        except json.JSONDecodeError:
            pass
    token_usage["character_states"] = estimate_tokens(char_text)
    context_parts.append(f"## 角色当前状态\n{char_text}\n")
    
    # 1c. 硬规则 (≤1000 token)
    config_path = ws / "config.json"
    rules_text = ""
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            world_rules = config.get("world_rules", {}).get("hard_constraints", [])
            char_rules = config.get("character_rules", {}).get("hard_constraints", [])
            rules_items = [r.get("rule", "") for r in world_rules + char_rules]
            rules_text = "\n".join(f"- {r}" for r in rules_items if r)
            rules_text = truncate_to_tokens(rules_text, 1000)
        except json.JSONDecodeError:
            pass
    token_usage["rules"] = estimate_tokens(rules_text)
    context_parts.append(f"## 核心规则\n{rules_text}\n")
    
    p1_used = sum(token_usage.get(k, 0) for k in ["world_bible", "character_states", "rules"])
    
    # ===== 优先级 2: 近期前文 (~4000 token) =====
    p2_budget = 4000
    recent_text = ""
    
    # 读取最近 2 章全文
    for offset in range(1, 3):
        prev_num = chapter_number - offset
        if prev_num <= 0:
            break
        prev_id = f"chapter-{prev_num:04d}"
        # 先尝试定稿版本，再尝试草稿
        for prefix in ["final", "draft"]:
            prev_path = ws / "chapters" / prefix / f"{prev_id}.md"
            if prev_path.exists():
                prev_content = prev_path.read_text(encoding="utf-8")
                prev_content = truncate_to_tokens(prev_content, 2000)
                recent_text += f"\n### {prev_id} 前文\n{prev_content}\n"
                break
    
    if not recent_text:
        # 没有最近章节全文，用摘要填充
        for offset in range(1, 3):
            prev_num = chapter_number - offset
            if prev_num <= 0:
                break
            summary_path = ws / "chapters" / "summaries" / f"chapter-{prev_num:04d}_summary.json"
            if summary_path.exists():
                try:
                    summary = json.loads(summary_path.read_text(encoding="utf-8"))
                    recent_text += f"\n### {summary.get('chapter', '')} 摘要\n{summary.get('summary', '')}\n"
                except json.JSONDecodeError:
                    pass
    
    recent_text = truncate_to_tokens(recent_text, p2_budget)
    token_usage["recent_chapters"] = estimate_tokens(recent_text)
    context_parts.append(f"## 近期前文\n{recent_text}\n")
    
    # ===== 优先级 3: 早期摘要 (~2000 token) =====
    p3_budget = 2000
    summaries_path = ws / "chapters" / "summaries"
    early_summaries = ""
    
    if summaries_path.exists():
        summary_files = sorted(summaries_path.glob("*.json"))
        # 按相关性评分排序
        scored = []
        for sf in summary_files:
            try:
                s = json.loads(sf.read_text(encoding="utf-8"))
                score = 0
                s_text = json.dumps(s, ensure_ascii=False)
                
                # 提及涉及的角色 +3
                for char in involved_characters:
                    if char in s_text:
                        score += 3
                        break
                
                # 提及相关伏笔 +3
                for hook in relevant_hooks:
                    if hook in s_text:
                        score += 3
                        break
                
                # 章节号越近 +1
                ch_num = s.get("chapter", "").replace("chapter-", "")
                try:
                    ch_int = int(ch_num)
                    score += max(0, 5 - abs(chapter_number - ch_int))
                except (ValueError, TypeError):
                    pass
                
                scored.append((score, s))
            except json.JSONDecodeError:
                continue
        
        # 按分数降序取 top 5
        scored.sort(key=lambda x: x[0], reverse=True)
        for score, s in scored[:5]:
            early_summaries += f"- {s.get('chapter', '?')}: {s.get('summary', '')}\n"
        
        early_summaries = truncate_to_tokens(early_summaries, p3_budget)
    
    token_usage["early_summaries"] = estimate_tokens(early_summaries)
    context_parts.append(f"## 早期章节摘要\n{early_summaries}\n")
    
    # ===== 优先级 4: 本章规划 (~1500 token) =====
    p4_budget = 1500
    
    # 章节意图
    intent_path = ws / "runtime" / f"chapter-{chapter_number:04d}" / "intent.md"
    intent_text = ""
    if intent_path.exists():
        intent_text = intent_path.read_text(encoding="utf-8")
    
    # 活跃伏笔（v4.0: 从 outline.json.foreshadowing 读取）
    outline_path = ws / "outline" / "outline.json"
    hook_text = ""
    if outline_path.exists():
        try:
            outline_data = json.loads(outline_path.read_text(encoding="utf-8"))
            active_hooks = [
                h for h in outline_data.get("foreshadowing", [])
                if h.get("status") in ["active", "planted"]
            ]
            # 筛选相关的
            if relevant_hooks:
                relevant_set = set(relevant_hooks)
                filtered = [h for h in active_hooks if h.get("id") in relevant_set]
                if filtered:
                    active_hooks = filtered
            hook_text = json.dumps(active_hooks, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
    
    plan_text = ""
    if intent_text:
        plan_text += f"### 本章意图\n{intent_text}\n"
    if hook_text:
        plan_text += f"### 活跃伏笔\n{hook_text}\n"
    
    plan_text = truncate_to_tokens(plan_text, p4_budget)
    token_usage["chapter_plan"] = estimate_tokens(plan_text)
    context_parts.append(f"## 本章规划\n{plan_text}\n")
    
    # ===== 总计 & 降级检查 =====
    total_tokens = sum(token_usage.values())
    
    if total_tokens > budget_tokens:
        # 降级策略
        logger.warning(f"上下文 token 超限: {total_tokens}/{budget_tokens}，执行降级")
        
        # 降级 1: 裁剪世界设定至核心规则
        if token_usage.get("world_bible", 0) > 500:
            world_text = truncate_to_tokens(world_text, 500)
            truncated_warnings.append("世界设定已裁剪至核心规则")
        
        # 降级 2: 最近 2 章全文替换为摘要
        if token_usage.get("recent_chapters", 0) > 2000:
            recent_text = truncate_to_tokens(recent_text, 1000)
            truncated_warnings.append("近期前文已替换为摘要")
        
        # 降级 3: 早期摘要从 5 章缩减到 3 章
        truncated_warnings.append("早期摘要已缩减")
        
        total_tokens = sum(estimate_tokens(p) for p in context_parts)
    
    # 拼装最终上下文文本
    context_text = "\n\n".join(part for part in context_parts if part.strip())
    
    return {
        "context_text": context_text,
        "token_usage": token_usage,
        "total_tokens": estimate_tokens(context_text),
        "truncated_warnings": truncated_warnings,
    }

"""
WritingContext Service — 统一封装写作场景所需的 10 项上下文数据
数据来源：world_data.json、outline.json、characters.json、chapters/、book.json / config.json

v4.0 核心改动：替代 chat.py 中 _build_system_prompt 的硬编码拼接，
同时替代 outline.py 中 writing-context 端点的重复逻辑。
"""
import json
import logging
import re
from pathlib import Path
from typing import Optional

from app.api.books import _get_book_dir
from app.tools.file_ops import read_json, read_file

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token 估算：中文约 1 字 ≈ 1.5 token
# ---------------------------------------------------------------------------

TOKEN_PER_CHAR = 1.5  # 粗略估算


def _estimate_tokens(text: str) -> int:
    """估算 token 数（粗略）"""
    return int(len(text) * TOKEN_PER_CHAR)


def _truncate(text: str, max_tokens: int) -> tuple[str, bool]:
    """
    按 token 上限截断文本。
    返回 (截断后文本, 是否发生了截断)。
    """
    if not text:
        return text, False
    est = _estimate_tokens(text)
    if est <= max_tokens:
        return text, False
    # 按字符截断（保守一些，确保不超 token 上限）
    max_chars = int(max_tokens / TOKEN_PER_CHAR)
    return text[:max_chars] + "...", True


# ---------------------------------------------------------------------------
# 内部：大纲 volumes 标准化（兼容新旧格式）
# ---------------------------------------------------------------------------

def _normalize_volumes(data: dict) -> list[dict]:
    """
    从 outline.json 提取 volumes 数组，兼容旧格式。
    """
    volumes = data.get("volumes", [])
    if volumes and isinstance(volumes, list):
        return volumes

    # 旧格式：outline 字段里是 OutlineNode[]
    outline_nodes = data.get("outline", [])
    if outline_nodes and isinstance(outline_nodes, list):
        converted = []
        for i, node in enumerate(outline_nodes):
            if not isinstance(node, dict):
                continue
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
                if not converted:
                    converted.append({
                        "id": "vol-auto", "number": 1, "title": "正文",
                        "story_arc": "", "chapters": [],
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

    # chapters 字段（更旧格式）
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
                "id": "vol-auto", "number": 1, "title": "正文",
                "story_arc": "", "chapters": ch_list,
            }]

    return []


def _find_chapter_in_volumes(volumes: list[dict], chapter_number: int):
    """在 volumes 中查找指定章节号，返回 (volume, chapter) 或 (None, None)"""
    for vol in volumes:
        for ch in vol.get("chapters", []):
            if ch.get("number") == chapter_number:
                return vol, ch
    return None, None


def _flatten_chapters(volumes: list[dict]) -> list[dict]:
    """将 volumes 中的章节展平为有序列表"""
    result = []
    for vol in volumes:
        for ch in vol.get("chapters", []):
            result.append({
                "number": ch.get("number", 0),
                "title": ch.get("title", ""),
                "summary": ch.get("summary", ""),
                "characters": ch.get("characters", []),
                "volume_number": vol.get("number", 0),
                "volume_title": vol.get("title", ""),
                "volume_arc": vol.get("story_arc", ""),
                "id": ch.get("id", ""),
            })
    result.sort(key=lambda c: c["number"])
    return result


# ---------------------------------------------------------------------------
# 核心：WritingContextService
# ---------------------------------------------------------------------------

class WritingContextService:
    """
    统一封装写作场景所需的 10 项上下文数据。
    调用 get_writing_context(book_id, chapter_number) 获取完整结果。
    """

    # Token 上限定义（PRD 5.1 节）
    TOKEN_LIMITS = {
        "world_summary":       2000,
        "volume_structure":    3000,
        "current_volume_arc":  500,
        "current_chapter":     500,
        "prev_chapters":       2000,
        "next_chapters":       1000,
        "active_characters":   3000,
        "active_foreshadows":  2000,
        "style_guide":         1500,
        "writing_rules":       500,
    }

    TOTAL_BUDGET = 16000  # 总 Token 预算

    def __init__(self, book_id: str):
        self.book_id = book_id
        self.book_dir: Path = _get_book_dir(book_id)
        self._outline_data: Optional[dict] = None
        self._volumes: Optional[list[dict]] = None

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------

    def get_writing_context(self, chapter_number: int) -> dict:
        """
        获取指定章节的完整写作上下文。
        返回格式与 PRD 6.6 节 WritingContextResponse 一致。
        """
        # 加载基础数据
        outline_data = self._get_outline_data()
        volumes = self._get_volumes(outline_data)
        current_vol, current_ch_data = _find_chapter_in_volumes(volumes, chapter_number)
        all_chapters = _flatten_chapters(volumes)

        items = []

        # 1. 世界观精简版
        items.append(self._build_world_summary())

        # 2. 卷章结构全量
        items.append(self._build_volume_structure(volumes))

        # 3. 当前卷故事线
        items.append(self._build_current_volume_arc(current_vol, chapter_number))

        # 4. 当前章信息
        items.append(self._build_current_chapter_info(current_ch_data, chapter_number))

        # 5. 前 10 章摘要
        items.append(self._build_prev_chapters(all_chapters, chapter_number))

        # 6. 后 5 章预告
        items.append(self._build_next_chapters(all_chapters, chapter_number))

        # 7. 出场角色详细卡
        items.append(self._build_active_characters(current_ch_data, chapter_number))

        # 8. 活跃伏笔
        items.append(self._build_active_foreshadows(outline_data, chapter_number))

        # 9. 风格指南
        items.append(self._build_style_guide())

        # 10. 写作规则
        items.append(self._build_writing_rules())

        # 统计 Token
        total_budget = self.TOTAL_BUDGET
        total_used = sum(it["token_count"] for it in items)

        # Token 预算统计
        budget_items = []
        for it in items:
            max_tok = self.TOKEN_LIMITS.get(it["context_name"], 9999)
            budget_items.append({
                "context_name": it["context_name"],
                "max_tokens": max_tok,
                "actual_tokens": it["token_count"],
                "truncated": it["truncated"],
            })

        token_budget = {
            "items": budget_items,
            "total_budget": total_budget,
            "total_used": total_used,
        }

        # 章节标题
        chapter_title = current_ch_data.get("title", f"第{chapter_number}章") if current_ch_data else f"第{chapter_number}章"

        return {
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "items": items,
            "total_tokens": total_used,
            "token_budget": token_budget,
        }

    def build_system_prompt_for_writing(self, chapter_number: int, base_prompt: str, book_info: str, style_guide_text: str) -> str:
        """
        使用 WritingContext Service 的数据构建 writing 场景的 system prompt。
        替代 chat.py 中 _build_system_prompt 的 writing 场景硬编码部分。
        """
        ctx = self.get_writing_context(chapter_number)
        prompt_parts = [base_prompt]

        if book_info:
            prompt_parts.append(f"\n\n--- 书籍基本信息 ---\n{book_info}")

        if style_guide_text:
            prompt_parts.append(f"\n\n{style_guide_text}")

        for item in ctx["items"]:
            content = item.get("content")
            name = item.get("name", "")
            if not content:
                continue
            # 格式化注入
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
            # 风格指南和写作规则已在外层注入，不重复

        return "\n".join(prompt_parts)

    # ------------------------------------------------------------------
    # 各上下文项构建方法
    # ------------------------------------------------------------------

    def _build_world_summary(self) -> dict:
        """1. 世界观精简版 — 来源: world_data.json，上限 2000 token"""
        max_tokens = self.TOKEN_LIMITS["world_summary"]
        world_data = read_json(str(self.book_dir / "world" / "world_data.json")) or {}
        parts = []
        for key, label in [("geography", "地理"), ("power_system", "力量体系"),
                            ("factions", "势力"), ("social_rules", "社会规则")]:
            val = world_data.get(key, "")
            if val:
                val_str = str(val)
                if len(val_str.strip()) > 0:
                    # 每字段最多 ~333 字 ≈ 500 token
                    per_field_max_chars = int(500 / TOKEN_PER_CHAR)
                    truncated_val = val_str[:per_field_max_chars]
                    is_trunc = len(val_str) > per_field_max_chars
                    parts.append(f"【{label}】{truncated_val}{'...' if is_trunc else ''}")
        text = "\n".join(parts) if parts else "（暂无世界观数据）"
        final_text, was_truncated = _truncate(text, max_tokens)
        return {
            "context_name": "world_summary",
            "name": "世界观精简版",
            "content": final_text,
            "token_count": _estimate_tokens(final_text),
            "truncated": was_truncated,
        }

    def _build_volume_structure(self, volumes: list[dict]) -> dict:
        """2. 卷章结构全量 — 来源: outline.json.volumes，上限 3000 token"""
        max_tokens = self.TOKEN_LIMITS["volume_structure"]
        if not volumes:
            text = "（暂无大纲数据）"
        else:
            parts = []
            for vol in volumes:
                parts.append(f"【第{vol.get('number', '')}卷】{vol.get('title', '')}")
                for ch in vol.get("chapters", []):
                    title = ch.get("title", "")
                    summary = ch.get("summary", "")
                    line = f"  第{ch.get('number', '')}章 {title}"
                    if summary:
                        line += f" — {str(summary)[:80]}"
                    parts.append(line)
            text = "\n".join(parts)
        final_text, was_truncated = _truncate(text, max_tokens)
        return {
            "context_name": "volume_structure",
            "name": "卷章结构全量",
            "content": final_text,
            "token_count": _estimate_tokens(final_text),
            "truncated": was_truncated,
        }

    def _build_current_volume_arc(self, current_vol: Optional[dict], chapter_number: int) -> dict:
        """3. 当前卷故事线 — 来源: outline.json，上限 500 token"""
        max_tokens = self.TOKEN_LIMITS["current_volume_arc"]
        if current_vol:
            arc = current_vol.get("story_arc", "（未设定）")
            text = (
                f"--- 当前卷：第{current_vol.get('number', '')}卷《{current_vol.get('title', '')}》 ---\n"
                f"卷故事线：{arc}"
            )
        else:
            text = f"--- 当前章节：第{chapter_number}章 ---\n（未在大纲中找到对应卷信息）"
        final_text, was_truncated = _truncate(text, max_tokens)
        return {
            "context_name": "current_volume_arc",
            "name": "当前卷故事线",
            "content": final_text,
            "token_count": _estimate_tokens(final_text),
            "truncated": was_truncated,
        }

    def _build_current_chapter_info(self, current_ch_data: Optional[dict], chapter_number: int) -> dict:
        """4. 当前章信息 — 来源: outline.json，上限 500 token"""
        max_tokens = self.TOKEN_LIMITS["current_chapter"]
        if current_ch_data:
            ch_chars = current_ch_data.get("characters", [])
            chars_text = "、".join(ch_chars) if ch_chars else "（未指定）"
            text = (
                f"--- 当前写作：第{chapter_number}章《{current_ch_data.get('title', '')}》 ---\n"
                f"章节简介：{current_ch_data.get('summary', '（未设定）')}\n"
                f"出场角色：{chars_text}"
            )
        else:
            text = f"--- 当前写作：第{chapter_number}章 ---\n（未在大纲中找到本章信息）"
        final_text, was_truncated = _truncate(text, max_tokens)
        return {
            "context_name": "current_chapter",
            "name": "当前章信息",
            "content": final_text,
            "token_count": _estimate_tokens(final_text),
            "truncated": was_truncated,
        }

    def _build_prev_chapters(self, all_chapters: list[dict], chapter_number: int) -> dict:
        """5. 前 10 章摘要 — 来源: outline + chapter summaries，上限 2000 token"""
        max_tokens = self.TOKEN_LIMITS["prev_chapters"]
        prev_chs = [c for c in all_chapters if c["number"] < chapter_number][-10:]
        if not prev_chs:
            text = "（无前序章节）"
        else:
            # 尝试补充 chapters/ 目录中的实际摘要
            parts = []
            for c in prev_chs:
                # 尝试从章节摘要文件读取更丰富的摘要
                summary = self._get_chapter_summary(c["number"]) or str(c.get("summary", ""))[:100]
                parts.append(f"第{c['number']}章 {c['title']}：{summary}")
            text = f"--- 前序章节（最近{len(prev_chs)}章） ---\n" + "\n".join(parts)
        final_text, was_truncated = _truncate(text, max_tokens)
        return {
            "context_name": "prev_chapters",
            "name": "前 10 章摘要",
            "content": final_text,
            "token_count": _estimate_tokens(final_text),
            "truncated": was_truncated,
        }

    def _build_next_chapters(self, all_chapters: list[dict], chapter_number: int) -> dict:
        """6. 后 5 章预告 — 来源: outline.json，上限 1000 token"""
        max_tokens = self.TOKEN_LIMITS["next_chapters"]
        next_chs = [c for c in all_chapters if c["number"] > chapter_number][:5]
        if not next_chs:
            text = "（无后续章节预告）"
        else:
            parts = []
            for c in next_chs:
                summary_short = str(c.get("summary", ""))[:80]
                parts.append(f"第{c['number']}章 {c['title']}：{summary_short}")
            text = f"--- 后续章节预告 ---\n" + "\n".join(parts)
        final_text, was_truncated = _truncate(text, max_tokens)
        return {
            "context_name": "next_chapters",
            "name": "后 5 章预告",
            "content": final_text,
            "token_count": _estimate_tokens(final_text),
            "truncated": was_truncated,
        }

    def _build_active_characters(self, current_ch_data: Optional[dict], chapter_number: int) -> dict:
        """7. 出场角色详细卡 — 来源: characters.json，上限 3000 token，≤8 人"""
        max_tokens = self.TOKEN_LIMITS["active_characters"]
        char_data = read_json(str(self.book_dir / "characters" / "characters.json")) or {}
        all_chars = char_data.get("characters", [])

        # 确定出场角色
        ch_char_names = current_ch_data.get("characters", []) if current_ch_data else []
        if ch_char_names:
            relevant_chars = [c for c in all_chars if c.get("name", "") in ch_char_names]
        else:
            relevant_chars = [c for c in all_chars if c.get("role", "") in ("主角", "男主", "女主", "男主角", "女主角")]

        if not relevant_chars:
            text = "（暂无出场角色信息）"
        else:
            char_parts = []
            for c in relevant_chars[:8]:
                entry = f"【{c.get('name', '')}】{c.get('role', '')}"
                if c.get("personality"):
                    entry += f"\n  性格：{str(c['personality'])[:200]}"
                if c.get("background"):
                    entry += f"\n  背景：{str(c['background'])[:200]}"
                if c.get("catchphrase"):
                    entry += f"\n  口头禅：{c['catchphrase']}"
                char_parts.append(entry)
            text = f"--- 本章出场角色 ---\n" + "\n".join(char_parts)
        final_text, was_truncated = _truncate(text, max_tokens)
        return {
            "context_name": "active_characters",
            "name": "出场角色详细卡",
            "content": final_text,
            "token_count": _estimate_tokens(final_text),
            "truncated": was_truncated,
        }

    def _build_active_foreshadows(self, outline_data: dict, chapter_number: int) -> dict:
        """8. 活跃伏笔 — 来源: outline.json.foreshadowing，上限 2000 token，≤10 条"""
        max_tokens = self.TOKEN_LIMITS["active_foreshadows"]
        # 仅从 outline.json.foreshadowing 读取（v4.0 统一存储）
        foreshadows = outline_data.get("foreshadowing", [])

        active_fs = []
        for fs in foreshadows:
            if not isinstance(fs, dict):
                continue
            start = fs.get("start_chapter", 0)
            end = fs.get("end_chapter", 0)
            status = fs.get("status", "planted")
            if status == "resolved":
                continue
            if start <= chapter_number and status in ("planted", "active"):
                active_fs.append(fs)
            elif start <= chapter_number and abs(end - chapter_number) <= 5:
                active_fs.append(fs)

        if not active_fs:
            text = "（当前无活跃伏笔）"
        else:
            fs_parts = []
            for fs in active_fs[:10]:
                chars = "、".join(fs.get("characters", [])) or "—"
                fs_parts.append(
                    f"【{fs.get('purpose', '')}】第{fs.get('start_chapter', '?')}章埋下 → 第{fs.get('end_chapter', '?')}章回收 "
                    f"| 涉及角色: {chars} | 状态: {fs.get('status', 'planted')}\n"
                    f"  说明：{fs.get('description', '')[:150]}"
                )
            text = f"--- 活跃伏笔（需关注引爆时机） ---\n" + "\n".join(fs_parts)
        final_text, was_truncated = _truncate(text, max_tokens)
        return {
            "context_name": "active_foreshadows",
            "name": "活跃伏笔",
            "content": final_text,
            "token_count": _estimate_tokens(final_text),
            "truncated": was_truncated,
        }

    def _build_style_guide(self) -> dict:
        """9. 风格指南 — 来源: config.json.writing_config.style_guide，上限 1500 token"""
        max_tokens = self.TOKEN_LIMITS["style_guide"]
        config_path = self.book_dir / "config.json"
        if not config_path.exists():
            text = ""
        else:
            config = read_json(str(config_path))
            sg = config.get("style_guide", "")
            if isinstance(sg, str):
                text = sg
            elif isinstance(sg, dict):
                # 格式化为可读文本
                parts = []
                if sg.get("narrative_pov"):
                    parts.append(f"叙事视角：{sg['narrative_pov']}")
                if sg.get("tone"):
                    parts.append(f"语言风格：{sg['tone']}")
                if sg.get("dialogue_style"):
                    parts.append(f"对话风格：{sg['dialogue_style']}")
                if sg.get("chapter_ending_hook"):
                    parts.append(f"章节结尾钩子：{sg.get('chapter_ending_hook_instruction', '是')}")
                pacing = sg.get("pacing", {})
                if pacing.get("overall_curve"):
                    parts.append(f"节奏：{pacing['overall_curve']}")
                if sg.get("custom_rules"):
                    parts.append(f"自定义规则：{sg['custom_rules']}")
                text = "\n".join(parts)
            else:
                text = ""
        if not text:
            text = "（暂无风格指南）"
        final_text, was_truncated = _truncate(text, max_tokens)
        return {
            "context_name": "style_guide",
            "name": "风格指南",
            "content": final_text,
            "token_count": _estimate_tokens(final_text),
            "truncated": was_truncated,
        }

    def _build_writing_rules(self) -> dict:
        """10. 写作规则 — 上限 500 token

        数据来源（兼容合并）：
        - config.json.style（forbidden_patterns / preferred_techniques，v4.x 实际写入位置，books.py:236-245）
        - config.json.character_rules / world_rules（hard_constraints / soft_*）
        - config.json.target_words_per_chapter（单章目标字数）
        - config.json.writing_config（PRD WritingConfig 键，若存在则优先采用其字段）
        旧实现只读 config.writing_config，但创建/更新配置从不写该键，导致本项恒为空转（审计 Y3）。
        """
        max_tokens = self.TOKEN_LIMITS["writing_rules"]
        config_path = self.book_dir / "config.json"
        if not config_path.exists():
            text = "（暂无写作规则）"
        else:
            config = read_json(str(config_path))
            style = config.get("style", {}) or {}
            char_rules = config.get("character_rules", {}) or {}
            world_rules = config.get("world_rules", {}) or {}
            wc = config.get("writing_config", {}) or {}

            parts = []

            # 禁止模式：优先 writing_config，其次实际 style 字段
            forbidden = wc.get("forbidden_patterns") or style.get("forbidden_patterns") or []
            if forbidden:
                parts.append(f"禁止模式：{', '.join(forbidden[:10])}")

            # 推荐技法：优先 writing_config，其次 style
            preferred = wc.get("preferred_techniques") or style.get("preferred_techniques") or []
            if preferred:
                parts.append(f"推荐技法：{', '.join(preferred[:10])}")

            # 硬性约束：合并 writing_config / character_rules / world_rules 三处
            hard = list(wc.get("hard_constraints") or [])
            for extra in (char_rules.get("hard_constraints") or [], world_rules.get("hard_constraints") or []):
                for item in extra:
                    if item not in hard:
                        hard.append(item)
            if hard:
                parts.append(f"硬性约束：{'; '.join(hard[:10])}")

            # 单章目标字数：优先 writing_config.target_word_count，其次书籍级 target_words_per_chapter
            target = wc.get("target_word_count") or config.get("target_words_per_chapter")
            if target:
                parts.append(f"单章目标字数：{target}")

            text = "\n".join(parts) if parts else "（暂无额外写作规则）"
        final_text, was_truncated = _truncate(text, max_tokens)
        return {
            "context_name": "writing_rules",
            "name": "写作规则",
            "content": final_text,
            "token_count": _estimate_tokens(final_text),
            "truncated": was_truncated,
        }

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _get_outline_data(self) -> dict:
        """加载 outline.json（带缓存）"""
        if self._outline_data is None:
            self._outline_data = read_json(str(self.book_dir / "outline" / "outline.json")) or {}
        return self._outline_data

    def _get_volumes(self, outline_data: Optional[dict] = None) -> list[dict]:
        """获取标准化的 volumes 列表（带缓存）"""
        if self._volumes is None:
            data = outline_data or self._get_outline_data()
            self._volumes = _normalize_volumes(data)
        return self._volumes

    def _get_chapter_summary(self, chapter_number: int) -> str:
        """
        从 chapters/summaries/ 目录读取章节摘要文本。
        如果不存在则返回空字符串。
        """
        summary_path = self.book_dir / "chapters" / "summaries" / f"chapter-{chapter_number:03d}_summary.json"
        if summary_path.exists():
            data = read_json(str(summary_path))
            if data:
                return data.get("text", data.get("summary", ""))
        # 也尝试从 chapters.json 获取
        chapters_json_path = self.book_dir / "chapters" / "chapters.json"
        if chapters_json_path.exists():
            chapters_data = read_json(str(chapters_json_path))
            for ch in chapters_data.get("chapters", []):
                if ch.get("chapter_number") == chapter_number:
                    summary = ch.get("summary", "")
                    if isinstance(summary, dict):
                        return summary.get("text", str(summary))
                    return str(summary)
        return ""

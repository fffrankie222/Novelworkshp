"""
Char Designer Agent — 角色设计师
职责：人物创建、蒸馏、关系图谱维护、角色弧线设计
task_type: creative_high → 火山引擎 volc-pro (primary)

【改造】输出处理：解析 14 字段 JSON → 写入 PROFILE.json → 调用拆分脚本 → 生成 PROFILE.md
"""
import json
import logging
import re
from pathlib import Path

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class CharDesignerAgent(BaseAgent):
    agent_name = "char_designer"
    prompt_file = "char_designer.md"
    task_type = "creative_high"
    default_temperature = 0.5
    default_max_tokens = 8000

    def build_messages(self, task_input: dict, system_prompt: str) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]

        task_type = task_input.get("sub_task", "create")

        if task_type == "create":
            # 创建新角色
            world_summary = task_input.get("world_summary", "")
            char_descriptions = task_input.get("characters", [])

            user_content = f"基于以下世界设定，创建角色档案：\n\n"
            user_content += f"**世界设定摘要**：\n{world_summary}\n\n"
            user_content += f"**角色描述**：\n"
            for char in char_descriptions:
                user_content += f"- {char.get('name', '?')}: {char.get('description', '')}\n"

            user_content += "\n请严格按 14 组字段 JSON 格式输出完整角色档案。\n"
            user_content += "输出顺序：先输出 JSON 角色档案，然后用 === 分隔，输出 relations.mermaid.md。\n"

        elif task_type == "distill":
            # 从已有文本蒸馏角色
            source_text = task_input.get("source_text", "")
            user_content = f"请从以下文本中蒸馏角色档案：\n\n{source_text}\n\n"
            user_content += "提取所有重要角色的 14 组字段信息，严格按 JSON 格式输出。\n"

        elif task_type == "update":
            # 更新角色状态
            character_name = task_input.get("character_name", "")
            changes = task_input.get("changes", "")
            user_content = f"请更新角色 {character_name} 的状态：\n{changes}\n"
            user_content += "按 14 组字段 JSON 格式输出更新后的完整档案。\n"

        else:
            user_content = task_input.get("task", "请帮助我设计角色")

        messages.append({"role": "user", "content": user_content})
        return messages

    def parse_response(self, response: str, task_input: dict) -> dict:
        """
        解析 LLM 响应：
        1. 提取 JSON 角色档案 → 写入 PROFILE.json
        2. 调用拆分脚本生成 7 个子文件 + PROFILE.md
        3. 提取 relations.mermaid.md
        """
        workspace_path = task_input.get("workspace_path", "")
        parsed = {
            "output_files": [],
            "sections": {},
            "raw": response,
            "json_output": {},
        }

        # 用 === 分割响应
        sections = response.split("===")

        # ---- 第一步：提取 JSON 角色档案 ----
        profile_json = self._extract_json(sections[0] if sections else response)

        if profile_json:
            parsed["json_output"] = profile_json

            # 写入 PROFILE.json
            if workspace_path:
                chars_dir = Path(workspace_path) / "characters"
                chars_dir.mkdir(parents=True, exist_ok=True)

                json_path = chars_dir / "PROFILE.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(profile_json, f, ensure_ascii=False, indent=2)
                parsed["output_files"].append("characters/PROFILE.json")
                logger.info(f"角色档案 JSON 已写入: {json_path}")

                # ---- 第二步：调用拆分脚本 ----
                split_result = self._run_split(workspace_path)
                if split_result:
                    parsed["output_files"].extend(split_result.get("output_files", []))
                    parsed["characters"] = split_result.get("characters", [])
                    parsed["summary"] = split_result.get("summary", "角色档案拆分完成")
                else:
                    parsed["summary"] = "角色 JSON 已生成，但拆分脚本执行失败"
            else:
                parsed["summary"] = "角色 JSON 已生成（无 workspace_path，未写入文件）"
        else:
            # JSON 提取失败，尝试从原始文本中解析
            logger.warning("未能从 LLM 响应中提取到有效 JSON，回退到启发式解析")
            parsed["summary"] = "角色设计完成（JSON 解析失败，已保存原始文本）"

            # 保存原始响应到 PROFILE.md
            if workspace_path:
                chars_dir = Path(workspace_path) / "characters"
                chars_dir.mkdir(parents=True, exist_ok=True)
                md_path = chars_dir / "PROFILE.md"
                md_path.write_text(response, encoding="utf-8")
                parsed["output_files"].append("characters/PROFILE.md")

        # ---- 第三步：提取关系图谱 ----
        relations_content = ""
        for section in sections[1:]:
            section = section.strip()
            if "mermaid" in section.lower() or "relation" in section.lower():
                relations_content = section
                break

        if not relations_content and len(sections) > 1:
            # 取最后一段作为关系图
            relations_content = sections[-1].strip()

        if relations_content and workspace_path:
            chars_dir = Path(workspace_path) / "characters"
            chars_dir.mkdir(parents=True, exist_ok=True)
            rel_path = chars_dir / "relations.mermaid.md"
            rel_path.write_text(relations_content, encoding="utf-8")
            parsed["output_files"].append("characters/relations.mermaid.md")
            parsed["sections"]["relations.mermaid.md"] = relations_content

        if not parsed.get("summary"):
            parsed["summary"] = f"完成角色设计，生成了 {len(parsed['output_files'])} 个文件"

        return parsed

    def _extract_json(self, text: str) -> dict | None:
        """
        从文本中提取 JSON 对象。
        支持多种格式：纯 JSON、```json 代码块、混合文本中的 JSON。
        """
        # 尝试 1: 直接解析整段文本
        text = text.strip()
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        # 尝试 2: 提取 ```json ... ``` 代码块
        json_blocks = re.findall(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
        for block in json_blocks:
            try:
                data = json.loads(block.strip())
                if isinstance(data, dict):
                    # 验证是否包含角色档案特征字段
                    first_val = next(iter(data.values()), None)
                    if isinstance(first_val, dict) and any(
                        k.startswith("group_") for k in first_val.keys()
                    ):
                        return data
                    # 即使没有 group_ 前缀，只要是合理的 dict 也接受
                    if len(data) > 0:
                        return data
            except json.JSONDecodeError:
                continue

        # 尝试 3: 查找最外层 { ... } 匹配
        brace_count = 0
        start = -1
        for i, ch in enumerate(text):
            if ch == '{':
                if brace_count == 0:
                    start = i
                brace_count += 1
            elif ch == '}':
                brace_count -= 1
                if brace_count == 0 and start >= 0:
                    candidate = text[start:i + 1]
                    try:
                        data = json.loads(candidate)
                        if isinstance(data, dict) and len(data) > 0:
                            return data
                    except json.JSONDecodeError:
                        start = -1

        return None

    def _run_split(self, workspace_path: str) -> dict | None:
        """
        调用角色档案拆分脚本。

        Returns:
            拆分结果 dict，失败返回 None
        """
        try:
            from app.tools.split_character_profile import split_character_profile
            result = split_character_profile(workspace_path=workspace_path)
            logger.info(f"角色档案拆分完成: {result.get('summary', '')}")
            return result
        except Exception as e:
            logger.error(f"角色档案拆分失败: {e}")
            return None

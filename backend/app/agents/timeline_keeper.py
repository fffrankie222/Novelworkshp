"""
Timeline Keeper Agent — 时间线管理员
职责：维护故事内部时间线，检测时间矛盾
task_type: light → deepseek-chat (primary)
"""
import logging
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class TimelineKeeperAgent(BaseAgent):
    agent_name = "timeline_keeper"
    prompt_file = "timeline_keeper.md"
    task_type = "light"
    default_temperature = 0.3
    default_max_tokens = 4000

    def build_messages(self, task_input: dict, system_prompt: str) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]
        
        chapter_text = task_input.get("chapter_text", "")
        current_timeline = task_input.get("current_timeline", "")
        chapter_number = task_input.get("chapter_number", 1)
        
        user_content = f"请分析第 {chapter_number} 章，提取时间线事件并检测时间矛盾。\n\n"
        user_content += f"**章节正文**：\n{chapter_text}\n\n"
        user_content += f"**当前时间线**：\n{current_timeline}\n\n"
        user_content += "请完成：\n"
        user_content += "1. 从正文中提取所有时间标记（如'三天后'、'次日清晨'等）\n"
        user_content += "2. 生成新的事件条目（JSON 格式）\n"
        user_content += "3. 检测是否存在时间矛盾（如同一时间出现在不同地点）\n"
        user_content += "4. 输出更新后的时间线\n\n"
        user_content += "输出格式：\n"
        user_content += "{new_events: [...], contradictions: [...], updated_timeline: [...]}\n"
        
        messages.append({"role": "user", "content": user_content})
        return messages

    def parse_response(self, response: str, task_input: dict) -> dict:
        import json
        try:
            json_str = response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            parsed = json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            parsed = {"raw": response}
        
        new_events = parsed.get("new_events", [])
        contradictions = parsed.get("contradictions", [])
        
        return {
            "summary": f"时间线更新：新增 {len(new_events)} 个事件，{len(contradictions)} 个矛盾",
            "parsed_data": parsed,
            "output_file": task_input.get("output_path", ""),
        }

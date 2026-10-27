"""
Humanizer Agent — 去 AI 味专家
职责：对章节正文进行"去 AI 味"润色，检测 36 种 AI 写作模式
task_type: creative_bulk → deepseek-chat (primary), volc-pro (fallback)
"""
import logging
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class HumanizerAgent(BaseAgent):
    agent_name = "humanizer_agent"
    prompt_file = "humanizer_agent.md"
    task_type = "creative_bulk"
    default_temperature = 0.4
    default_max_tokens = 12000

    def build_messages(self, task_input: dict, system_prompt: str) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]
        
        mode = task_input.get("mode", "embedded")
        chapter_text = task_input.get("chapter_text", "")
        style_guide = task_input.get("style_guide", "")
        audit_report = task_input.get("audit_report", "")
        
        if mode == "revise":
            # 根据审核报告修复 + 去 AI 味
            user_content = "请根据审核报告修复关键问题，同时进行去 AI 味润色。\n\n"
            if audit_report:
                user_content += f"**审核报告**：\n{audit_report}\n\n"
            user_content += f"**待润色正文**：\n{chapter_text}\n\n"
            user_content += "要求：\n"
            user_content += "- 逐条处理审核报告中的 critical 和 warning 问题\n"
            user_content += "- 同时检测并修复 36 种 AI 写作模式\n"
            user_content += "- 保持事实守恒，不添加原文没有的信息\n"
            user_content += "- 输出润色后的完整正文\n"
            
        elif mode == "embedded":
            # 检测后直接在原文上修改
            user_content = f"请对以下正文执行去 AI 味润色（Embedded 模式）：\n\n"
            user_content += f"**待润色正文**：\n{chapter_text}\n\n"
            if style_guide:
                user_content += f"**风格指南**：\n{style_guide}\n\n"
            user_content += "要求：\n"
            user_content += "- 检测 36 种 AI 写作模式，直接在原文上修改\n"
            user_content += "- 保持事实守恒\n"
            user_content += "- 打破均匀句长，制造自然的长短交替\n"
            user_content += "- 输出修改后的完整正文\n"
            
        elif mode == "review":
            # 只检测并报告问题，不修改原文
            user_content = f"请对以下正文执行 AI 味检测（Review-only 模式）：\n\n"
            user_content += f"**待检测正文**：\n{chapter_text}\n\n"
            user_content += "请逐一检测 36 种 AI 写作模式，输出检测报告：\n"
            user_content += "{detected_patterns: [{pattern_id, pattern_name, severity, location, description, suggestion}]}\n"
            
        else:
            user_content = task_input.get("task", "请对文本进行去 AI 味处理")
        
        messages.append({"role": "user", "content": user_content})
        return messages

    def parse_response(self, response: str, task_input: dict) -> dict:
        mode = task_input.get("mode", "embedded")
        word_count = len(response.replace("\n", "").replace(" ", ""))
        
        if mode == "review":
            return {
                "summary": "AI 味检测完成",
                "report": response,
                "word_count": word_count,
            }
        else:
            return {
                "summary": f"去 AI 味润色完成，约 {word_count} 字",
                "content": response,
                "word_count": word_count,
                "output_file": task_input.get("output_path", ""),
            }

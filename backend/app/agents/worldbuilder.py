"""
Worldbuilder Agent — 世界构建师
职责：构建和维护世界观设定（地理、政治、魔法/科技体系、历史、社会规则）
task_type: creative_high → 火山引擎 volc-pro (primary)
"""
import logging
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class WorldbuilderAgent(BaseAgent):
    agent_name = "worldbuilder"
    prompt_file = "worldbuilder.md"
    task_type = "creative_high"
    default_temperature = 0.6
    default_max_tokens = 8000

    def build_messages(self, task_input: dict, system_prompt: str) -> list[dict]:
        """构建消息列表"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # 用户输入（题材描述/参考资料）
        genre = task_input.get("genre", "xuanhuan")
        description = task_input.get("description", "")
        reference = task_input.get("reference", "")
        
        user_content = f"请为以下题材构建完整的世界观设定：\n\n"
        user_content += f"**题材类型**：{genre}\n"
        user_content += f"**核心描述**：{description}\n"
        
        if reference:
            user_content += f"\n**参考资料**：\n{reference}\n"
        
        user_content += "\n请生成以下内容：\n"
        user_content += "1. 世界圣经（world_bible.md）— 世界整体框架\n"
        user_content += "2. 力量体系（power_system.md）— 修炼/能力等级体系\n"
        user_content += "3. 地理设定（geography.md）— 世界版图与重要地点\n"
        user_content += "4. 世界规则（rules.md）— 硬性规则与软性约定\n"
        user_content += "\n每个文件请用 markdown 格式输出，用 === 分隔各文件内容。\n"
        
        messages.append({"role": "user", "content": user_content})
        return messages

    def parse_response(self, response: str, task_input: dict) -> dict:
        """解析响应，拆分为多个文件"""
        # 按 === 分隔符拆分
        sections = response.split("===")
        output_files = []
        
        file_names = ["world_bible.md", "power_system.md", "geography.md", "rules.md"]
        parsed = {"output_files": output_files, "sections": {}}
        
        for i, section in enumerate(sections):
            section = section.strip()
            if section and i < len(file_names):
                parsed["sections"][file_names[i]] = section
                output_files.append(file_names[i])
        
        parsed["summary"] = f"完成世界观构建，生成了 {len(parsed['sections'])} 个设定文件"
        return parsed

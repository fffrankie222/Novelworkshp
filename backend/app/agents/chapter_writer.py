"""
Chapter Writer Agent — 章节写手
职责：根据章节纲和上下文，生成正文初稿
task_type: creative_bulk → deepseek-chat (primary), volc-pro (fallback)
支持两种模式：write（创意写作）和 normalize（字数调整）
"""
import logging
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ChapterWriterAgent(BaseAgent):
    agent_name = "chapter_writer"
    prompt_file = "chapter_writer.md"
    task_type = "creative_bulk"
    default_temperature = 0.7  # 创意写作温度偏高
    default_max_tokens = 12000

    def build_messages(self, task_input: dict, system_prompt: str) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]
        
        mode = task_input.get("mode", "write")
        
        if mode == "write":
            # 创意写作模式
            chapter_number = task_input.get("chapter_number", 1)
            chapter_intent = task_input.get("chapter_intent", "")
            context = task_input.get("context_text", "")
            prev_summary = task_input.get("previous_chapter_summary", "")
            target_words = task_input.get("target_words", 3000)
            
            user_content = f"请写第 {chapter_number} 章的正文初稿。\n\n"
            user_content += f"**目标字数**：{target_words} 字（±10%）\n\n"
            
            if chapter_intent:
                user_content += f"**本章意图**：\n{chapter_intent}\n\n"
            if prev_summary:
                user_content += f"**前章摘要**：\n{prev_summary}\n\n"
            if context:
                user_content += f"**上下文信息包**：\n{context}\n\n"
            
            user_content += "请直接输出正文内容，以章节标题开头。\n"
            user_content += "注意：注重文采和情节推进，避免 AI 味，保持风格一致。\n"
            
        elif mode == "normalize":
            # 字数调整模式
            chapter_text = task_input.get("chapter_text", "")
            target_words = task_input.get("target_words", 3000)
            tolerance = task_input.get("tolerance", 0.1)
            
            user_content = f"请调整以下正文的字数到目标范围。\n\n"
            user_content += f"**目标字数**：{target_words} 字（±{int(tolerance*100)}%）\n\n"
            user_content += f"**当前正文**：\n{chapter_text}\n\n"
            user_content += "要求：\n"
            user_content += "- 保持情节和角色行为不变\n"
            user_content += "- 需要扩写时，增加细节描写和感官描写\n"
            user_content += "- 需要缩写时，精简冗余描写，保留关键情节\n"
            
        elif mode == "continue":
            # 续写模式（部分生成中断后继续）
            partial_draft = task_input.get("partial_draft", "")
            target_words = task_input.get("target_words", 3000)
            
            user_content = f"请从以下内容续写，保持风格一致：\n\n"
            user_content += f"**已生成内容**：\n{partial_draft}\n\n"
            user_content += f"**目标总字数**：{target_words} 字\n"
            user_content += "请从中断处继续，保持衔接自然。\n"
        
        elif mode == "write_scene":
            # 单场景写作模式（写作工坊第三步）
            chapter_number = task_input.get("chapter_number", 1)
            scene_data = task_input.get("scene_data", {})
            target_words = task_input.get("target_words", 800)
            context = task_input.get("context", "")
            prev_summary = task_input.get("previous_chapter_summary", "")
            prev_scenes = task_input.get("previous_scenes", "")
            chapter_outline = task_input.get("chapter_outline", "")
            instructions = task_input.get("instructions", "")

            scene_title = scene_data.get("title", "")
            scene_purpose = scene_data.get("purpose", "")
            scene_location = scene_data.get("location", "")
            scene_pov = scene_data.get("pov", "")
            scene_conflict = scene_data.get("conflict", "")
            scene_outcome = scene_data.get("outcome", "")
            scene_emotion = scene_data.get("emotional_beat", "")

            user_content = f"请写第 {chapter_number} 章中的一个场景。\n\n"
            user_content += f"**场景标题**：{scene_title}\n"
            user_content += f"**目标字数**：{target_words} 字（±10%）\n"
            user_content += f"**POV角色**：{scene_pov}\n"
            user_content += f"**地点**：{scene_location}\n"
            user_content += f"**场景目标**：{scene_purpose}\n"
            user_content += f"**核心冲突**：{scene_conflict}\n"
            user_content += f"**结局走向**：{scene_outcome}\n"
            user_content += f"**情绪基调**：{scene_emotion}\n\n"

            if prev_summary:
                user_content += f"**上一章摘要**：\n{prev_summary}\n\n"
            if prev_scenes:
                user_content += f"**本章已写场景（作为衔接参考）**：\n{prev_scenes}\n\n"
            if context:
                user_content += f"**世界观与角色设定**：\n{context}\n\n"
            if chapter_outline:
                user_content += f"**本章大纲**：\n{chapter_outline}\n\n"
            if instructions:
                user_content += f"**用户补充指令**：\n{instructions}\n\n"

            user_content += "请直接输出场景正文内容。\n"
            user_content += "注意：\n"
            user_content += "- 以场景标题（### 开头）作为第一行\n"
            user_content += "- 注重场景的完整起承转合\n"
            user_content += "- 用动作和对话推动情节，减少直述\n"
            user_content += "- 结尾自然过渡到下一个场景（如果不是最后一个场景）\n"
            user_content += "- 严格遵守写作技法和反AI味规则\n"

        else:
            user_content = task_input.get("task", "请写一章小说")
        
        messages.append({"role": "user", "content": user_content})
        return messages

    def parse_response(self, response: str, task_input: dict) -> dict:
        # 统计字数
        word_count = len(response.replace("\n", "").replace(" ", ""))
        
        return {
            "summary": f"完成章节写作，约 {word_count} 字",
            "word_count": word_count,
            "content": response,
            "output_file": task_input.get("output_path", ""),
        }

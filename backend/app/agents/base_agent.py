"""
BaseAgent — 所有 Agent 的抽象基类
提供 system prompt 加载、占位符注入、LLM 调用封装、NodeResult 输出等通用能力
"""
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Any

from app.models.workflow import NodeResult
from app.llm.router import get_model_router

logger = logging.getLogger(__name__)

# prompts 目录路径
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class BaseAgent(ABC):
    """
    Agent 抽象基类。每个子类代表一个专用 Agent。
    
    职责：
    1. 从 prompts/*.md 加载 system prompt
    2. 支持 {{placeholder}} 占位符运行时注入
    3. 封装 LLM 调用（通过 ModelRouter 自动选模型）
    4. 统一输出为 NodeResult 结构
    """

    # 子类必须设置
    agent_name: str = ""          # 如 "worldbuilder"
    prompt_file: str = ""         # 如 "worldbuilder.md"
    task_type: str = "light"      # 对应的模型任务类型
    
    # 可选配置
    default_temperature: float = 0.5
    default_max_tokens: int = 8000

    def __init__(self):
        self._system_prompt_template: Optional[str] = None
        self._router = get_model_router()
        self._load_prompt()

    def _load_prompt(self):
        """从 prompts/ 目录加载 system prompt 模板"""
        prompt_path = PROMPTS_DIR / self.prompt_file
        if prompt_path.exists():
            self._system_prompt_template = prompt_path.read_text(encoding="utf-8")
            logger.info(f"Agent [{self.agent_name}] 加载 prompt: {self.prompt_file}")
        else:
            logger.warning(f"Agent [{self.agent_name}] prompt 文件不存在: {prompt_path}")
            self._system_prompt_template = f"你是一个名为 {self.agent_name} 的网文写作助手。"

    def build_system_prompt(self, **kwargs) -> str:
        """
        构建最终的 system prompt，替换所有 {{placeholder}} 占位符。
        
        支持的占位符（由 kwargs 传入）：
        - {{writing_rules_section}} — 写作规则
        - {{character_constraints_section}} — 角色约束
        - {{world_rules_section}} — 世界规则
        - {{genre_conventions_section}} — 类型惯例
        - {{current_state_section}} — 当前状态
        其他自定义占位符也可通过 kwargs 传入。
        """
        if not self._system_prompt_template:
            self._load_prompt()

        prompt = self._system_prompt_template or ""

        # 替换所有占位符
        for key, value in kwargs.items():
            placeholder = "{{" + key + "}}"
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, str(value))

        # 将未替换的占位符替换为空字符串（避免模型看到占位符标记）
        import re
        prompt = re.sub(r"\{\{[a-z_]+\}\}", "", prompt)

        return prompt.strip()

    @abstractmethod
    def build_messages(self, task_input: dict, system_prompt: str) -> list[dict]:
        """
        构建发送给 LLM 的消息列表。
        子类必须实现此方法，根据 task_input 组装 messages。
        
        Args:
            task_input: 任务输入参数
            system_prompt: 已构建好的 system prompt
        Returns:
            [{"role": "system/user/assistant", "content": "..."}, ...]
        """
        pass

    @abstractmethod
    def parse_response(self, response: str, task_input: dict) -> dict:
        """
        解析 LLM 响应，提取结构化输出。
        子类必须实现此方法。
        
        Args:
            response: LLM 返回的文本
            task_input: 原始任务输入（可用于上下文）
        Returns:
            结构化输出字典
        """
        pass

    async def run(self, task_input: dict, **prompt_kwargs) -> NodeResult:
        """
        Agent 主执行入口。
        
        流程：
        1. 构建 system prompt（注入占位符）
        2. 构建 messages
        3. 通过 ModelRouter 调用 LLM（含 fallback）
        4. 解析响应
        5. 包装为 NodeResult 返回
        
        Args:
            task_input: 任务输入
            **prompt_kwargs: 传给 build_system_prompt 的占位符参数
        Returns:
            NodeResult
        """
        start_time = time.time()
        node_id = task_input.get("node_id", self.agent_name)

        try:
            # 1. 构建 system prompt
            system_prompt = self.build_system_prompt(**prompt_kwargs)

            # 2. 构建 messages
            messages = self.build_messages(task_input, system_prompt)

            # 3. 通过 ModelRouter 调用（带 fallback）
            logger.info(f"Agent [{self.agent_name}] 开始执行任务: {task_input.get('task', '未命名')}")
            
            response, model_used = await self._router.call_with_fallback(
                messages=messages,
                task_type=self.task_type,
                temperature=self.default_temperature,
                max_tokens=self.default_max_tokens,
            )

            # 4. 解析响应
            parsed = self.parse_response(response, task_input)

            # 5. 处理输出文件（如果有）
            output_files = parsed.get("output_files", [])
            if parsed.get("output_file"):
                output_files.append(parsed["output_file"])

            duration = time.time() - start_time

            logger.info(
                f"Agent [{self.agent_name}] 任务完成 | "
                f"模型={model_used} | "
                f"耗时={duration:.1f}s"
            )

            return NodeResult(
                node_id=node_id,
                agent=self.agent_name,
                status="success",
                summary=parsed.get("summary", f"{self.agent_name} 任务完成"),
                output_files=output_files,
                metadata={
                    "model_used": model_used,
                    "duration_seconds": round(duration, 2),
                    "task_type": self.task_type,
                    "word_count": parsed.get("word_count", 0),
                    "degraded": "/" in model_used and not model_used.startswith(
                        self._router.get_primary_model(self.task_type)[0]
                    ),
                },
                started_at="",  # 可补充
                completed_at="",
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Agent [{self.agent_name}] 任务失败 | "
                f"耗时={duration:.1f}s | 错误={str(e)[:300]}"
            )
            return NodeResult(
                node_id=node_id,
                agent=self.agent_name,
                status="failed",
                summary=f"{self.agent_name} 执行失败: {str(e)[:200]}",
                metadata={
                    "duration_seconds": round(duration, 2),
                    "task_type": self.task_type,
                },
                error=str(e),
            )

    async def run_json(self, task_input: dict, **prompt_kwargs) -> NodeResult:
        """
        执行任务并要求 LLM 返回 JSON 格式。
        用于需要结构化输出的场景（如 Observer 事实提取、Reflector delta 生成）。
        """
        start_time = time.time()
        node_id = task_input.get("node_id", self.agent_name)

        try:
            system_prompt = self.build_system_prompt(**prompt_kwargs)
            messages = self.build_messages(task_input, system_prompt)

            # 确保 system prompt 中包含 JSON 输出要求
            messages.insert(0, {
                "role": "system",
                "content": system_prompt + "\n\n【重要】请以纯 JSON 格式输出结果，不要包含其他文字。"
            })

            parsed_json, model_used = await self._router.call_with_fallback_json(
                messages=messages[1:],  # 去掉刚插入的 system（chat_json 内部会处理）
                task_type=self.task_type,
                temperature=self.default_temperature,
                max_tokens=self.default_max_tokens,
            )

            duration = time.time() - start_time

            return NodeResult(
                node_id=node_id,
                agent=self.agent_name,
                status="success",
                summary=parsed_json.get("summary", f"{self.agent_name} JSON 任务完成"),
                output_files=parsed_json.get("output_files", []),
                metadata={
                    "model_used": model_used,
                    "duration_seconds": round(duration, 2),
                    "task_type": self.task_type,
                    "json_output": parsed_json,
                },
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Agent [{self.agent_name}] JSON 任务失败: {str(e)[:300]}")
            return NodeResult(
                node_id=node_id,
                agent=self.agent_name,
                status="failed",
                summary=f"{self.agent_name} JSON 任务失败: {str(e)[:200]}",
                error=str(e),
                metadata={"duration_seconds": round(duration, 2)},
            )

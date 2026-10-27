"""
LLM 统一客户端 — 基于 OpenAI SDK 的封装
支持重试、指数退避、温度调整、fallback 等机制
"""
import asyncio
import logging
import time
from typing import Optional

from openai import AsyncOpenAI

from config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """统一 LLM 客户端，封装 OpenAI 兼容协议的调用"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str = "deepseek-chat",
        max_retries: int = 3,
        backoff_base: int = 2,
        temperature_adjustments: Optional[list[float]] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        # 每次重试时叠加到 temperature 上的增量
        self.temperature_adjustments = temperature_adjustments or [0.0, 0.1, 0.2]

        # 创建 OpenAI 异步客户端
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=180.0,
            max_retries=0,  # 我们自己管理重试
        )

    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
    ) -> str:
        """
        发送聊天请求，返回文本响应。
        内置重试逻辑：指数退避 + 温度递增。
        
        Args:
            messages: 消息列表 [{"role": "user/assistant/system", "content": "..."}]
            model: 模型名称，不传则用默认
            temperature: 采样温度，不传则用配置默认值
            max_tokens: 最大输出 token 数
            system: 可选的系统消息，会插入到 messages 最前面
        
        Returns:
            模型响应的文本内容
        """
        _model = model or self.default_model
        settings = get_settings()
        _temperature = temperature if temperature is not None else settings.default_temperature
        _max_tokens = max_tokens or settings.default_max_tokens

        # 如果有 system 参数，插入到消息列表开头
        if system:
            messages = [{"role": "system", "content": system}] + list(messages)

        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                # 重试时调整温度（增加随机性以突破生成卡死）
                temp_adjust = 0.0
                if attempt < len(self.temperature_adjustments):
                    temp_adjust = self.temperature_adjustments[attempt]
                effective_temp = min(_temperature + temp_adjust, 1.5)

                logger.info(
                    f"LLM 调用 [模型={_model}, 尝试={attempt + 1}, "
                    f"温度={effective_temp:.2f}, max_tokens={_max_tokens}]"
                )

                response = await self._client.chat.completions.create(
                    model=_model,
                    messages=messages,
                    temperature=effective_temp,
                    max_tokens=_max_tokens,
                )

                content = response.choices[0].message.content
                if not content or not content.strip():
                    raise ValueError("模型返回空响应")

                logger.info(
                    f"LLM 响应成功 [模型={_model}, tokens={response.usage.total_tokens if response.usage else '?'}]"
                )
                return content.strip()

            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                logger.warning(
                    f"LLM 调用失败 [模型={_model}, 尝试={attempt + 1}/{self.max_retries + 1}, "
                    f"错误类型={error_type}, 错误={str(e)[:200]}]"
                )

                # 最后一次尝试不再等待
                if attempt < self.max_retries:
                    wait_time = self.backoff_base ** (attempt + 1)
                    logger.info(f"等待 {wait_time}s 后重试...")
                    await asyncio.sleep(wait_time)

        # 所有重试都失败了
        raise LLMError(
            f"LLM 调用失败，已重试 {self.max_retries + 1} 次。最后错误: {last_error}",
            model=_model,
            original_error=last_error,
        )

    async def chat_json(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """
        发送聊天请求并解析 JSON 响应。
        如果响应不是合法 JSON，触发重试。
        """
        import json

        for attempt in range(self.max_retries + 1):
            try:
                content = await self.chat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                # 尝试从响应中提取 JSON
                # 有时模型会在 JSON 前后加上 ```json ... ``` 标记
                json_str = content
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0]

                result = json.loads(json_str.strip())
                return result

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"JSON 解析失败 [尝试={attempt + 1}]: {str(e)[:200]}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.backoff_base ** (attempt + 1))
                continue

        raise LLMError(
            f"JSON 解析失败，已重试 {self.max_retries + 1} 次",
            model=model or self.default_model,
        )

    async def close(self):
        """关闭客户端连接"""
        await self._client.close()


class LLMError(Exception):
    """LLM 调用异常"""

    def __init__(self, message: str, model: str = "", original_error: Optional[Exception] = None):
        super().__init__(message)
        self.model = model
        self.original_error = original_error


def create_deepseek_client(**kwargs) -> LLMClient:
    """创建 DeepSeek 客户端的工厂函数"""
    settings = get_settings()
    return LLMClient(
        api_key=kwargs.get("api_key", settings.deepseek_api_key),
        base_url=kwargs.get("base_url", settings.deepseek_base_url),
        default_model=kwargs.get("model", settings.deepseek_model),
        max_retries=kwargs.get("max_retries", settings.max_retries),
        backoff_base=kwargs.get("backoff_base", settings.retry_backoff_base),
    )


def create_volcano_client(**kwargs) -> LLMClient:
    """创建火山引擎客户端的工厂函数（当前欠费不可用）"""
    settings = get_settings()
    return LLMClient(
        api_key=kwargs.get("api_key", settings.volcano_api_key),
        base_url=kwargs.get("base_url", settings.volcano_base_url),
        default_model=kwargs.get("model", "doubao-pro-32k"),
        max_retries=kwargs.get("max_retries", settings.max_retries),
        backoff_base=kwargs.get("backoff_base", settings.retry_backoff_base),
    )

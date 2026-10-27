"""
ModelRouter — 根据 task_type 选择模型，支持 fallback 链
读取 config/model_config.json 配置，为每个 Agent 自动选择合适的模型

双 Provider 路由：
  - volcano (volc-pro): 推理/创意能力强，适合高阶创意、推理、对话
  - deepseek (deepseek-chat): 性价比高，适合大量文本生成

火山引擎特殊处理：model_config 中用逻辑名 volc-pro，调用时自动转换为 endpoint_id。
"""
import json
import logging
from pathlib import Path
from typing import Optional

from config.settings import get_settings
from app.llm.client import LLMClient, LLMError, create_deepseek_client

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    模型路由器 — 根据任务类型选择最优模型
    支持 fallback 链：primary → fallback_1 → fallback_2
    """

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = str(Path(__file__).resolve().parent.parent.parent / "config" / "model_config.json")

        with open(config_path, "r", encoding="utf-8") as f:
            self._config = json.load(f)

        # 缓存的客户端实例（key = provider:model）
        self._clients: dict[str, LLMClient] = {}

        # agent → task_type 的映射
        self._agent_task_map: dict[str, str] = self._config.get("agent_task_type_mapping", {})

        # task_type 配置
        self._task_types: dict = self._config.get("task_types", {})

        # provider 配置
        self._providers: dict = self._config.get("providers", {})

        logger.info(
            f"ModelRouter 初始化完成 | "
            f"{len(self._task_types)} 种任务类型 | "
            f"{len(self._providers)} 个 Provider | "
            f"火山引擎: {'可用' if self._providers.get('volcano', {}).get('enabled') else '不可用'}"
        )

    def get_task_type(self, agent_name: str) -> str:
        """获取 Agent 对应的 task_type"""
        task_type = self._agent_task_map.get(agent_name, "light")
        return task_type

    def get_model_config(self, task_type: str) -> dict:
        """获取指定 task_type 的模型配置（primary + fallbacks）"""
        return self._task_types.get(task_type, self._task_types.get("light", {}))

    def _resolve_model_for_call(self, provider_name: str, model_name: str) -> str:
        """
        将逻辑模型名解析为实际调用时的 model 参数。
        
        火山引擎特殊处理：volc-pro → endpoint_id
        DeepSeek 直接透传：deepseek-chat → deepseek-chat
        """
        if provider_name == "volcano":
            # 火山引擎：逻辑名 → endpoint_id
            from app.llm.volcano import get_endpoint_id
            try:
                endpoint_id = get_endpoint_id(model_name)
                logger.debug(f"火山引擎模型解析: {model_name} → {endpoint_id}")
                return endpoint_id
            except ValueError as e:
                logger.error(f"火山引擎模型解析失败: {e}")
                raise LLMError(f"火山引擎模型不可用: {model_name} - {e}", model=model_name)
        else:
            # DeepSeek 等其他 provider 直接透传
            return model_name

    def get_client(self, provider_name: str) -> LLMClient:
        """获取或创建指定 provider 的客户端实例"""
        if provider_name in self._clients:
            return self._clients[provider_name]

        provider_config = self._providers.get(provider_name, {})

        # 检查 provider 是否启用
        if not provider_config.get("enabled", False):
            raise LLMError(f"Provider '{provider_name}' 未启用", model="")

        if provider_name == "deepseek":
            client = create_deepseek_client()
        elif provider_name == "volcano":
            from app.llm.client import create_volcano_client
            client = create_volcano_client()
        else:
            logger.warning(f"未知 provider '{provider_name}'，回退到 deepseek")
            client = create_deepseek_client()

        self._clients[provider_name] = client
        return client

    def get_primary_model(self, task_type: str) -> tuple[str, str]:
        """获取 task_type 对应的主模型，返回 (provider_name, model_name)"""
        config = self.get_model_config(task_type)
        primary = config.get("primary", {"provider": "deepseek", "model": "deepseek-chat"})
        return primary["provider"], primary["model"]

    def get_fallback_chain(self, task_type: str) -> list[tuple[str, str]]:
        """
        获取完整的 fallback 链，返回 [(provider, model), ...]
        顺序：primary → fallback_1 → fallback_2
        相邻重复项会被跳过（如 fallback_2 和 primary 相同时）
        """
        config = self.get_model_config(task_type)
        chain = []

        for key in ["primary", "fallback_1", "fallback_2"]:
            entry = config.get(key)
            if entry:
                provider = entry.get("provider", "deepseek")
                model = entry.get("model", "deepseek-chat")
                
                # 检查 provider 是否启用
                provider_config = self._providers.get(provider, {})
                if not provider_config.get("enabled", True):
                    logger.debug(f"跳过不可用 provider: {provider}/{model}")
                    continue
                
                chain.append((provider, model))

        # 去重：连续相同的 (provider, model) 只保留第一次出现
        deduped_chain = []
        prev = None
        for item in chain:
            if item != prev:
                deduped_chain.append(item)
            prev = item

        return deduped_chain

    async def call_with_fallback(
        self,
        messages: list[dict],
        task_type: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, str]:
        """
        带 fallback 的 LLM 调用。
        依次尝试 primary → fallback_1 → fallback_2，
        返回 (response_text, model_used)。
        
        火山引擎的 model 参数会自动从逻辑名（volc-pro）转换为 endpoint_id。
        
        Raises:
            LLMError: 所有模型都失败时抛出
        """
        fallback_chain = self.get_fallback_chain(task_type)

        if not fallback_chain:
            fallback_chain = [("deepseek", "deepseek-chat")]

        last_error: Optional[Exception] = None

        for provider_name, model_name in fallback_chain:
            try:
                client = self.get_client(provider_name)
                # 将逻辑模型名转换为实际调用参数
                actual_model = self._resolve_model_for_call(provider_name, model_name)
                
                response = await client.chat(
                    messages=messages,
                    model=actual_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                # 如果不是主模型，记录降级事件
                primary_provider, primary_model = fallback_chain[0]
                if (provider_name, model_name) != (primary_provider, primary_model):
                    logger.warning(
                        f"模型降级: {primary_provider}/{primary_model} → "
                        f"{provider_name}/{model_name} (task_type={task_type})"
                    )

                return response, f"{provider_name}/{model_name}"

            except (LLMError, Exception) as e:
                last_error = e
                logger.warning(
                    f"模型 {provider_name}/{model_name} 调用失败，"
                    f"尝试下一个 fallback: {str(e)[:200]}"
                )
                continue

        raise LLMError(
            f"所有模型均调用失败 (task_type={task_type}, "
            f"尝试了: {[f'{p}/{m}' for p, m in fallback_chain]})",
            model=fallback_chain[-1][1] if fallback_chain else "unknown",
            original_error=last_error,
        )

    async def call_with_fallback_json(
        self,
        messages: list[dict],
        task_type: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> tuple[dict, str]:
        """
        带 fallback 的 JSON LLM 调用。
        返回 (parsed_json, model_used)。
        """
        fallback_chain = self.get_fallback_chain(task_type)

        if not fallback_chain:
            fallback_chain = [("deepseek", "deepseek-chat")]

        last_error: Optional[Exception] = None

        for provider_name, model_name in fallback_chain:
            try:
                client = self.get_client(provider_name)
                actual_model = self._resolve_model_for_call(provider_name, model_name)
                
                result = await client.chat_json(
                    messages=messages,
                    model=actual_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return result, f"{provider_name}/{model_name}"

            except (LLMError, Exception) as e:
                last_error = e
                logger.warning(f"模型 {provider_name}/{model_name} JSON 调用失败: {str(e)[:200]}")
                continue

        raise LLMError(
            f"所有模型 JSON 调用均失败 (task_type={task_type})",
            model=fallback_chain[-1][1] if fallback_chain else "unknown",
            original_error=last_error,
        )

    def get_model_info_summary(self) -> dict:
        """获取当前模型配置的摘要信息（用于 API 展示）"""
        summary = {
            "providers": {},
            "task_types": {},
        }

        # Provider 信息
        for name, config in self._providers.items():
            summary["providers"][name] = {
                "name": config.get("name", name),
                "enabled": config.get("enabled", False),
                "models": list(config.get("models", {}).keys()),
            }

        # task_type 路由信息
        for task_type, config in self._task_types.items():
            primary = config.get("primary", {})
            summary["task_types"][task_type] = {
                "description": config.get("description", ""),
                "primary": f"{primary.get('provider', '')}:{primary.get('model', '')}",
                "fallbacks": [
                    f"{config.get(f'fallback_{i}', {}).get('provider', '')}:"
                    f"{config.get(f'fallback_{i}', {}).get('model', '')}"
                    for i in [1, 2]
                    if config.get(f"fallback_{i}")
                ],
            }

        # Agent 映射
        summary["agent_mapping"] = dict(self._agent_task_map)

        return summary


# 全局单例
_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """获取全局 ModelRouter 单例"""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router

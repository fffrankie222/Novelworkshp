"""
DeepSeek Provider — DeepSeek API 特定配置
DeepSeek 兼容 OpenAI 协议，所以核心调用走 LLMClient 即可
此文件仅做 DeepSeek 特定的适配和扩展
"""
import logging
from app.llm.client import LLMClient, create_deepseek_client

logger = logging.getLogger(__name__)

# DeepSeek 模型能力配置
DEEPSEEK_MODELS = {
    "deepseek-chat": {
        "name": "DeepSeek Chat (V3)",
        "context_window": 64000,
        "max_output_tokens": 8192,
        "supports_json": True,
        "supports_stream": True,
    },
    "deepseek-reasoner": {
        "name": "DeepSeek Reasoner (R1)",
        "context_window": 64000,
        "max_output_tokens": 8192,
        "supports_json": True,
        "supports_stream": True,
    },
}


def get_deepseek_client(model: str = "deepseek-chat") -> LLMClient:
    """获取 DeepSeek 客户端实例"""
    return create_deepseek_client(model=model)


def get_model_info(model_name: str) -> dict:
    """获取模型信息"""
    return DEEPSEEK_MODELS.get(model_name, {
        "name": model_name,
        "context_window": 32000,
        "max_output_tokens": 4096,
        "supports_json": False,
        "supports_stream": True,
    })

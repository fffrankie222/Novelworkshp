"""
火山引擎 Provider — 豆包系列模型完整实现

火山引擎使用 OpenAI 兼容协议，但 model 参数需要传推理接入点 ID（endpoint_id）。
endpoint_id 属于部署侧敏感配置，统一从环境变量 / config/.env 读取
（settings.volcano_pro_endpoint，对应 VOLCANO_PRO_ENDPOINT），源码不内置真实值。
"""
import logging

from config.settings import get_settings
from app.llm.client import LLMClient, create_volcano_client

logger = logging.getLogger(__name__)


def _get_volc_pro_endpoint() -> str:
    """从配置（环境变量/.env）读取豆包 Pro 推理接入点 ID，未配置时返回空串。"""
    try:
        return get_settings().volcano_pro_endpoint or ""
    except Exception:
        return ""


# 火山引擎模型配置 — endpoint_id 运行时从配置读取，不在源码硬编码
VOLCANO_MODELS = {
    "volc-pro": {
        "name": "豆包 Pro 32K",
        "endpoint_id": _get_volc_pro_endpoint(),  # model 参数实际要传的值，来自 VOLCANO_PRO_ENDPOINT
        "context_window": 32000,
        "max_output_tokens": 4096,
        "enabled": True,
        "description": "推理和创意能力强，适合高阶创意、推理、对话任务",
    },
}


def is_volcano_available() -> bool:
    """检查火山引擎是否可用"""
    return any(m.get("enabled", False) for m in VOLCANO_MODELS.values())


def get_endpoint_id(model_name: str) -> str:
    """
    获取火山引擎推理接入点 ID。
    火山引擎的 model 参数必须传 endpoint_id，不是模型名称。
    
    Args:
        model_name: 逻辑模型名，如 "volc-pro"
    Returns:
        endpoint_id，形如 "ep-xxxxxxxx"（来自环境变量 VOLCANO_PRO_ENDPOINT）
    """
    model_info = VOLCANO_MODELS.get(model_name)
    if not model_info:
        raise ValueError(f"未知的火山引擎模型: {model_name}，可选: {list(VOLCANO_MODELS.keys())}")
    
    endpoint_id = model_info.get("endpoint_id")
    if not endpoint_id:
        raise ValueError(
            f"模型 {model_name} 未配置 endpoint_id：请在 config/.env 中设置 VOLCANO_PRO_ENDPOINT"
            f"（参考 config/.env.example）"
        )
    
    if not model_info.get("enabled", False):
        raise ValueError(f"模型 {model_name} 当前未启用")
    
    return endpoint_id


def get_volcano_client(model: str = "volc-pro") -> LLMClient:
    """
    获取火山引擎客户端实例。
    model 参数为逻辑名称（如 volc-pro），调用时自动转换为 endpoint_id。
    """
    if not is_volcano_available():
        raise RuntimeError("火山引擎当前不可用，请检查配置")
    
    # 获取实际的 endpoint_id
    endpoint_id = get_endpoint_id(model)
    logger.info(f"创建火山引擎客户端: {model} → endpoint_id={endpoint_id}")
    
    return create_volcano_client(model=endpoint_id)


def get_model_info(model_name: str) -> dict:
    """获取火山引擎模型信息"""
    return VOLCANO_MODELS.get(model_name, {
        "name": model_name,
        "endpoint_id": "",
        "context_window": 32000,
        "max_output_tokens": 4096,
        "enabled": False,
    })


def list_available_models() -> list[str]:
    """列出所有可用的火山引擎模型（逻辑名称）"""
    return [name for name, info in VOLCANO_MODELS.items() if info.get("enabled", False)]

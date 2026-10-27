"""
全局配置管理 — 基于 Pydantic BaseSettings，读取 .env 文件
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用全局配置"""

    # 项目基础路径
    base_dir: str = Field(default=str(Path(__file__).resolve().parent.parent))

    # DeepSeek API 配置（密钥仅从环境变量 / config/.env 读取，源码不内置任何真实密钥）
    deepseek_api_key: str = Field(default="")
    deepseek_base_url: str = Field(default="https://api.deepseek.com/v1")
    deepseek_model: str = Field(default="deepseek-chat")

    # 火山引擎 API 配置（密钥与推理接入点 ID 仅从环境变量 / config/.env 读取）
    volcano_api_key: str = Field(default="")
    volcano_base_url: str = Field(default="https://ark.cn-beijing.volces.com/api/v3")
    volcano_pro_endpoint: str = Field(default="")  # 火山推理接入点 endpoint_id，如 ep-xxxxxxxx

    # 数据目录
    data_dir: str = Field(default="data")

    # LLM 全局默认配置
    default_temperature: float = Field(default=0.7)
    default_max_tokens: int = Field(default=8000)
    max_retries: int = Field(default=3)
    retry_backoff_base: int = Field(default=2)

    # 上下文管理
    context_budget_tokens: int = Field(default=10500)
    summary_max_tokens: int = Field(default=1000)
    recent_chapter_max_tokens: int = Field(default=2000)

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


_settings: Settings | None = None


def get_settings() -> Settings:
    """获取单例配置"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

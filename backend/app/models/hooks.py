"""
伏笔账本数据模型
"""
from typing import Optional
from pydantic import BaseModel, Field


class HookStatus:
    """伏笔状态枚举"""
    PLANTED = "planted"
    ACTIVE = "active"
    ADVANCING = "advancing"
    RESOLVING = "resolving"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"


class Hook(BaseModel):
    """单条伏笔"""
    id: str
    description: str
    status: str = "planted"
    planted_in: str = ""  # 埋入的章节
    planted_at: str = ""  # 时间戳
    target_resolution: str = ""  # 目标回收位置（如 volume_2）
    last_advanced: str = ""  # 最后推进的章节
    mentions: list[str] = Field(default_factory=list)  # 提及过的章节列表
    priority: str = "medium"  # high / medium / low
    tags: list[str] = Field(default_factory=list)


class HookHealth(BaseModel):
    """伏笔健康度报告"""
    red_alerts: list[str] = Field(default_factory=list)
    yellow_alerts: list[str] = Field(default_factory=list)
    over_mentioned: list[str] = Field(default_factory=list)
    healthy: list[str] = Field(default_factory=list)


class HookLedger(BaseModel):
    """伏笔账本"""
    hooks: list[Hook] = Field(default_factory=list)
    status_enum: dict[str, str] = Field(default_factory=lambda: {
        "planted": "刚埋下",
        "active": "已激活，读者已知",
        "advancing": "正在推进中",
        "resolving": "即将揭晓",
        "resolved": "已回收",
        "abandoned": "已废弃（需标注原因）"
    })

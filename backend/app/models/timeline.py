"""
时间线数据模型
"""
from typing import Optional
from pydantic import BaseModel, Field


class TimeSystem(BaseModel):
    """时间系统定义"""
    type: str = "fictional_calendar"  # fictional_calendar / real_world / relative
    calendar_name: str = ""
    notes: str = ""


class TimelineEvent(BaseModel):
    """时间线事件"""
    id: str
    chapter: str  # 来源章节
    absolute_time: str = ""  # 绝对时间（如 天玄历1024年三月初三）
    relative_time: str = ""  # 相对时间（如 故事开始后第3天）
    description: str = ""
    location: str = ""
    characters_involved: list[str] = Field(default_factory=list)
    consequences: list[str] = Field(default_factory=list)


class Timeline(BaseModel):
    """时间线"""
    events: list[TimelineEvent] = Field(default_factory=list)
    time_system: Optional[TimeSystem] = None

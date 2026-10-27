"""
世界观数据模型
"""
from typing import Optional
from pydantic import BaseModel, Field


class WorldRule(BaseModel):
    """世界规则"""
    id: str
    category: str  # power_system / geography / social / magic / technology
    rule: str
    is_hard: bool = True  # 硬规则/软规则
    description: str = ""
    chapter_applicable: str = "all"


class WorldBible(BaseModel):
    """世界圣经"""
    book_id: str
    genre: str = ""
    world_bible_md: str = ""  # world_bible.md 的内容
    power_system_md: str = ""
    geography_md: str = ""
    rules_md: str = ""
    rules: list[WorldRule] = Field(default_factory=list)


class WorldState(BaseModel):
    """当前世界状态（可随剧情变化）"""
    faction_relations: dict[str, str] = Field(default_factory=dict)
    active_events: list[str] = Field(default_factory=list)
    power_balance: str = ""
    last_updated: str = ""

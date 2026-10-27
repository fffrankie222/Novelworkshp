"""
角色数据模型
"""
from typing import Optional
from pydantic import BaseModel, Field


class CharacterState(BaseModel):
    """角色当前状态"""
    location: str = ""
    cultivation_level: str = ""
    hp: str = "healthy"
    emotional_state: str = ""
    known_secrets: list[str] = Field(default_factory=list)
    inventory: list[str] = Field(default_factory=list)
    relationships: dict[str, str] = Field(default_factory=dict)
    last_updated: str = ""


class Relationship(BaseModel):
    """角色关系"""
    source: str
    target: str
    relation_type: str  # ally / enemy / mentor / rival / neutral
    description: str = ""
    strength: float = 0.5  # 0-1, 关系强度
    updated_in: str = ""  # 最后更新的章节


class Character(BaseModel):
    """角色主模型"""
    name: str
    book_id: str
    role: str = "supporting"  # protagonist / supporting / antagonist / minor
    description: str = ""
    profile_path: str = ""
    state: Optional[CharacterState] = None
    # 14 组字段的精简引用
    core_identity: str = ""
    speech_style: str = ""
    signature_phrases: list[str] = Field(default_factory=list)
    arc_trajectory: str = ""
    ooc_red_lines: list[str] = Field(default_factory=list)

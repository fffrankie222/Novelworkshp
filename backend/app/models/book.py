"""
书籍数据模型
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BookConfig(BaseModel):
    """书籍配置"""
    book_id: str
    book_title: str
    genre: str = "xuanhuan"  # 题材：xuanhuan/xianxia/urban/scifi/horror
    target_words_per_chapter: int = 3000
    total_target_chapters: int = 100

    # 风格配置
    narrative_pov: str = "third_person_limited"  # 叙事视角
    narrative_tense: str = "past"  # 叙事时态
    tone_tags: list[str] = Field(default_factory=lambda: ["轻松幽默", "热血燃向"])
    language_level: str = "通俗白话，少量文言用语点缀"
    forbidden_patterns: list[str] = Field(default_factory=list)
    preferred_techniques: list[str] = Field(default_factory=list)

    # 角色规则
    character_hard_constraints: list[dict] = Field(default_factory=list)
    character_soft_preferences: list[dict] = Field(default_factory=list)

    # 世界规则
    world_hard_constraints: list[dict] = Field(default_factory=list)
    world_soft_constraints: list[dict] = Field(default_factory=list)

    # 类型惯例
    reader_expectations: list[str] = Field(default_factory=list)
    max_consecutive_calm_chapters: int = 2
    required_hooks_per_chapter: int = 1
    chapter_end_must_have_hook: bool = True


class Book(BaseModel):
    """书籍主模型"""
    book_id: str
    title: str
    genre: str = "xuanhuan"
    description: str = ""
    status: str = "draft"  # draft / writing / completed / archived
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_chapters: int = 0
    current_chapter: int = 0
    config: Optional[BookConfig] = None
    workspace_path: str = ""

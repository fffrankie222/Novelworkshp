"""
章节数据模型
"""
from typing import Optional
from pydantic import BaseModel, Field


class ChapterStatus(str):
    """章节状态枚举"""
    PLANNED = "planned"
    DRAFTING = "drafting"
    DRAFTED = "drafted"
    REVIEWING = "reviewing"
    REVISION = "revision"
    FINALIZED = "finalized"
    EXPORTED = "exported"


class ChapterSummary(BaseModel):
    """章节摘要"""
    chapter: str
    title: str = ""
    word_count: int = 0
    summary: str = ""
    character_changes: list[dict] = Field(default_factory=list)
    new_facts: list[str] = Field(default_factory=list)
    hook_changes: list[dict] = Field(default_factory=list)
    timeline_event: Optional[dict] = None
    tone: str = ""
    pov_character: str = ""


class Chapter(BaseModel):
    """章节模型"""
    chapter_id: str  # 如 chapter-0001
    book_id: str
    chapter_number: int
    title: str = ""
    status: str = "planned"
    word_count: int = 0
    target_words: int = 3000
    outline: str = ""  # 章节细纲内容
    draft_path: str = ""
    final_path: str = ""
    summary: Optional[ChapterSummary] = None
    created_at: str = ""
    updated_at: str = ""
    audit_retry_count: int = 0
    model_used: str = ""
    degraded: bool = False  # 是否使用了备用模型

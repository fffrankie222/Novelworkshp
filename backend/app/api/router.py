"""
API 路由汇总
"""
from fastapi import APIRouter

from app.api.books import router as books_router
from app.api.workflows import router as workflows_router
from app.api.approvals import router as approvals_router
from app.api.agents import router as agents_router
from app.api.chapters import router as chapters_router
from app.api.world import router as world_router
from app.api.characters import router as characters_router
from app.api.outline import router as outline_router
from app.api.hooks import router as hooks_router
from app.api.timeline import router as timeline_router
from app.api.chat import router as chat_router
from app.api.writing_workshop import router as workshop_router

api_router = APIRouter()

api_router.include_router(books_router, prefix="/books", tags=["书籍管理"])
api_router.include_router(workflows_router, tags=["工作流"])
api_router.include_router(approvals_router, tags=["审批"])
api_router.include_router(agents_router, prefix="/agents", tags=["Agent"])
api_router.include_router(chapters_router, tags=["章节"])
api_router.include_router(world_router, prefix="/books", tags=["世界观"])
api_router.include_router(characters_router, prefix="/books", tags=["角色"])
api_router.include_router(outline_router, prefix="/books", tags=["大纲"])
api_router.include_router(hooks_router, prefix="/books", tags=["伏笔"])
api_router.include_router(timeline_router, prefix="/books", tags=["时间线"])
api_router.include_router(chat_router, prefix="/books", tags=["对话"])
api_router.include_router(workshop_router, prefix="/books", tags=["写作工坊"])

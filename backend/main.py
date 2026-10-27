"""
NovelWorkshop 后端入口 — FastAPI 应用
启动命令: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
import os
import sys

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from app.api.router import api_router

settings = get_settings()

app = FastAPI(
    title="NovelWorkshop",
    description="网文写作多 Agent 系统后端服务",
    version="0.1.0",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "NovelWorkshop"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

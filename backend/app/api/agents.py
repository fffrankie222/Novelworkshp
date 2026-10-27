"""
Agent 状态查询 API
"""
import logging

from fastapi import APIRouter

from app.llm.router import get_model_router

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("")
async def list_agents():
    """列出所有 Agent 及其配置"""
    agents = [
        {
            "name": "worldbuilder",
            "display_name": "世界构建师",
            "task_type": "creative_high",
            "description": "构建世界观设定：地理、政治、魔法体系、历史、社会规则",
        },
        {
            "name": "char_designer",
            "display_name": "角色设计师",
            "task_type": "creative_high",
            "description": "人物创建、蒸馏、关系图谱维护、角色弧线设计",
        },
        {
            "name": "plot_architect",
            "display_name": "情节架构师",
            "task_type": "reasoning",
            "description": "故事大纲、章节规划、伏笔管理、节奏控制",
        },
        {
            "name": "chapter_writer",
            "display_name": "章节写手",
            "task_type": "creative_bulk",
            "description": "根据章节纲和上下文生成正文初稿",
        },
        {
            "name": "consistency_checker",
            "display_name": "一致性审核员",
            "task_type": "reasoning",
            "description": "检查章节与世界设定、角色状态、时间线的一致性（支持 observer/reflector/auditor 三种模式）",
        },
        {
            "name": "humanizer_agent",
            "display_name": "去AI味专家",
            "task_type": "creative_bulk",
            "description": "对章节正文进行去AI味润色，检测36种AI写作模式",
        },
        {
            "name": "timeline_keeper",
            "display_name": "时间线管理员",
            "task_type": "light",
            "description": "维护故事内部时间线，检测时间矛盾",
        },
        {
            "name": "main_agent",
            "display_name": "主控Agent",
            "task_type": "reasoning",
            "description": "接收用户指令，协调其他Agent，汇报进度",
        },
    ]
    
    # 补充模型路由信息
    router_instance = get_model_router()
    for agent in agents:
        task_type = agent["task_type"]
        primary_provider, primary_model = router_instance.get_primary_model(task_type)
        agent["primary_model"] = f"{primary_provider}/{primary_model}"
        fallback_chain = router_instance.get_fallback_chain(task_type)
        agent["fallback_chain"] = [f"{p}/{m}" for p, m in fallback_chain]
    
    return {"agents": agents, "total": len(agents)}


@router.get("/model-config")
async def get_model_config():
    """获取当前模型分级配置"""
    router_instance = get_model_router()
    return router_instance.get_model_info_summary()

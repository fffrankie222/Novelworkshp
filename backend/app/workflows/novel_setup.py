"""
novel-setup Workflow — 新书建立流程
worldbuilder → char-designer → plot-architect → approval
"""
import logging
import time
from pathlib import Path

from app.workflows.engine import WorkflowEngine, WorkflowNode
from app.agents.worldbuilder import WorldbuilderAgent
from app.agents.char_designer import CharDesignerAgent
from app.agents.plot_architect import PlotArchitectAgent

logger = logging.getLogger(__name__)


def build_novel_setup_nodes(genre: str = "xuanhuan", description: str = "",
                            character_ideas: list = None, book_id: str = "") -> list[WorkflowNode]:
    """
    构建新书建立工作流的节点列表。
    独立为函数，供 resume_workflow 重建节点结构时使用。

    Args:
        genre: 题材类型
        description: 故事描述
        character_ideas: 角色初始想法
        book_id: 书籍 ID
    Returns:
        节点列表
    """
    worldbuilder = WorldbuilderAgent()
    char_designer = CharDesignerAgent()
    plot_architect = PlotArchitectAgent()

    return [
        # 节点 1: 世界构建
        WorkflowNode(
            node_id="build_world",
            node_type="agent",
            handler=worldbuilder,
            config={"genre": genre, "description": description},
        ),
        # 节点 2: 角色设计
        WorkflowNode(
            node_id="design_characters",
            node_type="agent",
            handler=char_designer,
            config={
                "sub_task": "create",
                "characters": character_ideas or [],
            },
        ),
        # 节点 3: 情节规划
        WorkflowNode(
            node_id="create_outline",
            node_type="agent",
            handler=plot_architect,
            config={"sub_task": "outline", "genre": genre},
        ),
        # 节点 4: 用户确认（真实审批，暂停等待）
        WorkflowNode(
            node_id="approval",
            node_type="approval",
            config={
                "description": "请审阅世界观设定、角色档案和故事大纲，确认或提出修改意见",
                "artifact_sources": [
                    {
                        "key": "worldbuilding_output",
                        "label": "世界观设定",
                        "files": [
                            "world/WORLD.md",
                            "world/RULES.md",
                            "world/FACTIONS.md",
                        ],
                    },
                    {
                        "key": "character_design_output",
                        "label": "角色档案",
                        "files": [
                            "characters/PROFILE.md",
                            "characters/PROFILE.json",
                            "characters/relations.mermaid.md",
                        ],
                    },
                    {
                        "key": "outline_output",
                        "label": "故事大纲",
                        "files": [
                            "outline/OUTLINE.md",
                        ],
                    },
                ],
            },
        ),
    ]


async def run_novel_setup(
    workspace_path: str,
    book_id: str,
    genre: str,
    description: str,
    character_ideas: list[dict] = None,
) -> dict:
    """
    执行新书建立工作流。

    Args:
        workspace_path: 书籍工作区路径
        book_id: 书籍 ID
        genre: 题材类型
        description: 用户的故事描述
        character_ideas: 用户初步的角色想法
    Returns:
        执行结果（status 可能为 waiting_approval 表示暂停等待审批）
    """
    ws = Path(workspace_path)
    engine = WorkflowEngine(workspace_path)

    nodes = build_novel_setup_nodes(
        genre=genre,
        description=description,
        character_ideas=character_ideas,
        book_id=book_id,
    )

    workflow_id = f"novel-setup-{book_id}-{int(time.time())}"

    # 执行（到达 approval 节点时会暂停返回 waiting_approval）
    state = await engine.execute_workflow(
        workflow_id=workflow_id,
        workflow_type="novel-setup",
        book_id=book_id,
        nodes=nodes,
        initial_context={
            "book_id": book_id,
            "genre": genre,
            "description": description,
            "workspace_path": workspace_path,
        },
    )

    result = {
        "workflow_id": workflow_id,
        "status": state.status,
        "nodes": {k: v.dict() for k, v in state.nodes.items()},
    }

    # 如果暂停等待审批，附加审批信息
    if state.status == "waiting_approval" and state.pending_approval:
        result["pending_approval"] = state.pending_approval.dict()

    return result

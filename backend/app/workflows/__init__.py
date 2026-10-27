"""
Workflow 引擎模块

注意：各流程（novel_setup / chapter_production / revision / character_import）
对外提供 build_*_nodes() 节点构建函数与 run_*() 异步入口，而非以 *Workflow 类形式存在。
旧版 __init__ 曾 import 不存在的 NovelSetupWorkflow 等类名，导致
`import app.workflows.engine` 时触发包 __init__ 的 ImportError（approvals 工作流状态
扫描会因此静默失败）。已修正为真实导出的符号（R3 配套修复）。
"""
from app.workflows.engine import WorkflowEngine
from app.workflows.novel_setup import build_novel_setup_nodes, run_novel_setup
from app.workflows.chapter_production import build_chapter_production_nodes, run_chapter_production
from app.workflows.revision import build_revision_nodes, run_revision
from app.workflows.character_import import build_character_import_nodes, run_character_import

__all__ = [
    "WorkflowEngine",
    "build_novel_setup_nodes",
    "run_novel_setup",
    "build_chapter_production_nodes",
    "run_chapter_production",
    "build_revision_nodes",
    "run_revision",
    "build_character_import_nodes",
    "run_character_import",
]

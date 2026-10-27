"""
Workflow Engine — 轻量级工作流引擎
支持顺序执行、条件分支、循环、checkpoint 保存/恢复
新增：审批流程真实化 + 工作流状态持久化到磁盘
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional, Any, Callable

from app.models.workflow import WorkflowState, NodeResult, NodeStatus, Checkpoint, PendingApproval

logger = logging.getLogger(__name__)


class WorkflowNode:
    """工作流节点定义"""

    def __init__(
        self,
        node_id: str,
        node_type: str,  # "agent" | "script" | "condition" | "approval"
        handler: Any = None,  # Agent 实例或 callable
        config: dict = None,
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.handler = handler
        self.config = config or {}


class WorkflowEngine:
    """
    轻量级工作流引擎。

    特性：
    - 顺序执行节点
    - 条件分支（condition 节点根据结果路由）
    - 循环（audit → revise → audit 最多 N 次）
    - checkpoint 保存/恢复
    - 失败时从最近的 checkpoint 恢复
    - 【新增】审批流程真实化：approval 节点暂停等待用户审阅
    - 【新增】工作流状态持久化到磁盘（runtime/workflows/{workflow_id}.json）
    """

    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self._workflows: dict[str, WorkflowState] = {}
        # 确保持久化目录存在
        self._workflows_dir = self.workspace_path / "runtime" / "workflows"
        self._workflows_dir.mkdir(parents=True, exist_ok=True)
        self._approvals_dir = self.workspace_path / "runtime" / "approvals"
        self._approvals_dir.mkdir(parents=True, exist_ok=True)
        # 启动时从磁盘恢复已有工作流状态
        self._restore_from_disk()

    # ============================================================
    # 持久化相关方法
    # ============================================================

    def _restore_from_disk(self):
        """启动时从磁盘恢复工作流状态到内存"""
        if not self._workflows_dir.exists():
            return
        for fp in self._workflows_dir.glob("*.json"):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                state = WorkflowState(**data)
                self._workflows[state.workflow_id] = state
                logger.info(f"从磁盘恢复工作流: {state.workflow_id} (status={state.status})")
            except Exception as e:
                logger.warning(f"恢复工作流失败 {fp}: {e}")

    def _persist_state(self, state: WorkflowState):
        """将工作流状态写入磁盘"""
        state.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        fp = self._workflows_dir / f"{state.workflow_id}.json"
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(state.dict(), f, ensure_ascii=False, indent=2)
        logger.debug(f"工作流状态已持久化: {fp}")

    def _load_state_from_disk(self, workflow_id: str) -> Optional[WorkflowState]:
        """从磁盘加载单个工作流状态"""
        fp = self._workflows_dir / f"{workflow_id}.json"
        if fp.exists():
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return WorkflowState(**data)
            except Exception as e:
                logger.warning(f"加载工作流 {workflow_id} 失败: {e}")
        return None

    # ============================================================
    # 工作流执行
    # ============================================================

    async def execute_workflow(
        self,
        workflow_id: str,
        workflow_type: str,
        book_id: str,
        nodes: list[WorkflowNode],
        initial_context: dict = None,
        max_loop_count: int = 3,
        on_progress: Optional[Callable] = None,
    ) -> WorkflowState:
        """
        执行工作流。
        如果到达 approval 节点则暂停并返回 waiting_approval 状态。

        Args:
            workflow_id: 工作流唯一标识
            workflow_type: 工作流类型
            book_id: 关联的书籍 ID
            nodes: 节点列表（按顺序）
            initial_context: 初始上下文数据
            max_loop_count: 循环最大次数（审核循环）
            on_progress: 进度回调函数
        Returns:
            WorkflowState
        """
        # 初始化或恢复工作流状态
        state = self._workflows.get(workflow_id)
        if state and state.status in ("running", "waiting_approval"):
            logger.info(f"恢复工作流 {workflow_id}，从节点 {state.current_node} 继续")
        else:
            state = WorkflowState(
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                book_id=book_id,
                status="running",
                current_node=nodes[0].node_id if nodes else "",
            )
            self._workflows[workflow_id] = state
            self._persist_state(state)

        context = initial_context or {}
        # 构建节点映射
        node_map = {n.node_id: n for n in nodes}

        # 确定起始节点索引
        start_idx = 0
        if state.current_node:
            for i, n in enumerate(nodes):
                if n.node_id == state.current_node:
                    start_idx = i
                    break

        # 从 start_idx 开始执行
        return await self._execute_from(
            state, nodes, start_idx, context, max_loop_count, on_progress
        )

    async def _execute_from(
        self,
        state: WorkflowState,
        nodes: list[WorkflowNode],
        start_idx: int,
        context: dict,
        max_loop_count: int,
        on_progress: Optional[Callable],
    ) -> WorkflowState:
        """
        从指定索引开始执行工作流节点。
        遇到 approval 节点时暂停并返回。

        Args:
            state: 当前工作流状态
            nodes: 全部节点列表
            start_idx: 起始索引
            context: 工作流上下文
            max_loop_count: 最大循环次数
            on_progress: 进度回调
        Returns:
            WorkflowState（可能是 completed 或 waiting_approval）
        """
        loop_count = state.loop_count or 0
        i = start_idx

        while i < len(nodes):
            node = nodes[i]
            state.current_node = node.node_id

            # 检查是否已有成功 checkpoint（恢复模式下跳过已完成节点）
            checkpoint = self._load_checkpoint(state.workflow_id, node.node_id)
            if checkpoint and checkpoint.status == "success":
                logger.info(f"节点 {node.node_id} 已有 checkpoint，跳过")
                if checkpoint.output:
                    context.update(checkpoint.output)
                i += 1
                continue

            # 创建节点结果
            node_result = NodeResult(node_id=node.node_id, status="running")
            state.nodes[node.node_id] = node_result

            try:
                logger.info(f"执行节点: {node.node_id} (类型={node.node_type})")

                if node.node_type == "agent":
                    await self._execute_agent_node(node, node_result, context)

                elif node.node_type == "script":
                    await self._execute_script_node(node, node_result, context)

                elif node.node_type == "condition":
                    loop_count = await self._execute_condition_node(
                        node, node_result, context, state, loop_count, max_loop_count, nodes
                    )
                    # 条件节点可能改变了 i（循环跳转），需要检查
                    if state.current_node != node.node_id:
                        # current_node 被 condition 修改了，重新查找索引
                        for j, n in enumerate(nodes):
                            if n.node_id == state.current_node:
                                i = j
                                break
                        self._persist_state(state)
                        continue
                    # 未跳转时 i 不变，继续下面的逻辑
                    # 但 condition 执行完后需要 continue 以避免 i += 1
                    self._save_checkpoint(state.workflow_id, node.node_id, node_result, context)
                    if on_progress:
                        await on_progress(state.workflow_id, node.node_id, node_result)
                    self._persist_state(state)
                    i += 1
                    continue

                elif node.node_type == "approval":
                    # ★ 审批节点：暂停等待用户确认（不再自动通过）
                    result = await self._handle_approval_node(
                        state, node, context, nodes, i
                    )
                    if result is not None:
                        # 返回非 None 表示工作流已暂停等待审批
                        self._persist_state(state)
                        return result

                # 保存 checkpoint
                self._save_checkpoint(state.workflow_id, node.node_id, node_result, context)

                # 进度回调
                if on_progress:
                    await on_progress(state.workflow_id, node.node_id, node_result)

                # 如果节点失败
                if node_result.status == "failed":
                    state.status = "failed"
                    state.error = node_result.error
                    logger.error(f"节点 {node.node_id} 执行失败: {node_result.error}")

                    # 尝试从最近的 checkpoint 恢复
                    recovered = await self._try_recover(state, nodes, i, context)
                    if recovered:
                        self._persist_state(state)
                        continue
                    else:
                        self._persist_state(state)
                        break

                i += 1

            except Exception as e:
                node_result.status = "failed"
                node_result.error = str(e)
                state.status = "failed"
                state.error = str(e)
                logger.error(f"节点 {node.node_id} 异常: {str(e)[:300]}")
                self._persist_state(state)
                break

        # 更新最终状态
        if state.status == "running":
            state.status = "completed"

        state.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._persist_state(state)

        logger.info(f"工作流 {state.workflow_id} 执行完成: status={state.status}")
        return state

    # ============================================================
    # 各类型节点执行方法
    # ============================================================

    async def _execute_agent_node(self, node: WorkflowNode, node_result: NodeResult, context: dict):
        """执行 Agent 类型节点"""
        task_input = {**context, "node_id": node.node_id}
        task_input.update(node.config)

        result = await node.handler.run(task_input)
        node_result.status = result.status
        node_result.summary = result.summary
        node_result.output_files = result.output_files
        node_result.metadata = result.metadata
        node_result.error = result.error

        # 将结果合并到上下文
        if result.metadata:
            context.update(result.metadata)
            if "json_output" in result.metadata:
                context.update(result.metadata["json_output"])

    async def _execute_script_node(self, node: WorkflowNode, node_result: NodeResult, context: dict):
        """执行 Script 类型节点"""
        script_fn = node.handler
        result = await script_fn(context, node.config)
        node_result.status = "success"
        node_result.summary = result.get("summary", "脚本执行完成")
        context.update(result)

    async def _execute_condition_node(
        self,
        node: WorkflowNode,
        node_result: NodeResult,
        context: dict,
        state: WorkflowState,
        loop_count: int,
        max_loop_count: int,
        nodes: list[WorkflowNode],
    ) -> int:
        """
        执行 Condition 类型节点。
        返回更新后的 loop_count。如果触发循环，会修改 state.current_node。
        """
        condition_fn = node.config.get("condition_fn")
        if condition_fn:
            should_loop = condition_fn(context, loop_count, max_loop_count)
            if should_loop:
                loop_count += 1
                state.loop_count = loop_count
                logger.info(f"条件触发循环: {node.node_id} → 回到审核节点 (第{loop_count}次)")
                target_id = node.config.get("true_target", "")
                state.current_node = target_id
            else:
                logger.info(f"条件不满足，跳出循环，继续下一节点")

        node_result.status = "success"
        node_result.summary = f"条件判断完成 (循环次数={loop_count})"
        return loop_count

    async def _handle_approval_node(
        self,
        state: WorkflowState,
        node: WorkflowNode,
        context: dict,
        nodes: list[WorkflowNode],
        current_idx: int,
    ) -> Optional[WorkflowState]:
        """
        处理审批节点：保存审批产物、设置 waiting_approval 状态、暂停执行。

        Returns:
            WorkflowState — 暂停状态的工作流（供 execute_workflow / resume 返回）
            None — 理论上不会到达（始终返回暂停状态）
        """
        # 找到上一个 agent 节点（驳回时的回退目标）
        prev_agent_node = ""
        for j in range(current_idx - 1, -1, -1):
            if nodes[j].node_type == "agent":
                prev_agent_node = nodes[j].node_id
                break

        # 保存审批产物文件
        artifact_path = self._save_approval_artifact(state, node, context)

        # 记录待审批信息
        state.pending_approval = PendingApproval(
            node_id=node.node_id,
            artifact_path=artifact_path,
            waiting_since=time.strftime("%Y-%m-%dT%H:%M:%S"),
            prev_agent_node=prev_agent_node,
            description=node.config.get("description", "请审阅以上产物"),
        )

        # 标记当前节点为 waiting_approval
        node_result = state.nodes.get(node.node_id)
        if node_result:
            node_result.status = NodeStatus.WAITING_APPROVAL
            node_result.summary = "等待用户审批"

        # 设置工作流整体状态为 waiting_approval
        state.status = "waiting_approval"

        logger.info(
            f"工作流 {state.workflow_id} 在节点 {node.node_id} 暂停等待审批, "
            f"产物路径: {artifact_path}"
        )
        return state

    def _save_approval_artifact(
        self, state: WorkflowState, node: WorkflowNode, context: dict
    ) -> str:
        """
        保存审批产物到 runtime/approvals/{workflow_id}_{node_id}.json

        产物内容包括：
        - 节点配置中指定的 artifact_sources 对应的上下文数据
        - 产物文件的文本内容（自动读取）

        Returns:
            产物文件的相对路径
        """
        artifact = {
            "workflow_id": state.workflow_id,
            "workflow_type": state.workflow_type,
            "book_id": state.book_id,
            "node_id": node.node_id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "description": node.config.get("description", "请审阅以上产物"),
            "sources": {},
            "files_content": {},
        }

        # 从 context 收集指定的产物源数据
        for src in node.config.get("artifact_sources", []):
            key = src.get("key", "")
            label = src.get("label", key)
            if key in context:
                artifact["sources"][label] = context[key]

        # 收集产物文件的实际文本内容（供前端预览）
        workspace_path = context.get("workspace_path", self.workspace_path)
        for src in node.config.get("artifact_sources", []):
            for fp in src.get("files", []):
                full_path = Path(workspace_path) / fp
                if full_path.exists():
                    try:
                        text = full_path.read_text(encoding="utf-8")
                        # 截断过长内容（单个文件最多保留 20000 字符）
                        artifact["files_content"][fp] = (
                            text if len(text) <= 20000 else text[:20000] + "\n... [内容已截断]"
                        )
                    except Exception:
                        pass

        # 写入磁盘
        fp = self._approvals_dir / f"{state.workflow_id}_{node.node_id}.json"
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(artifact, f, ensure_ascii=False, indent=2)

        logger.info(f"审批产物已保存: {fp}")
        # 返回相对路径
        return str(fp.relative_to(self.workspace_path))

    # ============================================================
    # 审批恢复
    # ============================================================

    async def resume_workflow(
        self,
        workflow_id: str,
        approved: bool,
        feedback: str = "",
        modifications: dict = None,
    ) -> Optional[WorkflowState]:
        """
        恢复等待审批的工作流。

        Args:
            workflow_id: 工作流 ID
            approved: True=通过, False=驳回
            feedback: 用户反馈意见
            modifications: 用户直接修改的产物内容（审批时修改）
        Returns:
            WorkflowState，找不到则返回 None
        """
        state = self._workflows.get(workflow_id)
        if not state:
            state = self._load_state_from_disk(workflow_id)
            if state:
                self._workflows[workflow_id] = state
            else:
                return None

        if state.status != "waiting_approval":
            logger.warning(f"工作流 {workflow_id} 当前状态为 {state.status}，非 waiting_approval")
            return state

        if not state.pending_approval:
            logger.warning(f"工作流 {workflow_id} 无待审批记录")
            return state

        approval_node_id = state.pending_approval.node_id
        logger.info(
            f"审批结果: workflow={workflow_id}, node={approval_node_id}, "
            f"approved={approved}, feedback={feedback[:100]}"
        )

        if approved:
            # ★ 通过审批：如果有用户修改则先应用，然后继续执行下一个节点
            if modifications:
                self._apply_modifications(state, modifications)

            # 标记审批节点为成功
            node_result = state.nodes.get(approval_node_id)
            if node_result:
                node_result.status = "success"
                node_result.summary = f"用户审批通过。反馈: {feedback}" if feedback else "用户审批通过"

            # 清除待审批状态
            state.pending_approval = None
            state.status = "running"
            self._persist_state(state)

            # 找到审批节点索引，从下一个节点继续
            nodes = self._rebuild_node_list(state)
            approval_idx = -1
            for idx, n in enumerate(nodes):
                if n.node_id == approval_node_id:
                    approval_idx = idx
                    break

            if approval_idx >= 0 and approval_idx + 1 < len(nodes):
                context = self._load_context(state.workflow_id)
                return await self._execute_from(
                    state, nodes, approval_idx + 1, context,
                    max_loop_count=3, on_progress=None
                )
            else:
                state.status = "completed"
                self._persist_state(state)
                return state

        else:
            # ★ 驳回审批：回退到上一个 agent 节点重新执行
            if modifications:
                self._apply_modifications(state, modifications)

            rollback_target = state.pending_approval.prev_agent_node or ""

            # 清除审批节点的 checkpoint 和状态
            self._clear_checkpoint(state.workflow_id, approval_node_id)
            if approval_node_id in state.nodes:
                del state.nodes[approval_node_id]

            state.pending_approval = None
            state.status = "running"
            state.error = f"用户驳回: {feedback}" if feedback else "用户驳回"
            self._persist_state(state)

            # 从回退目标节点重新执行
            if rollback_target:
                nodes = self._rebuild_node_list(state)
                target_idx = -1
                for idx, n in enumerate(nodes):
                    if n.node_id == rollback_target:
                        target_idx = idx
                        break

                if target_idx >= 0:
                    context = self._load_context(state.workflow_id)
                    context["user_feedback"] = feedback
                    return await self._execute_from(
                        state, nodes, target_idx, context,
                        max_loop_count=3, on_progress=None
                    )

            state.status = "failed"
            self._persist_state(state)
            return state

    # ============================================================
    # 辅助方法
    # ============================================================

    def _apply_modifications(self, state: WorkflowState, modifications: dict):
        """
        将用户在审批时提交的修改应用到工作区文件。
        modifications 格式: {"relative/file/path.md": "新的文件内容", ...}
        """
        workspace_path = self.workspace_path
        for rel_path, content in modifications.items():
            full_path = workspace_path / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            logger.info(f"用户修改已应用: {rel_path}")

    def _rebuild_node_list(self, state: WorkflowState) -> list[WorkflowNode]:
        """
        根据工作流类型重建节点列表（仅含结构信息，不含 handler）。
        用于 resume 时定位节点索引。
        """
        # 动态导入工作流定义以获取节点结构
        try:
            if state.workflow_type == "novel-setup":
                from app.workflows.novel_setup import build_novel_setup_nodes
                return build_novel_setup_nodes(
                    genre=state.nodes.get("build_world", NodeResult(node_id="")).metadata.get("genre", "xuanhuan"),
                    book_id=state.book_id,
                )
            elif state.workflow_type == "chapter-production":
                from app.workflows.chapter_production import build_chapter_production_nodes
                return build_chapter_production_nodes(
                    book_id=state.book_id,
                    chapter_number=1,
                )
            elif state.workflow_type == "revision":
                from app.workflows.revision import build_revision_nodes
                return build_revision_nodes()
            elif state.workflow_type == "character-import":
                from app.workflows.character_import import build_character_import_nodes
                return build_character_import_nodes()
        except Exception as e:
            logger.warning(f"重建节点列表失败: {e}")

        # fallback: 仅用已知的节点 ID 构建空壳节点
        return [WorkflowNode(node_id=nid, node_type="agent") for nid in state.nodes.keys()]

    def _load_context(self, workflow_id: str) -> dict:
        """从最新 checkpoint 加载上下文"""
        checkpoint_dir = self.workspace_path / "runtime" / f"checkpoint-{workflow_id}"
        if not checkpoint_dir.exists():
            return {}

        context = {}
        # 按文件修改时间排序，加载所有 checkpoint
        checkpoints = sorted(checkpoint_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        for cp_file in checkpoints:
            try:
                with open(cp_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("output"):
                    context.update(data["output"])
            except Exception:
                pass
        return context

    # ============================================================
    # Checkpoint 管理
    # ============================================================

    def _save_checkpoint(self, workflow_id: str, node_id: str, result: NodeResult, context: dict):
        """保存节点 checkpoint"""
        checkpoint_dir = self.workspace_path / "runtime" / f"checkpoint-{workflow_id}"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            "node_id": node_id,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "status": result.status,
            "output": {k: v for k, v in context.items() if isinstance(v, (str, int, float, bool, list, dict))},
            "result_summary": result.summary,
            "can_resume_from": result.status == "success",
        }

        checkpoint_file = checkpoint_dir / f"{node_id}.json"
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)

        logger.debug(f"Checkpoint 保存: {checkpoint_file}")

    def _load_checkpoint(self, workflow_id: str, node_id: str) -> Optional[Checkpoint]:
        """加载节点 checkpoint"""
        checkpoint_file = self.workspace_path / "runtime" / f"checkpoint-{workflow_id}" / f"{node_id}.json"

        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("can_resume_from", False):
                    return Checkpoint(
                        node_id=data["node_id"],
                        completed_at=data.get("completed_at", ""),
                        status=data.get("status", "success"),
                        output=data.get("output", {}),
                        can_resume_from=True,
                    )
            except Exception as e:
                logger.warning(f"Checkpoint 加载失败: {e}")

        return None

    def _clear_checkpoint(self, workflow_id: str, node_id: str):
        """清除指定节点的 checkpoint（驳回时使用）"""
        checkpoint_file = self.workspace_path / "runtime" / f"checkpoint-{workflow_id}" / f"{node_id}.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info(f"Checkpoint 已清除: {checkpoint_file}")

    async def _try_recover(
        self, state: WorkflowState, nodes: list[WorkflowNode], failed_idx: int, context: dict
    ) -> bool:
        """尝试从最近的 checkpoint 恢复"""
        for i in range(failed_idx - 1, -1, -1):
            checkpoint = self._load_checkpoint(state.workflow_id, nodes[i].node_id)
            if checkpoint and checkpoint.can_resume_from:
                logger.info(f"从 checkpoint 恢复: 节点 {nodes[i].node_id}")
                state.current_node = nodes[i + 1].node_id
                state.status = "running"
                return True
        return False

    # ============================================================
    # 状态查询
    # ============================================================

    def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """获取工作流状态（先查内存，再从磁盘）"""
        state = self._workflows.get(workflow_id)
        if state:
            return state
        # 尝试从磁盘加载
        state = self._load_state_from_disk(workflow_id)
        if state:
            self._workflows[workflow_id] = state
        return state

    def list_workflows(self) -> list[WorkflowState]:
        """列出所有工作流（合并内存 + 磁盘扫描）"""
        # 先扫描磁盘补充
        self._restore_from_disk()
        return list(self._workflows.values())

    def get_approval_info(self, workflow_id: str) -> Optional[dict]:
        """获取工作流当前待审批的详细信息"""
        state = self.get_workflow_state(workflow_id)
        if not state or not state.pending_approval:
            return None

        artifact_path = self.workspace_path / state.pending_approval.artifact_path
        artifact_data = {}
        if artifact_path.exists():
            try:
                with open(artifact_path, "r", encoding="utf-8") as f:
                    artifact_data = json.load(f)
            except Exception:
                pass

        return {
            "workflow_id": workflow_id,
            "workflow_type": state.workflow_type,
            "book_id": state.book_id,
            "node_id": state.pending_approval.node_id,
            "waiting_since": state.pending_approval.waiting_since,
            "prev_agent_node": state.pending_approval.prev_agent_node,
            "description": state.pending_approval.description,
            "artifact": artifact_data,
        }

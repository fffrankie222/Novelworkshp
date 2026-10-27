import type { WorkflowState, NodeResult } from '../types'
import { Check, Loader2 } from 'lucide-react'

interface WorkflowProgressProps {
  workflow: WorkflowState
}

const STATUS_MAP: Record<string, { label: string; className: string }> = {
  pending: { label: '等待中', className: 'nw-badge' },
  running: { label: '进行中', className: 'nw-badge nw-badge-info' },
  completed: { label: '已完成', className: 'nw-badge nw-badge-success' },
  failed: { label: '失败', className: 'nw-badge nw-badge-error' },
  waiting_approval: { label: '等待审批', className: 'nw-badge nw-badge-warning' },
}

const NODE_LABELS: Record<string, string> = {
  plan: '章节规划',
  compose: '上下文组装',
  write: '正文生成',
  observe: '事实提取',
  reflect: '状态更新',
  apply_state: '应用状态',
  normalize: '字数调整',
  audit: '20维审核',
  check_audit: '审核判断',
  revise: '修订',
  approval: '用户审批',
  done: '定稿',
  build_world: '世界构建',
  design_characters: '角色设计',
  create_outline: '情节规划',
  humanize: '润色',
  split_text: '文本分割',
  distill: '蒸馏',
  merge: '合并',
  export_graph: '导出关系图',
}

export default function WorkflowProgress({ workflow }: WorkflowProgressProps) {
  const status = STATUS_MAP[workflow.status] || STATUS_MAP.pending
  
  // Convert nodes record to array
  const nodesArray = Object.values(workflow.nodes || {})
  const totalNodes = nodesArray.length
  const completedNodes = nodesArray.filter((n) => n.status === 'success').length
  
  const progress = totalNodes > 0 ? (completedNodes / totalNodes) * 100 : 0

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-medium text-white">工作流进度</h4>
          <p className="text-[11px] text-nw-text-muted mt-0.5">
            {workflow.workflow_type === 'chapter-production' && '章节生产流程'}
            {workflow.workflow_type === 'novel-setup' && '新书建立流程'}
            {workflow.workflow_type === 'revision' && '修订润色流程'}
          </p>
        </div>
        <span className={status.className}>{status.label}</span>
      </div>

      {/* Progress bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] text-nw-text-muted uppercase tracking-wider">
            进度
          </span>
          <span className="text-[11px] font-mono text-white">
            {completedNodes} / {totalNodes}
          </span>
        </div>
        <div className="w-full h-px bg-nw-border relative">
          <div
            className="absolute top-0 left-0 h-px bg-white transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Nodes */}
      <div className="space-y-1">
        {nodesArray.map((node: NodeResult, i) => {
          const isCompleted = node.status === 'success'
          const isRunning = node.status === 'running'
          const isPending = node.status === 'pending'

          return (
            <div
              key={node.node_id}
              className={`flex items-center gap-3 py-2 px-2 border transition-all ${
                isRunning
                  ? 'border-white/30 bg-white/5'
                  : 'border-transparent'
              }`}
            >
              {/* Node icon */}
              <div className="w-4 h-4 flex items-center justify-center shrink-0">
                {isCompleted && (
                  <div className="w-3 h-3 border border-nw-success flex items-center justify-center">
                    <Check className="w-2 h-2 text-nw-success" strokeWidth={3} />
                  </div>
                )}
                {isRunning && (
                  <Loader2
                    className="w-3.5 h-3.5 text-white animate-spin"
                    strokeWidth={1.5}
                  />
                )}
                {isPending && (
                  <div className="w-2.5 h-2.5 border border-nw-border-light" />
                )}
              </div>

              {/* Node name */}
              <span
                className={`text-xs flex-1 ${
                  isCompleted
                    ? 'text-nw-text-secondary'
                    : isRunning
                      ? 'text-white'
                      : 'text-nw-text-muted'
                }`}
              >
                {NODE_LABELS[node.node_id] || node.node_id}
              </span>

              {/* Node summary */}
              {node.summary && (
                <span className="text-[10px] text-nw-text-muted font-mono shrink-0 max-w-[120px] truncate">
                  {node.summary}
                </span>
              )}

              {/* Node number */}
              <span className="text-[10px] text-nw-text-muted font-mono w-6 text-right">
                {String(i + 1).padStart(2, '0')}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

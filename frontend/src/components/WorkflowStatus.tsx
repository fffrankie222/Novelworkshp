import { useState } from 'react'
import { Check, Loader2, AlertTriangle, Clock } from 'lucide-react'
import type { WorkflowState, NodeResult } from '../types'
import { useStore } from '../store'
import ApprovalPanel from './ApprovalPanel'

interface WorkflowStatusProps {
  workflow: WorkflowState
  showApproval?: boolean
}

const WORKFLOW_TYPE_LABELS: Record<string, string> = {
  'chapter-production': '章节生产流程',
  'novel-setup': '新书建立流程',
  'revision': '修订润色流程',
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

export default function WorkflowStatus({ workflow, showApproval = true }: WorkflowStatusProps) {
  const { approvalData, fetchApproval } = useStore()
  const [approvalPanelOpen, setApprovalPanelOpen] = useState(false)

  // Convert nodes record to array
  const nodeEntries = Object.entries(workflow.nodes || {})
  const nodesArray: NodeResult[] = nodeEntries.map(([, node]) => node)
  const totalNodes = nodeEntries.length
  const completedNodes = nodesArray.filter((n) => n.status === 'success').length

  const progress = totalNodes > 0
    ? (completedNodes / totalNodes) * 100
    : 0

  const isWaitingApproval = workflow.status === 'waiting_approval'

  const handleApprovalNodeClick = () => {
    setApprovalPanelOpen(!approvalPanelOpen)
    if (!approvalPanelOpen && !approvalData) {
      fetchApproval(workflow.workflow_id)
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-medium text-white">工作流进度</h4>
          <p className="text-[11px] text-nw-text-muted mt-0.5">
            {WORKFLOW_TYPE_LABELS[workflow.workflow_type] || workflow.workflow_type}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isWaitingApproval && (
            <span className="nw-badge nw-badge-warning flex items-center gap-1">
              <AlertTriangle className="w-2.5 h-2.5" strokeWidth={1.5} />
              待审批
            </span>
          )}
          <span
            className={`nw-badge ${
              workflow.status === 'completed' ? 'nw-badge-success' :
              workflow.status === 'failed' ? 'nw-badge-error' :
              workflow.status === 'running' ? 'nw-badge-info' :
              workflow.status === 'waiting_approval' ? 'nw-badge-warning' :
              ''
            }`}
          >
            {workflow.status === 'completed' ? '已完成' :
             workflow.status === 'failed' ? '失败' :
             workflow.status === 'running' ? '进行中' :
             workflow.status === 'waiting_approval' ? '等待审批' :
             '等待中'}
          </span>
        </div>
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
            className={`absolute top-0 left-0 h-px transition-all duration-500 ${
              isWaitingApproval ? 'bg-yellow-500' : 'bg-white'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Nodes */}
      <div className="space-y-1">
        {nodesArray.map((node, i) => {
          const isCompleted = node.status === 'success'
          const isRunning = node.status === 'running'
          const isPending = node.status === 'pending'
          const isApproval = node.status === 'waiting_approval'
          const isFailed = node.status === 'failed'

          return (
            <div
              key={node.node_id}
              className={`flex items-center gap-3 py-2 px-2 border transition-all ${
                isRunning
                  ? 'border-white/30 bg-white/5'
                  : isApproval
                    ? 'border-yellow-500/30 bg-yellow-500/5 cursor-pointer hover:bg-yellow-500/10'
                    : isFailed
                      ? 'border-red-500/30 bg-red-500/5'
                      : 'border-transparent'
              }`}
              onClick={isApproval ? handleApprovalNodeClick : undefined}
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
                {isApproval && (
                  <AlertTriangle
                    className="w-3.5 h-3.5 text-yellow-500"
                    strokeWidth={1.5}
                  />
                )}
                {isFailed && (
                  <div className="w-3 h-3 border border-red-500 flex items-center justify-center">
                    <span className="text-red-500 text-[8px]">✕</span>
                  </div>
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
                    : isRunning || isApproval
                      ? 'text-white'
                      : isFailed
                        ? 'text-red-400'
                        : 'text-nw-text-muted'
                }`}
              >
                {NODE_LABELS[node.node_id] || node.node_id}
                {isApproval && (
                  <span className="ml-2 text-[10px] text-yellow-500">
                    {approvalPanelOpen ? '收起审批面板' : '点击审批'}
                  </span>
                )}
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

      {/* Approval panel (inline) */}
      {isWaitingApproval && approvalPanelOpen && approvalData && showApproval && (
        <div className="mt-2 nw-fade-in">
          <ApprovalPanel approvalData={approvalData} workflowId={workflow.workflow_id} />
        </div>
      )}

      {/* Waiting approval but no data yet */}
      {isWaitingApproval && approvalPanelOpen && !approvalData && showApproval && (
        <div className="mt-2 p-4 border border-nw-border flex items-center gap-2">
          <Loader2 className="w-4 h-4 text-nw-text-muted animate-spin" strokeWidth={1.5} />
          <span className="text-xs text-nw-text-muted">加载审批数据中...</span>
        </div>
      )}

      {/* Show approval badge even if panel not expanded */}
      {isWaitingApproval && !approvalPanelOpen && showApproval && (
        <button
          onClick={handleApprovalNodeClick}
          className="w-full flex items-center gap-2 px-3 py-2 border border-yellow-500/30 bg-yellow-500/5 hover:bg-yellow-500/10 transition-colors"
        >
          <AlertTriangle className="w-3.5 h-3.5 text-yellow-500" strokeWidth={1.5} />
          <span className="text-xs text-yellow-500">有工作流等待审批</span>
          <Clock className="w-3 h-3 text-nw-text-muted ml-auto" strokeWidth={1.5} />
        </button>
      )}
    </div>
  )
}

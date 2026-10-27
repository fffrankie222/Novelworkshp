import { useState } from 'react'
import {
  CheckCircle2,
  XCircle,
  MessageSquare,
  FileText,
  ChevronDown,
  ChevronRight,
  Edit3,
  Save,
} from 'lucide-react'
import type { ApprovalData as ApprovalDataType } from '../types'
import { useStore } from '../store'

interface ApprovalPanelProps {
  approvalData: ApprovalDataType
  workflowId: string
}

export default function ApprovalPanel({ approvalData, workflowId }: ApprovalPanelProps) {
  const { submitApproval } = useStore()
  const [feedback, setFeedback] = useState('')
  const [expandedFiles, setExpandedFiles] = useState<Record<string, boolean>>({})
  const [editingFiles, setEditingFiles] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)

  // Convert files_content to array for easier iteration
  const filesContent = approvalData.artifact?.files_content || {}
  const fileEntries = Object.entries(filesContent)

  const handleApprove = async () => {
    setSubmitting(true)
    // Build modifications from edited files
    const modifications: Record<string, string> = {}
    Object.entries(editingFiles).forEach(([path, content]) => {
      const original = filesContent[path]
      if (original && original !== content) {
        modifications[path] = content
      }
    })

    await submitApproval(workflowId, {
      approved: true,
      feedback: feedback.trim() || undefined,
      modifications: Object.keys(modifications).length > 0 ? modifications : undefined,
    })
    setSubmitting(false)
    setFeedback('')
    setEditingFiles({})
  }

  const handleReject = async () => {
    if (!feedback.trim()) return
    setSubmitting(true)
    await submitApproval(workflowId, {
      approved: false,
      feedback,
    })
    setSubmitting(false)
    setFeedback('')
  }

  const toggleFile = (path: string) => {
    setExpandedFiles((prev) => ({ ...prev, [path]: !prev[path] }))
  }

  const startEditing = (path: string, content: string) => {
    setEditingFiles((prev) => ({ ...prev, [path]: content }))
  }

  const saveEdit = (path: string) => {
    // Keep the edited content in state
    // The modifications will be sent when approving
  }

  const getFileName = (path: string) => {
    const parts = path.split('/')
    return parts[parts.length - 1] || path
  }

  return (
    <div className="nw-card border-white/20">
      {/* Header */}
      <div className="px-4 py-3 border-b border-nw-border flex items-center justify-between bg-white/[0.03]">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 border border-yellow-500/50 flex items-center justify-center">
            <span className="text-yellow-500 text-xs">!</span>
          </div>
          <div>
            <h4 className="text-xs font-medium text-white">待审批</h4>
            <p className="text-[10px] text-nw-text-muted">
              工作流 {approvalData.workflow_type === 'chapter-production' ? '章节生产' : approvalData.workflow_type === 'novel-setup' ? '新书建立' : '修订'}
              · 等待确认
            </p>
          </div>
        </div>
      </div>

      {/* Description */}
      {approvalData.description && (
        <div className="px-4 py-2 border-b border-nw-border">
          <p className="text-[11px] text-nw-text-secondary italic">
            {approvalData.description}
          </p>
        </div>
      )}

      {/* Files */}
      <div className="p-4 space-y-2">
        <p className="nw-label mb-2">待审核产物</p>
        {fileEntries.length === 0 ? (
          <div className="text-xs text-nw-text-muted py-4 text-center">
            暂无文件内容
          </div>
        ) : (
          fileEntries.map(([path, content]) => {
            const isExpanded = expandedFiles[path] !== false
            const isEditing = path in editingFiles

            return (
              <div key={path} className="border border-nw-border">
                {/* File header */}
                <button
                  onClick={() => toggleFile(path)}
                  className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/[0.02] transition-colors text-left"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-3 h-3 text-nw-text-muted shrink-0" strokeWidth={1.5} />
                  ) : (
                    <ChevronRight className="w-3 h-3 text-nw-text-muted shrink-0" strokeWidth={1.5} />
                  )}
                  <FileText className="w-3 h-3 text-nw-text-secondary shrink-0" strokeWidth={1.5} />
                  <span className="text-xs text-white flex-1 truncate">{getFileName(path)}</span>
                  <span className="nw-badge text-[9px]">{path.split('.').pop()?.toUpperCase() || 'FILE'}</span>
                </button>

                {/* File content */}
                {isExpanded && (
                  <div className="px-3 pb-3">
                    {isEditing ? (
                      <div>
                        <textarea
                          className="nw-textarea w-full h-40 font-mono text-xs leading-relaxed"
                          value={editingFiles[path]}
                          onChange={(e) =>
                            setEditingFiles((prev) => ({
                              ...prev,
                              [path]: e.target.value,
                            }))
                          }
                        />
                        <div className="flex justify-end gap-2 mt-2">
                          <button
                            onClick={() => {
                              const { [path]: _, ...rest } = editingFiles
                              setEditingFiles(rest)
                            }}
                            className="nw-btn text-[11px]"
                          >
                            取消
                          </button>
                          <button
                            onClick={() => saveEdit(path)}
                            className="nw-btn nw-btn-primary text-[11px]"
                          >
                            <Save className="w-3 h-3" strokeWidth={1.5} />
                            保存修改
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <pre className="text-xs text-nw-text-secondary leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto bg-nw-bg p-3 border border-nw-border">
                          {content}
                        </pre>
                        <button
                          onClick={() => startEditing(path, content)}
                          className="mt-2 text-[11px] text-nw-text-muted hover:text-white transition-colors flex items-center gap-1"
                        >
                          <Edit3 className="w-3 h-3" strokeWidth={1.5} />
                          编辑内容
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>

      {/* Feedback input */}
      <div className="px-4 pb-3">
        <label className="nw-label block mb-1.5 flex items-center gap-1.5">
          <MessageSquare className="w-3 h-3" strokeWidth={1.5} />
          反馈意见
          {!feedback.trim() && <span className="text-[10px] text-nw-text-muted">（驳回时必填）</span>}
        </label>
        <textarea
          className="nw-textarea h-16 text-xs"
          placeholder="填写修改意见或确认备注..."
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
        />
      </div>

      {/* Action buttons */}
      <div className="px-4 pb-4 flex items-center gap-2">
        <button
          onClick={handleReject}
          disabled={submitting || !feedback.trim()}
          className="nw-btn flex-1 border-red-500/30 text-red-400 hover:bg-red-500/10 hover:border-red-500 hover:text-red-300 disabled:opacity-40"
        >
          <XCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
          驳回并反馈
        </button>
        <button
          onClick={handleApprove}
          disabled={submitting}
          className="nw-btn nw-btn-primary flex-1"
        >
          <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
          通过并继续
        </button>
      </div>
    </div>
  )
}

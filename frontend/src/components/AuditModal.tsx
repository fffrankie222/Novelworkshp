import {
  X,
  AlertTriangle,
  CheckCircle,
  XCircle,
  MinusCircle,
  Sparkles,
} from 'lucide-react'
import type { AuditResult, AuditIssue } from '../types'

function IssueIcon({ type }: { type: string }) {
  if (type === 'consistency') {
    return <AlertTriangle className="w-3.5 h-3.5" strokeWidth={1.5} />
  }
  if (type === 'ai_style') {
    return <XCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
  }
  if (type === 'quality') {
    return <Sparkles className="w-3.5 h-3.5" strokeWidth={1.5} />
  }
  if (type === 'pacing') {
    return <MinusCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
  }
  return <AlertTriangle className="w-3.5 h-3.5" strokeWidth={1.5} />
}

function TypeBadge({ type }: { type: string }) {
  const labels: Record<string, string> = {
    consistency: '一致性',
    quality: '文笔质量',
    ai_style: 'AI 味',
    pacing: '节奏',
    other: '其他',
  }
  const colors: Record<string, string> = {
    consistency: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    quality: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    ai_style: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    pacing: 'bg-green-500/10 text-green-400 border-green-500/20',
    other: 'bg-nw-bg-secondary text-nw-text-secondary border-nw-border',
  }
  return (
    <span className={`px-1.5 py-0.5 text-[9px] border rounded ${colors[type] || colors.other}`}>
      {labels[type] || type}
    </span>
  )
}

function SeverityDot({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    high: 'bg-red-500',
    medium: 'bg-yellow-500',
    low: 'bg-green-500',
  }
  return <span className={`w-2 h-2 rounded-full ${colors[severity] || 'bg-nw-text-muted'}`} />
}

export default function AuditModal({
  auditResult,
  onClose,
}: {
  auditResult: AuditResult
  onClose: () => void
}) {
  const highIssues = auditResult.issues.filter((i) => i.severity === 'high')
  const mediumIssues = auditResult.issues.filter((i) => i.severity === 'medium')
  const lowIssues = auditResult.issues.filter((i) => i.severity === 'low')

  const scoreColor = (score: number) => {
    if (score >= 8) return 'text-nw-success'
    if (score >= 6) return 'text-nw-warning'
    return 'text-red-400'
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-8">
      {/* 背景遮罩 */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      {/* 弹窗内容 */}
      <div className="relative w-full max-w-2xl max-h-[85vh] bg-nw-bg border border-nw-border rounded-lg overflow-hidden flex flex-col">
        {/* 标题栏 */}
        <div className="px-5 py-3.5 border-b border-nw-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-5 h-5 text-nw-warning" strokeWidth={1.5} />
            <div>
              <h2 className="text-sm font-semibold text-white">章节审核报告</h2>
              <p className="text-[11px] text-nw-text-muted">
                第 {auditResult.chapter_number} 章 · {auditResult.total_words.toLocaleString()} 字
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-nw-text-muted hover:text-white hover:bg-white/5 rounded transition-colors"
          >
            <X className="w-4 h-4" strokeWidth={1.5} />
          </button>
        </div>

        {/* 内容区 */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* 综合评分 */}
          <div className="nw-card p-4">
            <div className="flex items-end gap-4 mb-4">
              <div>
                <p className="text-[11px] text-nw-text-muted mb-1">综合评分</p>
                <p className={`text-3xl font-bold ${scoreColor(auditResult.overall_score)}`}>
                  {auditResult.overall_score.toFixed(1)}
                  <span className="text-sm font-normal text-nw-text-muted"> / 10</span>
                </p>
              </div>
              <div className="flex-1">
                <div className="flex justify-between text-[10px] text-nw-text-muted mb-1">
                  <span>较差</span>
                  <span>优秀</span>
                </div>
                <div className="w-full h-2 bg-nw-bg-secondary rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      auditResult.overall_score >= 8
                        ? 'bg-nw-success'
                        : auditResult.overall_score >= 6
                          ? 'bg-nw-warning'
                          : 'bg-red-500'
                    }`}
                    style={{ width: `${auditResult.overall_score * 10}%` }}
                  />
                </div>
              </div>
            </div>

            {/* 各维度评分 */}
            <div className="grid grid-cols-2 gap-x-6 gap-y-2">
              {Object.entries(auditResult.scores).map(([label, score]) => (
                <div key={label} className="flex items-center gap-2">
                  <span className="text-[11px] text-nw-text-secondary flex-1 truncate">
                    {label}
                  </span>
                  <span className={`text-[11px] font-mono ${scoreColor(score)}`}>
                    {score.toFixed(1)}
                  </span>
                  <div className="w-16 h-1 bg-nw-bg-secondary rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        score >= 8
                          ? 'bg-nw-success'
                          : score >= 6
                            ? 'bg-nw-warning'
                            : 'bg-red-500'
                      }`}
                      style={{ width: `${score * 10}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 问题统计 */}
          <div className="grid grid-cols-3 gap-3">
            <div className="nw-card p-3 text-center">
              <p className="text-xl font-bold text-red-400">{highIssues.length}</p>
              <p className="text-[10px] text-nw-text-muted mt-1">严重问题</p>
            </div>
            <div className="nw-card p-3 text-center">
              <p className="text-xl font-bold text-nw-warning">{mediumIssues.length}</p>
              <p className="text-[10px] text-nw-text-muted mt-1">中等问题</p>
            </div>
            <div className="nw-card p-3 text-center">
              <p className="text-xl font-bold text-nw-success">{lowIssues.length}</p>
              <p className="text-[10px] text-nw-text-muted mt-1">轻微问题</p>
            </div>
          </div>

          {/* 问题列表 */}
          {auditResult.issues.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-white mb-2 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" strokeWidth={1.5} />
                问题列表
                <span className="text-[10px] text-nw-text-muted font-normal">
                  （{auditResult.issues.length} 项）
                </span>
              </h3>
              <div className="space-y-2">
                {auditResult.issues.map((issue) => (
                  <div
                    key={issue.id}
                    className="nw-card p-3 hover:border-white/20 transition-colors"
                  >
                    <div className="flex items-start gap-2">
                      <div className="pt-0.5">
                        <IssueIcon type={issue.type} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <SeverityDot severity={issue.severity} />
                          <TypeBadge type={issue.type} />
                          {issue.location && (
                            <span className="text-[10px] text-nw-text-muted">
                              {issue.location}
                            </span>
                          )}
                        </div>
                        <p className="text-[12px] text-nw-text-secondary leading-relaxed">
                          {issue.description}
                        </p>
                        {issue.suggestion && (
                          <p className="text-[11px] text-nw-success/80 mt-1.5 pl-2 border-l border-nw-success/30">
                            💡 {issue.suggestion}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 审核总结 */}
          {auditResult.summary && (
            <div className="nw-card p-3">
              <h3 className="text-xs font-medium text-white mb-2 flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
                审核总结
              </h3>
              <p className="text-[12px] text-nw-text-secondary leading-relaxed">
                {auditResult.summary}
              </p>
            </div>
          )}
        </div>

        {/* 底部操作 */}
        <div className="px-5 py-3 border-t border-nw-border flex justify-end gap-2 shrink-0">
          <button className="nw-btn text-[12px]" onClick={onClose}>
            关闭
          </button>
          <button
            className="nw-btn nw-btn-primary text-[12px]"
            onClick={() => {
              onClose()
              // 可以触发回到写作步骤并定位到问题
            }}
          >
            开始修改
          </button>
        </div>
      </div>
    </div>
  )
}

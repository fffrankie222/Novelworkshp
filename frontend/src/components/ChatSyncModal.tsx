import { useState, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { X, Loader2, RefreshCw, ArrowLeft, ArrowRight, Zap } from 'lucide-react'
import { api } from '../api/client'
import { useStore } from '../store'
import type { SyncFieldAnalysis, ChatContext } from '../types'

const CONTEXT_TITLES: Record<string, string> = {
  worldbuilding: '世界观数据',
  character: '角色数据',
  outline: '大纲数据',
  writing: '写作数据',
}

const TAB_ICONS: Record<string, typeof Zap> = {
  geography: Zap,
  factions: Zap,
  power_system: Zap,
  history: Zap,
  social_rules: Zap,
  name: Zap,
  role: Zap,
  personality: Zap,
  background: Zap,
  motivation: Zap,
  abilities: Zap,
  catchphrase: Zap,
  portrait: Zap,
  core_conflict: Zap,
  main_plot: Zap,
  chapter_structure: Zap,
  foreshadowing: Zap,
  pacing_notes: Zap,
  chapter_title: Zap,
  chapter_content: Zap,
  chapter_summary: Zap,
  writing_notes: Zap,
}

interface ChatSyncModalProps {
  bookId: string
  context: ChatContext
  analysis: { context: string; fields: SyncFieldAnalysis[]; analyzed_message_count: number } | null
  onClose: () => void
  onApplied: () => void
}

export default function ChatSyncModal({ bookId, context, analysis, onClose, onApplied }: ChatSyncModalProps) {
  const { notify } = useStore()
  const fields = analysis?.fields || []
  const [selectedFields, setSelectedFields] = useState<Set<string>>(() => new Set(fields.map((f) => f.field)))
  const [activeField, setActiveField] = useState<string>(fields[0]?.field || '')
  const [applying, setApplying] = useState(false)

  const currentField = useMemo(() => fields.find((f) => f.field === activeField), [fields, activeField])
  const [viewMode, setViewMode] = useState<'proposed' | 'current'>('proposed')
  const [editedValue, setEditedValue] = useState<string>(currentField?.proposed_value || '')

  // Update editedValue when activeField changes
  useMemo(() => {
    if (currentField) {
      setEditedValue(currentField.proposed_value)
    }
  }, [activeField]) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleField = (field: string) => {
    setSelectedFields((prev) => {
      const next = new Set(prev)
      if (next.has(field)) next.delete(field)
      else next.add(field)
      return next
    })
  }

  const handleSelectAll = () => {
    if (selectedFields.size === fields.length) {
      setSelectedFields(new Set())
    } else {
      setSelectedFields(new Set(fields.map((f) => f.field)))
    }
  }

  const handleApply = async () => {
    if (selectedFields.size === 0 || applying) return
    setApplying(true)
    try {
      const selected: Record<string, string> = {}
      for (const f of fields) {
        if (selectedFields.has(f.field)) {
          // Use edited value if this is the currently active field, otherwise use proposed
          selected[f.field] = f.field === activeField ? editedValue : f.proposed_value
        }
      }
      const res = await api.applySync(bookId, context, selected)
      if (res.success) {
        notify(res.message, 'success')
        onApplied()
        onClose()
      } else {
        notify('同步失败', 'error')
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '同步请求失败'
      notify(msg, 'error')
    } finally {
      setApplying(false)
    }
  }

  if (!analysis || fields.length === 0) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center nw-fade-in">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-nw-bg border border-nw-border w-[780px] max-w-[95vw] h-[80vh] max-h-[700px] flex flex-col">
        {/* Header */}
        <div className="px-5 py-3 border-b border-nw-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 border border-nw-border-light flex items-center justify-center">
              <RefreshCw className="w-4 h-4 text-white" strokeWidth={1.5} />
            </div>
            <div>
              <h3 className="text-sm font-medium text-white">对话 → 结构化数据同步</h3>
              <p className="text-[10px] text-nw-text-muted">
                分析了 {analysis.analyzed_message_count} 条对话 · {CONTEXT_TITLES[context] || context}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-nw-text-muted hover:text-white transition-colors">
            <X className="w-4 h-4" strokeWidth={1.5} />
          </button>
        </div>

        {/* Body: left field list + right content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left: field list */}
          <div className="w-[240px] border-r border-nw-border flex flex-col shrink-0">
            <div className="px-3 py-2 border-b border-nw-border flex items-center justify-between">
              <span className="text-[11px] text-nw-text-muted">
                {selectedFields.size}/{fields.length} 项已选
              </span>
              <button
                onClick={handleSelectAll}
                className="text-[11px] text-nw-text-secondary hover:text-white transition-colors"
              >
                {selectedFields.size === fields.length ? '取消全选' : '全选'}
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              {fields.map((f) => {
                const active = activeField === f.field
                const selected = selectedFields.has(f.field)
                return (
                  <button
                    key={f.field}
                    onClick={() => setActiveField(f.field)}
                    className={`w-full text-left px-3 py-2.5 border-b border-nw-border/50 transition-all ${
                      active ? 'bg-white/[0.04]' : 'hover:bg-white/[0.02]'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={(e) => {
                          e.stopPropagation()
                          toggleField(f.field)
                        }}
                        className="w-3.5 h-3.5 accent-white shrink-0"
                      />
                      <span className={`text-xs font-medium truncate ${active ? 'text-white' : 'text-nw-text'}`}>
                        {f.label}
                      </span>
                    </div>
                    <p className="text-[10px] text-nw-text-muted mt-1 pl-5.5 truncate">
                      {f.change_description}
                    </p>
                    {/* Length indicator */}
                    <div className="flex items-center gap-1 mt-1 pl-5.5">
                      {f.current_value ? (
                        <span className="text-[9px] text-nw-text-muted">
                          {f.current_value.length}字 → {f.proposed_value.length}字
                        </span>
                      ) : (
                        <span className="text-[9px] text-nw-success">
                          新建 {f.proposed_value.length}字
                        </span>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Right: content view */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {currentField && (
              <>
                {/* Sub-header */}
                <div className="px-4 py-2.5 border-b border-nw-border flex items-center justify-between shrink-0">
                  <div>
                    <h4 className="text-xs font-medium text-white">{currentField.label}</h4>
                    <p className="text-[10px] text-nw-text-muted mt-0.5">
                      {currentField.change_description}
                    </p>
                  </div>
                  <div className="flex border border-nw-border">
                    <button
                      onClick={() => setViewMode('proposed')}
                      className={`px-2.5 py-1 text-[11px] transition-colors flex items-center gap-1 ${
                        viewMode === 'proposed'
                          ? 'bg-white text-nw-bg'
                          : 'text-nw-text-secondary hover:text-white'
                      }`}
                    >
                      <ArrowRight className="w-3 h-3" strokeWidth={1.5} />
                      新内容
                    </button>
                    <button
                      onClick={() => setViewMode('current')}
                      className={`px-2.5 py-1 text-[11px] transition-colors flex items-center gap-1 ${
                        viewMode === 'current'
                          ? 'bg-white text-nw-bg'
                          : 'text-nw-text-secondary hover:text-white'
                      }`}
                    >
                      <ArrowLeft className="w-3 h-3" strokeWidth={1.5} />
                      当前
                    </button>
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4">
                  {viewMode === 'proposed' ? (
                    <div>
                      {/* Editable proposed content */}
                      <textarea
                        className="w-full min-h-[300px] bg-nw-bg-secondary border border-nw-border p-3 text-xs text-nw-text leading-relaxed font-mono resize-y outline-none focus:border-white/30 transition-colors"
                        value={editedValue}
                        onChange={(e) => setEditedValue(e.target.value)}
                      />
                      <p className="text-[10px] text-nw-text-muted mt-2">
                        你可以直接编辑上方内容，确认后同步到左侧面板
                      </p>
                    </div>
                  ) : currentField.current_value ? (
                    <div className="markdown-preview">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {currentField.current_value}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-32 text-nw-text-muted text-xs">
                      当前此字段为空
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-nw-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <p className="text-[11px] text-nw-text-muted">
              选中 {selectedFields.size} 个字段将被写入结构化数据
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onClose} className="nw-btn" disabled={applying}>
              取消
            </button>
            <button
              onClick={handleApply}
              className="nw-btn nw-btn-primary flex items-center gap-1.5"
              disabled={selectedFields.size === 0 || applying}
            >
              {applying ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
              ) : (
                <RefreshCw className="w-3.5 h-3.5" strokeWidth={1.5} />
              )}
              确认同步 ({selectedFields.size})
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

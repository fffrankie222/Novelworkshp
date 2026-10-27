import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, Loader2, ArrowRight, MessageSquare, Bookmark, BookmarkCheck, AtSign, User, Swords } from 'lucide-react'
import { api } from '../api/client'
import { useStore } from '../store'
import type { ChatMessage, ChatContext, ChatCheckpoint } from '../types'
import { CONTEXT_LABELS } from '../types'

// ---- Entity types for @mention ----
export interface MentionEntity {
  name: string
  type: 'character' | 'faction'
  id?: string
}

export interface MentionEntities {
  characters: MentionEntity[]
  factions: MentionEntity[]
}

// ---- Props ----
export interface ChatPanelProps {
  bookId: string
  context: ChatContext
  contextId?: string
  onStageDataUpdate?: (data: Record<string, unknown>) => void
  /** Called when backend extracts structured data updates from chat */
  onDataUpdate?: (updates: Record<string, string>, context: string) => void
  /** Title shown in the header */
  title?: string
  /** Placeholder hint messages when chat is empty */
  hints?: string[]
  /** Entities for @mention autocomplete */
  entities?: MentionEntities
  /** 当分析同步弹窗打开或分析进行中时，禁止自动写入结构化数据 */
  suppressAutoSync?: boolean
  /** writing 场景：当前章节下拉选中的章节号，随消息回传后端（R1 修复） */
  chapterNumber?: number
}

// ---- Message Bubble ----
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <div className="px-3 py-1.5 border border-nw-border bg-nw-bg-secondary text-[11px] text-nw-text-muted max-w-md text-center">
          {message.content}
        </div>
      </div>
    )
  }

  const time = new Date(message.timestamp)
  const timeStr = `${String(time.getHours()).padStart(2, '0')}:${String(time.getMinutes()).padStart(2, '0')}`

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`w-7 h-7 shrink-0 flex items-center justify-center text-[10px] font-bold border ${
          isUser
            ? 'border-white bg-white text-nw-bg'
            : 'border-nw-border bg-nw-bg-secondary text-nw-text-secondary'
        }`}
      >
        {isUser ? '你' : 'AI'}
      </div>

      {/* Bubble */}
      <div className={`max-w-[75%] flex flex-col ${isUser ? 'items-end' : 'items-start'} gap-1`}>
        <div
          className={`px-4 py-3 text-[13px] leading-relaxed ${
            isUser
              ? 'bg-white/10 border border-white/10 text-white'
              : 'bg-nw-bg-secondary border border-nw-border text-nw-text'
          }`}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              h1: ({ children }) => <h1 className="text-base font-bold text-white mb-2">{children}</h1>,
              h2: ({ children }) => <h2 className="text-sm font-bold text-white mb-1.5">{children}</h2>,
              h3: ({ children }) => <h3 className="text-sm font-semibold text-white mb-1">{children}</h3>,
              ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
              li: ({ children }) => <li className="text-[13px]">{children}</li>,
              code: ({ children }) => (
                <code className="px-1.5 py-0.5 bg-nw-bg border border-nw-border text-[11px] font-mono">
                  {children}
                </code>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-nw-border pl-3 my-2 text-nw-text-muted italic">
                  {children}
                </blockquote>
              ),
              table: ({ children }) => (
                <div className="overflow-x-auto my-2">
                  <table className="min-w-full text-xs border border-nw-border">{children}</table>
                </div>
              ),
              th: ({ children }) => (
                <th className="border border-nw-border px-2 py-1 bg-nw-bg-secondary text-white font-medium">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="border border-nw-border px-2 py-1">{children}</td>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        <span className="text-[10px] text-nw-text-muted font-mono">{timeStr}</span>
      </div>
    </div>
  )
}

// ---- Main Component ----
export default function ChatPanel({
  bookId,
  context,
  contextId,
  onStageDataUpdate,
  onDataUpdate,
  title,
  hints,
  entities,
  suppressAutoSync,
  chapterNumber,
}: ChatPanelProps) {
  const { notify } = useStore()

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [stage, setStage] = useState<string>('')
  const [stageData, setStageData] = useState<Record<string, unknown>>({})
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [checkpoint, setCheckpoint] = useState<ChatCheckpoint | null>(null)
  const [checkpointLoading, setCheckpointLoading] = useState(false)

  // @mention state
  const [mentionOpen, setMentionOpen] = useState(false)
  const [mentionQuery, setMentionQuery] = useState('')
  const [mentionIndex, setMentionIndex] = useState(0)
  const [mentionStart, setMentionStart] = useState(-1)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto scroll
  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // @mention: build filtered entity list
  const mentionList = useCallback((): MentionEntity[] => {
    if (!entities) return []
    const q = mentionQuery.toLowerCase()
    const all = [...(entities.characters || []), ...(entities.factions || [])]
    if (!q) return all.slice(0, 10)
    return all.filter((e) => e.name.toLowerCase().includes(q)).slice(0, 10)
  }, [entities, mentionQuery])

  // Select a mention from the dropdown
  const selectMention = useCallback((entity: MentionEntity) => {
    if (mentionStart < 0) return
    const before = input.slice(0, mentionStart)
    const cursorPos = inputRef.current?.selectionStart ?? input.length
    const after = input.slice(cursorPos)
    const newInput = before + '@' + entity.name + ' ' + after
    setInput(newInput)
    setMentionOpen(false)
    setMentionQuery('')
    setMentionStart(-1)
    setMentionIndex(0)
    // Focus back to textarea
    setTimeout(() => {
      const el = inputRef.current
      if (el) {
        el.focus()
        const pos = before.length + entity.name.length + 2 // @name + space
        el.setSelectionRange(pos, pos)
      }
    }, 0)
  }, [input, mentionStart])

  // Load history when context / contextId changes
  useEffect(() => {
    if (!bookId) {
      setInitialLoading(false)
      return
    }

    setInitialLoading(true)
    setMessages([])
    setSuggestions([])
    setCheckpoint(null)

    api
      .getChatHistory(bookId, context, contextId)
      .then((res) => {
        setMessages(res.messages || [])
        setStage(res.stage || '')
        setStageData(res.stage_data || {})
        setCheckpoint(res.checkpoint || null)
        if (res.stage_data && onStageDataUpdate) {
          onStageDataUpdate(res.stage_data)
        }
      })
      .catch(() => {
        setMessages([])
        setStage('')
        setStageData({})
        setCheckpoint(null)
      })
      .finally(() => setInitialLoading(false))

    // 检查跨模块同步通知
    api.getSyncNotifications(bookId, context).then((res) => {
      if (res.notifications && res.notifications.length > 0) {
        const now = new Date().toISOString()
        const syncMsg: ChatMessage = {
          role: 'system',
          content: `🔄 来自${res.notifications.map(n => n.source_label).join('、')}模块的更新：\n${res.notifications.map(n => n.summary).join('\n')}`,
          timestamp: now,
        }
        setMessages((prev) => [...prev, syncMsg])

        // 自动发送一条消息让 AI 主动确认变更
        const syncTrigger = `我刚了解到以下来自其他模块的最新设定：\n${res.notifications.map(n => `[${n.source_label}] ${n.summary}`).join('\n')}\n请简短确认你已了解这些变更，并说明它们可能对本模块的影响。`
        setTimeout(() => {
          api.sendChatMessage(bookId, context, syncTrigger, contextId, undefined, chapterNumber)
            .then((chatRes) => {
              const aiMsg: ChatMessage = {
                role: 'assistant',
                content: chatRes.reply,
                timestamp: new Date().toISOString(),
              }
              setMessages((prev) => [...prev, aiMsg])
            })
            .catch(() => {})
        }, 500)
      }
    }).catch(() => {})
  }, [bookId, context, contextId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Create checkpoint manually
  const handleCreateCheckpoint = useCallback(async () => {
    if (!bookId || checkpointLoading) return
    setCheckpointLoading(true)
    try {
      const res = await api.createCheckpoint(bookId, context)
      if (res.success) {
        notify(res.message, 'success')
        // Refresh history to get updated checkpoint info
        const historyRes = await api.getChatHistory(bookId, context, contextId)
        setCheckpoint(historyRes.checkpoint || null)
      }
    } catch {
      notify('创建断点失败，请重试', 'error')
    } finally {
      setCheckpointLoading(false)
    }
  }, [bookId, context, contextId, checkpointLoading, notify])

  // Send message
  const handleSend = useCallback(
    async (text?: string) => {
      const messageText = (text || input).trim()
      if (!messageText || !bookId || loading) return

      const userMsg: ChatMessage = {
        role: 'user',
        content: messageText,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMsg])
      setInput('')
      setSuggestions([])
      setLoading(true)

      try {
        const res = await api.sendChatMessage(bookId, context, messageText, contextId, suppressAutoSync, chapterNumber)

        const aiMsg: ChatMessage = {
          role: 'assistant',
          content: res.reply,
          timestamp: new Date().toISOString(),
          stage: res.stage,
        }
        setMessages((prev) => [...prev, aiMsg])

        if (res.stage) setStage(res.stage)
        if (res.stage_data) {
          setStageData(res.stage_data)
          if (onStageDataUpdate) onStageDataUpdate(res.stage_data)
        }
        // 通知父页面有结构化数据更新
        if (res.data_updates && Object.keys(res.data_updates).length > 0 && onDataUpdate) {
          onDataUpdate(res.data_updates, context)
        }
        if (res.suggestions) setSuggestions(res.suggestions)
      } catch (err) {
        console.error('[ChatPanel] sendChatMessage failed:', err)
        notify('发送消息失败，请检查后端是否启动', 'error')
      } finally {
        setLoading(false)
      }
    },
    [input, bookId, context, contextId, loading, notify, onStageDataUpdate, onDataUpdate, suppressAutoSync, chapterNumber]
  )

  // Confirm stage
  const handleConfirmStage = useCallback(async () => {
    if (!bookId) return
    try {
      const res = await api.confirmChatStage(bookId, context, contextId)
      if (res.success) {
        notify(res.message || '阶段已确认', 'success')
        const sysMsg: ChatMessage = {
          role: 'system',
          content: `✅ ${res.message || '阶段已确认'}${res.checkpoint_created ? '（已自动创建对话断点）' : ''}`,
          timestamp: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, sysMsg])
        setSuggestions([])
        // Refresh checkpoint info
        const historyRes = await api.getChatHistory(bookId, context, contextId)
        setCheckpoint(historyRes.checkpoint || null)
      }
    } catch {
      notify('确认阶段失败，请重试', 'error')
    }
  }, [bookId, context, contextId, notify])

  // Keyboard
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // @mention navigation
    if (mentionOpen) {
      const list = mentionList()
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setMentionIndex((prev) => (prev + 1) % Math.max(list.length, 1))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setMentionIndex((prev) => (prev - 1 + list.length) % Math.max(list.length, 1))
        return
      }
      if (e.key === 'Enter' && list.length > 0) {
        e.preventDefault()
        selectMention(list[mentionIndex])
        return
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        setMentionOpen(false)
        return
      }
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Auto-resize textarea + @mention detection
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value
    setInput(val)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`

    // Detect @mention trigger
    const cursorPos = el.selectionStart ?? 0
    // Find the last @ before cursor
    const textBeforeCursor = val.slice(0, cursorPos)
    const atIndex = textBeforeCursor.lastIndexOf('@')

    if (atIndex >= 0) {
      // Check if @ is at start or preceded by space/newline
      const charBefore = atIndex > 0 ? textBeforeCursor[atIndex - 1] : ' '
      if (charBefore === ' ' || charBefore === '\n' || atIndex === 0) {
        const query = textBeforeCursor.slice(atIndex + 1)
        // Only show if no spaces in the query (still typing the name)
        if (!query.includes(' ') && !query.includes('\n')) {
          setMentionOpen(true)
          setMentionQuery(query)
          setMentionStart(atIndex)
          setMentionIndex(0)
          return
        }
      }
    }
    setMentionOpen(false)
  }

  // ---- Render ----

  if (initialLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-5 h-5 mx-auto mb-2 text-nw-text-muted animate-spin" />
          <p className="text-xs text-nw-text-muted">加载对话...</p>
        </div>
      </div>
    )
  }

  const displayTitle = title || CONTEXT_LABELS[context]

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-nw-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-nw-text-muted" strokeWidth={1.5} />
          <span className="text-sm font-medium text-white">{displayTitle}</span>
          {stage && (
            <span className="nw-badge text-[10px] ml-1">{stage}</span>
          )}
          {checkpoint && (
            <span className="nw-badge text-[10px] ml-1 flex items-center gap-1" title={`断点创建于 ${checkpoint.created_at}，已压缩 ${checkpoint.message_index} 条历史消息`}>
              <BookmarkCheck className="w-3 h-3" strokeWidth={1.5} />
              已设断点
            </span>
          )}
        </div>
        {messages.length >= 4 && (
          <button
            onClick={handleCreateCheckpoint}
            disabled={checkpointLoading}
            className="flex items-center gap-1 px-2 py-1 text-[11px] border border-nw-border text-nw-text-secondary hover:text-white hover:border-white/30 transition-all rounded disabled:opacity-50"
            title="压缩当前对话历史为摘要，后续对话只使用断点后的新消息"
          >
            {checkpointLoading ? (
              <Loader2 className="w-3 h-3 animate-spin" strokeWidth={1.5} />
            ) : (
              <Bookmark className="w-3 h-3" strokeWidth={1.5} />
            )}
            {checkpoint ? '更新断点' : '设置断点'}
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="w-11 h-11 mx-auto mb-3 border border-nw-border flex items-center justify-center">
                <MessageSquare className="w-5 h-5 text-nw-text-muted" strokeWidth={1} />
              </div>
              <h3 className="text-sm text-white font-medium mb-1">
                与AI对话 · {displayTitle}
              </h3>
              <p className="text-[12px] text-nw-text-muted leading-relaxed mb-4">
                通过对话来完成{displayTitle}，AI会根据你的想法逐步完善内容。
              </p>
              {(hints && hints.length > 0) && (
                <div className="flex flex-wrap gap-2 justify-center">
                  {hints.map((hint) => (
                    <button
                      key={hint}
                      className="px-3 py-1.5 text-[11px] border border-nw-border text-nw-text-secondary hover:text-white hover:border-white/30 transition-all"
                      onClick={() => handleSend(hint)}
                    >
                      {hint}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-4 max-w-3xl mx-auto">
            {messages.map((msg, i) => (
              <div key={i}>
                {/* Checkpoint divider: show before the first message after compressed history */}
                {checkpoint && checkpoint.message_index === i && i > 0 && (
                  <div className="flex items-center gap-3 py-2">
                    <div className="flex-1 h-px bg-nw-border/50" />
                    <span className="text-[11px] text-nw-text-muted whitespace-nowrap flex items-center gap-1.5">
                      📍 对话断点 · 已压缩 {checkpoint.message_index} 条历史消息
                    </span>
                    <div className="flex-1 h-px bg-nw-border/50" />
                  </div>
                )}
                <MessageBubble message={msg} />
              </div>
            ))}

            {/* Loading */}
            {loading && (
              <div className="flex gap-3">
                <div className="w-7 h-7 shrink-0 flex items-center justify-center text-[10px] font-bold border border-nw-border bg-nw-bg-secondary text-nw-text-secondary">
                  AI
                </div>
                <div className="px-4 py-3 bg-nw-bg-secondary border border-nw-border">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-nw-text-muted" />
                    <span className="text-[12px] text-nw-text-muted">正在思考...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="px-5 pb-4 pt-2 border-t border-nw-border shrink-0">
        {/* Suggestions */}
        {suggestions.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {suggestions.map((s, i) => (
              <button
                key={i}
                className="px-2.5 py-1 text-[11px] border border-nw-border text-nw-text-secondary hover:text-white hover:border-white/30 transition-all flex items-center gap-1"
                onClick={() => handleSend(s)}
                disabled={loading}
              >
                <ArrowRight className="w-2.5 h-2.5" strokeWidth={1.5} />
                {s}
              </button>
            ))}
          </div>
        )}

        <div className="flex gap-2 items-end relative">
          {/* @mention dropdown */}
          {mentionOpen && mentionList().length > 0 && (
            <div className="absolute bottom-full left-0 mb-1 w-64 max-h-48 overflow-y-auto bg-nw-bg border border-nw-border rounded shadow-lg z-50">
              {mentionList().map((entity, i) => (
                <button
                  key={`${entity.type}-${entity.name}`}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-left text-xs transition-colors ${
                    i === mentionIndex
                      ? 'bg-white/10 text-white'
                      : 'text-nw-text-secondary hover:bg-white/5 hover:text-white'
                  }`}
                  onClick={() => selectMention(entity)}
                  onMouseEnter={() => setMentionIndex(i)}
                >
                  {entity.type === 'character' ? (
                    <User className="w-3 h-3 shrink-0 text-nw-text-muted" strokeWidth={1.5} />
                  ) : (
                    <Swords className="w-3 h-3 shrink-0 text-nw-text-muted" strokeWidth={1.5} />
                  )}
                  <span className="truncate">{entity.name}</span>
                  <span className="ml-auto text-[10px] text-nw-text-muted">
                    {entity.type === 'character' ? '角色' : '势力'}
                  </span>
                </button>
              ))}
            </div>
          )}
          <textarea
            ref={inputRef}
            className="flex-1 px-4 py-3 bg-nw-bg-secondary border border-nw-border text-[13px] text-white placeholder:text-nw-text-muted resize-none outline-none focus:border-white/30 transition-colors min-h-[44px] max-h-[120px]"
            placeholder="输入你的想法... (@ 引用角色/势力, Enter 发送)"
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={loading}
          />
          <button
            className="nw-btn nw-btn-primary h-[44px] px-4"
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" strokeWidth={1.5} />
            ) : (
              <Send className="w-4 h-4" strokeWidth={1.5} />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// Re-export handleConfirmStage for parent usage via ref pattern is complex;
// instead expose via a separate export
export { type ChatPanelProps as ChatPanelComponentProps }

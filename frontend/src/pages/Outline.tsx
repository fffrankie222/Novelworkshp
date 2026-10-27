import { useState, useMemo, useEffect, useCallback } from 'react'
import {
  BookOpen,
  FileText,
  RefreshCw,
  Loader2,
  ChevronDown,
  ChevronRight,
  Flag,
  CheckCircle2,
} from 'lucide-react'
import ChatPanel from '../components/ChatPanel'
import ChatSyncModal from '../components/ChatSyncModal'
import { api } from '../api/client'
import { useStore } from '../store'
import type {
  OutlineVolume,
  OutlineChapter,
  OutlineNode,
  Foreshadow,
  SyncFieldAnalysis,
} from '../types'

type Tab = 'story' | 'foreshadow'

// ─── 右侧选中的条目 ───
type SelectedItem =
  | { kind: 'volume'; data: OutlineVolume }
  | { kind: 'chapter'; data: OutlineChapter; volumeTitle: string }
  | { kind: 'foreshadow'; data: Foreshadow }
  | null

export default function Outline() {
  const {
    currentBookId,
    outlineData,
    hooks,
    booksLoading,
    fetchOutline,
    fetchHooks,
    saveOutline,
    outlineLoading,
    notify,
    characters,
    fetchCharacters,
  } = useStore()

  // 当前书籍的角色列表（用于 @mention 自动补全）
  const bookCharacters = useMemo(
    () => (currentBookId ? characters.filter((c) => c.book_id === currentBookId) : []),
    [characters, currentBookId],
  )

  const [tab, setTab] = useState<Tab>('story')
  const [selected, setSelected] = useState<SelectedItem>(null)
  const [expandedVolumes, setExpandedVolumes] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [syncOpen, setSyncOpen] = useState(false)
  const [syncAnalyzing, setSyncAnalyzing] = useState(false)
  const [syncAnalysis, setSyncAnalysis] = useState<{
    context: string
    fields: SyncFieldAnalysis[]
    analyzed_message_count: number
  } | null>(null)

  // ─── CRUD state ───
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<Record<string, any>>({})

  // ─── 加载数据 ───
  useEffect(() => {
    if (!booksLoading && currentBookId) {
      setLoading(true)
      Promise.all([fetchOutline(currentBookId), fetchHooks(currentBookId), fetchCharacters(currentBookId)]).finally(
        () => setLoading(false),
      )
    }
  }, [currentBookId, booksLoading]) // eslint-disable-line react-hooks/exhaustive-deps

  // ─── 解析 volumes：兼容新旧格式 ───
  const volumes = useMemo<OutlineVolume[]>(() => {
    if (!outlineData || outlineData.length === 0) return []

    // 新格式：顶层已有 volumes 字段（从 outline.json 的 volumes 数组来）
    // 但 outlineData 是从 API 返回的 outline 数组，可能是旧格式的 OutlineNode[]
    // 先检查第一个元素是否有 story_arc 或 chapters 字段（新格式）
    const first = outlineData[0] as unknown as Record<string, unknown>
    if (first && (first.story_arc !== undefined || (first.chapters && Array.isArray(first.chapters)))) {
      // 新格式
      return (outlineData as unknown as OutlineVolume[]).map((v) => ({
        ...v,
        chapters: (v.chapters || []).map((c) => ({
          ...c,
          summary: c.summary || '',
        })),
      }))
    }

    // 旧格式 OutlineNode[] → 转换
    return (outlineData as unknown as OutlineNode[])
      .filter((n) => n.type === 'volume' || (n.children && n.children.length > 0))
      .map((v, vi) => ({
        id: v.id || `vol-${vi}`,
        number: vi + 1,
        title: v.title || `第${vi + 1}卷`,
        story_arc: v.summary || '',
        chapters: (v.children || []).map((c: OutlineNode, ci: number) => ({
          id: c.id || `ch-${vi}-${ci}`,
          number: c.chapter_number || ci + 1,
          title: c.title || `第${ci + 1}章`,
          summary: c.summary || '',
          characters: [] as string[],
        })),
      }))
  }, [outlineData])

  // ─── 解析 foreshadowing ───
  const foreshadows = useMemo<Foreshadow[]>(() => {
    if (hooks.length > 0) {
      return hooks.map((h) => ({
        id: h.id,
        purpose: h.title,
        description: h.description,
        start_chapter: h.planted_chapter,
        end_chapter: h.target_chapter,
        characters: [],
        status: (h.status === 'planted'
          ? 'planted'
          : h.status === 'resolved'
            ? 'resolved'
            : 'active') as Foreshadow['status'],
      }))
    }
    return []
  }, [hooks])

  // ─── 展开/折叠 ───
  const toggleVolume = (id: string) => {
    setExpandedVolumes((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  // ─── 统计 ───
  const stats = useMemo(() => {
    const totalCh = volumes.reduce((s, v) => s + v.chapters.length, 0)
    return {
      volumes: volumes.length,
      chapters: totalCh,
      planted: foreshadows.filter((f) => f.status === 'planted').length,
      active: foreshadows.filter((f) => f.status === 'active').length,
      resolved: foreshadows.filter((f) => f.status === 'resolved').length,
    }
  }, [volumes, foreshadows])

  // ─── 同步 ───
  const handleAnalyzeSync = useCallback(async () => {
    if (!currentBookId || syncAnalyzing) return
    setSyncAnalyzing(true)
    try {
      const res = await (await import('../api/client')).api.analyzeSync(currentBookId, 'outline')
      if (res.fields.length === 0) {
        notify('暂无可同步的内容，请先与AI讨论大纲规划', 'info')
      } else {
        setSyncAnalysis(res)
        setSyncOpen(true)
      }
    } catch {
      notify('分析失败，请重试', 'error')
    } finally {
      setSyncAnalyzing(false)
    }
  }, [currentBookId, syncAnalyzing, notify])

  const handleSyncApplied = useCallback(() => {
    if (currentBookId) {
      fetchOutline(currentBookId)
      fetchHooks(currentBookId)
    }
  }, [currentBookId, fetchOutline, fetchHooks])

  const handleStageDataUpdate = useCallback(() => {
    if (currentBookId) {
      fetchOutline(currentBookId)
      fetchHooks(currentBookId)
    }
  }, [currentBookId, fetchOutline, fetchHooks])

  // Handle structured data updates auto-extracted from chat
  const handleDataUpdate = useCallback((_updates: Record<string, string>, _ctx: string) => {
    if (currentBookId) {
      fetchOutline(currentBookId)
      fetchHooks(currentBookId)
    }
  }, [currentBookId, fetchOutline, fetchHooks])

  // ─── CRUD helpers ───
  const persistOutline = useCallback(async (newVolumes: OutlineVolume[]) => {
    if (!currentBookId) return
    try {
      await api.updateOutline(currentBookId, { outline: newVolumes as any })
      notify('大纲已保存', 'success')
      fetchOutline(currentBookId)
    } catch {
      notify('保存失败', 'error')
    }
  }, [currentBookId, notify, fetchOutline])

  const handleAddVolume = useCallback(() => {
    const title = window.prompt('请输入卷标题：')
    if (!title) return
    const newVol: OutlineVolume = {
      id: `vol-${Date.now()}`,
      number: volumes.length + 1,
      title,
      story_arc: '',
      chapters: [],
    }
    persistOutline([...volumes, newVol])
  }, [volumes, persistOutline])

  const handleAddChapter = useCallback((volumeId: string) => {
    const title = window.prompt('请输入章节标题：')
    if (!title) return
    const newVolumes = volumes.map((v) => {
      if (v.id === volumeId) {
        const newCh: OutlineChapter = {
          id: `ch-${Date.now()}`,
          number: v.chapters.length + 1,
          title,
          summary: '',
          characters: [],
        }
        return { ...v, chapters: [...v.chapters, newCh] }
      }
      return v
    })
    persistOutline(newVolumes)
  }, [volumes, persistOutline])

  const handleDeleteVolume = useCallback((volumeId: string) => {
    if (!window.confirm('确认删除此卷？')) return
    persistOutline(volumes.filter((v) => v.id !== volumeId))
  }, [volumes, persistOutline])

  const handleDeleteChapter = useCallback((volumeId: string, chapterId: string) => {
    const newVolumes = volumes.map((v) => {
      if (v.id === volumeId) {
        return { ...v, chapters: v.chapters.filter((c) => c.id !== chapterId) }
      }
      return v
    })
    persistOutline(newVolumes)
  }, [volumes, persistOutline])

  const handleMoveChapter = useCallback((volumeId: string, chapterId: string, direction: 'up' | 'down') => {
    const newVolumes = volumes.map((v) => {
      if (v.id !== volumeId) return v
      const idx = v.chapters.findIndex((c) => c.id === chapterId)
      if (idx < 0) return v
      const targetIdx = direction === 'up' ? idx - 1 : idx + 1
      if (targetIdx < 0 || targetIdx >= v.chapters.length) return v
      const newChs = [...v.chapters]
      ;[newChs[idx], newChs[targetIdx]] = [newChs[targetIdx], newChs[idx]]
      return { ...v, chapters: newChs.map((c, i) => ({ ...c, number: i + 1 })) }
    })
    persistOutline(newVolumes)
  }, [volumes, persistOutline])

  const handleStartEdit = useCallback((id: string, form: Record<string, any>) => {
    setEditingId(id)
    setEditForm(form)
  }, [])

  const handleCancelEdit = useCallback(() => {
    setEditingId(null)
    setEditForm({})
  }, [])

  const handleSaveEdit = useCallback(() => {
    if (!editingId) return
    // Check if it's a volume edit
    const vol = volumes.find((v) => v.id === editingId)
    if (vol) {
      const newVolumes = volumes.map((v) =>
        v.id === editingId ? { ...v, title: editForm.title || v.title, story_arc: editForm.story_arc || v.story_arc } : v
      )
      persistOutline(newVolumes)
      setEditingId(null)
      return
    }
    // Check if it's a chapter edit
    for (const v of volumes) {
      const ch = v.chapters.find((c) => c.id === editingId)
      if (ch) {
        const newVolumes = volumes.map((vv) => {
          if (vv.id !== v.id) return vv
          return {
            ...vv,
            chapters: vv.chapters.map((c) =>
              c.id === editingId ? { ...c, title: editForm.title || c.title, summary: editForm.summary || c.summary } : c
            ),
          }
        })
        persistOutline(newVolumes)
        setEditingId(null)
        return
      }
    }
  }, [editingId, editForm, volumes, persistOutline])

  const handleAddForeshadow = useCallback(() => {
    const purpose = window.prompt('请输入伏笔描述：')
    if (!purpose || !currentBookId) return
    api.createHook(currentBookId, { title: purpose, description: '', planted_chapter: 1, target_chapter: 1, status: 'planted' })
      .then(() => {
        notify('伏笔已添加', 'success')
        fetchHooks(currentBookId)
      })
      .catch(() => notify('添加失败', 'error'))
  }, [currentBookId, notify, fetchHooks])

  const handleDeleteForeshadow = useCallback((hookId: string) => {
    if (!window.confirm('确认删除此伏笔？') || !currentBookId) return
    api.updateHook(currentBookId, hookId, { status: 'resolved' } as any)
      .then(() => {
        notify('伏笔已删除', 'success')
        fetchHooks(currentBookId)
      })
      .catch(() => notify('删除失败', 'error'))
  }, [currentBookId, notify, fetchHooks])

  const handleCycleForeshadowStatus = useCallback((hookId: string, currentStatus: string) => {
    if (!currentBookId) return
    const next = currentStatus === 'planted' ? 'active' : currentStatus === 'active' ? 'resolved' : 'planted'
    api.updateHook(currentBookId, hookId, { status: next } as any)
      .then(() => {
        fetchHooks(currentBookId)
      })
      .catch(() => notify('状态更新失败', 'error'))
  }, [currentBookId, notify, fetchHooks])

  // ─── 首次加载时默认展开所有卷 ───
  useEffect(() => {
    if (volumes.length > 0 && expandedVolumes.size === 0) {
      setExpandedVolumes(new Set(volumes.map((v) => v.id)))
    }
  }, [volumes]) // eslint-disable-line react-hooks/exhaustive-deps

  const isLoading = loading || outlineLoading

  return (
    <div className="h-screen flex flex-col">
      {/* ─── 顶栏 ─── */}
      <div className="px-8 pt-8 pb-4 border-b border-nw-border">
        <div className="flex items-center justify-between">
          <div>
            <p className="nw-label mb-1">outline</p>
            <h1 className="text-xl font-semibold text-white tracking-wide">大纲规划</h1>
            <p className="text-xs text-nw-text-secondary mt-1">
              {stats.volumes} 卷 · {stats.chapters} 章 · {foreshadows.length} 条伏笔
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => tab === 'story' ? handleAddVolume() : handleAddForeshadow()}
              className="nw-btn nw-btn-primary flex items-center gap-1.5"
              disabled={!currentBookId}
            >
              + {tab === 'story' ? '新增卷' : '新增伏笔'}
            </button>
            <button
              onClick={handleAnalyzeSync}
              className="nw-btn flex items-center gap-1.5"
              disabled={syncAnalyzing || !currentBookId}
            >
              {syncAnalyzing ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
              ) : (
                <RefreshCw className="w-3.5 h-3.5" strokeWidth={1.5} />
              )}
              分析同步
            </button>
          </div>
        </div>
        <div className="nw-tabs mt-4">
          <button
            onClick={() => setTab('story')}
            className={`nw-tab flex items-center gap-2 ${tab === 'story' ? 'active' : ''}`}
          >
            <BookOpen className="w-3.5 h-3.5" strokeWidth={1.5} />
            故事线
          </button>
          <button
            onClick={() => setTab('foreshadow')}
            className={`nw-tab flex items-center gap-2 ${tab === 'foreshadow' ? 'active' : ''}`}
          >
            <Flag className="w-3.5 h-3.5" strokeWidth={1.5} />
            伏笔
            {foreshadows.length > 0 && (
              <span className="nw-badge ml-1">{foreshadows.length}</span>
            )}
          </button>
        </div>
      </div>

      {/* ─── 主体：左列表 + 右对话 ─── */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧面板 */}
        <div className="w-[40%] flex flex-col overflow-hidden border-r border-nw-border">
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-5 h-5 text-nw-text-muted animate-spin" />
                <span className="ml-2 text-sm text-nw-text-muted">加载中...</span>
              </div>
            ) : tab === 'story' ? (
              <StoryList
                volumes={volumes}
                expandedVolumes={expandedVolumes}
                selected={selected}
                onToggleVolume={toggleVolume}
                onSelectVolume={(v) => setSelected({ kind: 'volume', data: v })}
                onSelectChapter={(c, vTitle) =>
                  setSelected({ kind: 'chapter', data: c, volumeTitle: vTitle })
                }
                editingId={editingId}
                editForm={editForm}
                onStartEdit={handleStartEdit}
                onCancelEdit={handleCancelEdit}
                onSaveEdit={handleSaveEdit}
                onEditFormChange={setEditForm}
                onAddChapter={handleAddChapter}
                onDeleteVolume={handleDeleteVolume}
                onDeleteChapter={handleDeleteChapter}
                onMoveChapter={handleMoveChapter}
              />
            ) : (
              <ForeshadowList
                items={foreshadows}
                selected={selected}
                onSelect={(f) => setSelected({ kind: 'foreshadow', data: f })}
                onDeleteForeshadow={handleDeleteForeshadow}
                onCycleStatus={handleCycleForeshadowStatus}
              />
            )}
          </div>

          {/* 底部统计 */}
          <div className="border-t border-nw-border p-3 shrink-0">
            <div className="grid grid-cols-2 gap-2">
              <div className="nw-card p-2 text-center">
                <div className="text-[10px] text-nw-text-muted">总卷数</div>
                <div className="text-sm font-mono text-white">{stats.volumes}</div>
              </div>
              <div className="nw-card p-2 text-center">
                <div className="text-[10px] text-nw-text-muted">总章节</div>
                <div className="text-sm font-mono text-white">{stats.chapters}</div>
              </div>
            </div>
          </div>
        </div>

        {/* 右侧：对话 */}
        {currentBookId ? (
          <div className="w-[60%] flex flex-col overflow-hidden">
            <ChatPanel
              bookId={currentBookId}
              context="outline"
              suppressAutoSync={syncAnalyzing || syncOpen}
              onStageDataUpdate={handleStageDataUpdate}
              onDataUpdate={handleDataUpdate}
              entities={{
                characters: bookCharacters.map(c => ({ name: c.name, type: 'character' as const, id: c.id })),
                factions: [],
              }}
              hints={[
                '帮我规划每一卷的故事线',
                '设计第一卷的章节安排',
                '在第五章埋一个关键伏笔',
                '调整整体篇幅节奏',
              ]}
            />
          </div>
        ) : (
          <div className="w-[60%] flex items-center justify-center">
            <p className="text-sm text-nw-text-muted">请先选择一本书</p>
          </div>
        )}
      </div>

      {/* 同步弹窗 */}
      {syncOpen && syncAnalysis && (
        <ChatSyncModal
          bookId={currentBookId!}
          context="outline"
          analysis={syncAnalysis}
          onClose={() => {
            setSyncOpen(false)
            setSyncAnalysis(null)
          }}
          onApplied={handleSyncApplied}
        />
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   故事线列表（左侧）
   ═══════════════════════════════════════════════════════════════ */

interface StoryListProps {
  volumes: OutlineVolume[]
  expandedVolumes: Set<string>
  selected: SelectedItem
  onToggleVolume: (id: string) => void
  onSelectVolume: (v: OutlineVolume) => void
  onSelectChapter: (c: OutlineChapter, volumeTitle: string) => void
  editingId: string | null
  editForm: Record<string, any>
  onStartEdit: (id: string, form: Record<string, any>) => void
  onCancelEdit: () => void
  onSaveEdit: () => void
  onEditFormChange: (form: Record<string, any>) => void
  onAddChapter: (volumeId: string) => void
  onDeleteVolume: (volumeId: string) => void
  onDeleteChapter: (volumeId: string, chapterId: string) => void
  onMoveChapter: (volumeId: string, chapterId: string, direction: 'up' | 'down') => void
}

function StoryList({
  volumes,
  expandedVolumes,
  selected,
  onToggleVolume,
  onSelectVolume,
  onSelectChapter,
  editingId,
  editForm,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onEditFormChange,
  onAddChapter,
  onDeleteVolume,
  onDeleteChapter,
  onMoveChapter,
}: StoryListProps) {
  if (volumes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
        <BookOpen className="w-8 h-8 text-nw-text-muted mb-3" strokeWidth={1} />
        <p className="text-sm text-nw-text-muted mb-1">还没有大纲</p>
        <p className="text-xs text-nw-text-muted/60">
          在右侧与AI讨论，规划卷章结构和故事线
        </p>
      </div>
    )
  }

  return (
    <div className="py-2">
      {volumes.map((vol) => {
        const isExpanded = expandedVolumes.has(vol.id)
        const isVolSelected =
          selected?.kind === 'volume' && selected.data.id === vol.id

        return (
          <div key={vol.id}>
            {/* 卷头 */}
            <div
              className={`flex items-center gap-2 px-4 py-2.5 cursor-pointer transition-colors border-l-2 ${
                isVolSelected
                  ? 'bg-white/5 border-l-white'
                  : 'border-l-transparent hover:bg-white/[0.02]'
              }`}
              onClick={() => onSelectVolume(vol)}
            >
              <button
                className="p-0.5 text-nw-text-muted hover:text-white transition-colors shrink-0"
                onClick={(e) => {
                  e.stopPropagation()
                  onToggleVolume(vol.id)
                }}
              >
                {isExpanded ? (
                  <ChevronDown className="w-3.5 h-3.5" strokeWidth={1.5} />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" strokeWidth={1.5} />
                )}
              </button>
              <BookOpen className="w-3.5 h-3.5 text-white shrink-0" strokeWidth={1.5} />
              {editingId === vol.id ? (
                <div className="flex items-center gap-1 flex-1" onClick={(e) => e.stopPropagation()}>
                  <input
                    value={editForm.title || ''}
                    onChange={(e) => onEditFormChange({ ...editForm, title: e.target.value })}
                    className="flex-1 bg-nw-bg-secondary border border-nw-border rounded px-2 py-0.5 text-xs text-white"
                    placeholder="卷标题"
                  />
                  <button onClick={onSaveEdit} className="px-1.5 py-0.5 text-[10px] bg-nw-success/20 text-nw-success rounded">保存</button>
                  <button onClick={onCancelEdit} className="px-1.5 py-0.5 text-[10px] text-nw-text-muted rounded">取消</button>
                </div>
              ) : (
                <span className="text-xs font-medium text-white truncate flex-1">
                  第{vol.number}卷 · {vol.title}
                </span>
              )}
              <span className="text-[10px] text-nw-text-muted font-mono shrink-0">
                {vol.chapters.length}章
              </span>
              <button
                className="p-0.5 text-nw-text-muted hover:text-nw-success transition-colors shrink-0 text-[10px]"
                onClick={(e) => { e.stopPropagation(); onAddChapter(vol.id) }}
                title="新增章节"
              >+章节</button>
              <button
                className="p-0.5 text-nw-text-muted hover:text-white transition-colors shrink-0 text-[10px]"
                onClick={(e) => { e.stopPropagation(); onStartEdit(vol.id, { title: vol.title, story_arc: vol.story_arc }) }}
                title="编辑"
              >✎</button>
              <button
                className="p-0.5 text-nw-text-muted hover:text-red-400 transition-colors shrink-0 text-[10px]"
                onClick={(e) => { e.stopPropagation(); onDeleteVolume(vol.id) }}
                title="删除"
              >✕</button>
            </div>

            {/* 章节列表或 story_arc 纯文本展示 */}
            {isExpanded && (
              <div>
                {vol.chapters.length === 0 ? (
                  vol.story_arc ? (
                    <div className="px-6 py-3">
                      <p className="text-[11px] text-nw-text-muted mb-1.5">故事线概要：</p>
                      <p className="text-xs text-nw-text-secondary whitespace-pre-wrap leading-relaxed">
                        {vol.story_arc}
                      </p>
                    </div>
                  ) : (
                    <div className="px-12 py-2 text-[11px] text-nw-text-muted/50">
                      暂无章节
                    </div>
                  )
                ) : (
                  vol.chapters.map((ch, chIdx) => {
                    const isChSelected =
                      selected?.kind === 'chapter' && selected.data.id === ch.id
                    return (
                      <div
                        key={ch.id}
                        className={`flex items-center gap-2 pl-10 pr-4 py-2 cursor-pointer transition-colors border-l-2 ${
                          isChSelected
                            ? 'bg-white/5 border-l-white'
                            : 'border-l-transparent hover:bg-white/[0.02]'
                        }`}
                        onClick={() => onSelectChapter(ch, vol.title)}
                      >
                        <FileText
                          className="w-3 h-3 text-nw-text-muted shrink-0"
                          strokeWidth={1.5}
                        />
                        {editingId === ch.id ? (
                          <div className="flex items-center gap-1 flex-1" onClick={(e) => e.stopPropagation()}>
                            <input
                              value={editForm.title || ''}
                              onChange={(e) => onEditFormChange({ ...editForm, title: e.target.value })}
                              className="flex-1 bg-nw-bg-secondary border border-nw-border rounded px-2 py-0.5 text-xs text-white"
                              placeholder="章节标题"
                            />
                            <textarea
                              value={editForm.summary || ''}
                              onChange={(e) => onEditFormChange({ ...editForm, summary: e.target.value })}
                              className="flex-1 bg-nw-bg-secondary border border-nw-border rounded px-2 py-0.5 text-[10px] text-white"
                              placeholder="摘要"
                              rows={1}
                            />
                            <button onClick={onSaveEdit} className="px-1.5 py-0.5 text-[10px] bg-nw-success/20 text-nw-success rounded">保存</button>
                            <button onClick={onCancelEdit} className="px-1.5 py-0.5 text-[10px] text-nw-text-muted rounded">取消</button>
                          </div>
                        ) : (
                          <span className="text-xs text-nw-text-secondary truncate flex-1">
                            <span className="text-nw-text-muted font-mono mr-1.5">
                              {String(ch.number).padStart(2, '0')}
                            </span>
                            {ch.title}
                          </span>
                        )}
                        <button
                          className="p-0.5 text-nw-text-muted hover:text-white transition-colors shrink-0 text-[10px] opacity-0 group-hover:opacity-100"
                          onClick={(e) => { e.stopPropagation(); onMoveChapter(vol.id, ch.id, 'up') }}
                          disabled={chIdx === 0}
                          title="上移"
                        >↑</button>
                        <button
                          className="p-0.5 text-nw-text-muted hover:text-white transition-colors shrink-0 text-[10px] opacity-0 group-hover:opacity-100"
                          onClick={(e) => { e.stopPropagation(); onMoveChapter(vol.id, ch.id, 'down') }}
                          disabled={chIdx === vol.chapters.length - 1}
                          title="下移"
                        >↓</button>
                        <button
                          className="p-0.5 text-nw-text-muted hover:text-white transition-colors shrink-0 text-[10px]"
                          onClick={(e) => { e.stopPropagation(); onStartEdit(ch.id, { title: ch.title, summary: typeof ch.summary === 'string' ? ch.summary : '' }) }}
                          title="编辑"
                        >✎</button>
                        <button
                          className="p-0.5 text-nw-text-muted hover:text-red-400 transition-colors shrink-0 text-[10px]"
                          onClick={(e) => { e.stopPropagation(); onDeleteChapter(vol.id, ch.id) }}
                          title="删除"
                        >✕</button>
                      </div>
                    )
                  })
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   伏笔列表（左侧）
   ═══════════════════════════════════════════════════════════════ */

interface ForeshadowListProps {
  items: Foreshadow[]
  selected: SelectedItem
  onSelect: (f: Foreshadow) => void
  onDeleteForeshadow: (id: string) => void
  onCycleStatus: (id: string, currentStatus: string) => void
}

function ForeshadowList({ items, selected, onSelect, onDeleteForeshadow, onCycleStatus }: ForeshadowListProps) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
        <Flag className="w-8 h-8 text-nw-text-muted mb-3" strokeWidth={1} />
        <p className="text-sm text-nw-text-muted mb-1">还没有伏笔</p>
        <p className="text-xs text-nw-text-muted/60">
          在右侧与AI讨论，设计伏笔的埋设与回收
        </p>
      </div>
    )
  }

  const statusIcon = (s: Foreshadow['status']) => {
    if (s === 'resolved')
      return <CheckCircle2 className="w-3 h-3 text-green-400" strokeWidth={1.5} />
    if (s === 'active')
      return <Flag className="w-3 h-3 text-amber-400" strokeWidth={1.5} />
    return <Flag className="w-3 h-3 text-nw-text-muted" strokeWidth={1.5} />
  }

  return (
    <div className="py-2">
      {items.map((f) => {
        const isSelected =
          selected?.kind === 'foreshadow' && selected.data.id === f.id
        return (
          <div
            key={f.id}
            className={`flex items-start gap-2.5 px-4 py-3 cursor-pointer transition-colors border-l-2 ${
              isSelected
                ? 'bg-white/5 border-l-white'
                : 'border-l-transparent hover:bg-white/[0.02]'
            }`}
            onClick={() => onSelect(f)}
          >
            <span
              className="mt-0.5 shrink-0 cursor-pointer"
              onClick={(e) => { e.stopPropagation(); onCycleStatus(f.id, f.status) }}
              title={`点击切换状态 (当前: ${f.status})`}
            >{statusIcon(f.status)}</span>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">{f.purpose}</p>
              <p className="text-[11px] text-nw-text-muted mt-0.5 font-mono">
                第{f.start_chapter}章 → 第{f.end_chapter}章
                <span className="ml-2 text-nw-text-muted/50">[{f.status}]</span>
              </p>
            </div>
            <button
              className="p-0.5 text-nw-text-muted hover:text-red-400 transition-colors shrink-0 text-[10px]"
              onClick={(e) => { e.stopPropagation(); onDeleteForeshadow(f.id) }}
              title="删除"
            >✕</button>
          </div>
        )
      })}
    </div>
  )
}

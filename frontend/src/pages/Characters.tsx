import { useState, useMemo, useEffect, useCallback } from 'react'
import {
  Users,
  Plus,
  Search,
  User,
  Heart,
  Brain,
  Sparkles,
  Target,
  MessageCircle,
  Filter,
  Network,
  TrendingUp,
  ChevronRight,
  X,
  Loader2,
  CheckCircle2,
  RefreshCw,
  Pencil,
  Save,
  Trash2,
} from 'lucide-react'
import CharacterCard from '../components/CharacterCard'
import RelationGraph from '../components/RelationGraph'
import ChatPanel from '../components/ChatPanel'
import ChatSyncModal from '../components/ChatSyncModal'
import { useStore } from '../store'
import { api } from '../api/client'
import type { Character, GrowthNode, SyncFieldAnalysis } from '../types'

type ViewMode = 'grid' | 'graph'

const ROLE_FILTERS = ['全部', '主角', '女主', '反派/对手', '导师', '关键NPC']

export default function Characters() {
  const {
    currentBookId, characters, booksLoading,
    fetchCharacters, createCharacter, updateCharacter,
    deleteCharacter, notify,
  } = useStore()
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [roleFilter, setRoleFilter] = useState('全部')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [detailTab, setDetailTab] = useState<'profile' | 'growth'>('profile')
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [syncOpen, setSyncOpen] = useState(false)
  const [syncAnalyzing, setSyncAnalyzing] = useState(false)
  const [syncAnalysis, setSyncAnalysis] = useState<{ context: string; fields: SyncFieldAnalysis[]; analyzed_message_count: number } | null>(null)

  // Inline editing
  const [editingField, setEditingField] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [savingField, setSavingField] = useState(false)

  // New character form
  const [newChar, setNewChar] = useState({
    name: '',
    role: '主角',
    tag: '',
    description: '',
  })

  // Fetch characters when book changes (only after books list is loaded)
  useEffect(() => {
    if (!booksLoading && currentBookId) {
      setLoading(true)
      fetchCharacters(currentBookId).finally(() => setLoading(false))
    }
  }, [currentBookId, booksLoading]) // eslint-disable-line react-hooks/exhaustive-deps

  const bookCharacters = characters.filter((c) => c.book_id === currentBookId)

  const filteredCharacters = useMemo(() => {
    let result = bookCharacters
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          c.tag.toLowerCase().includes(q) ||
          c.role.toLowerCase().includes(q)
      )
    }
    if (roleFilter !== '全部') {
      // 宽松匹配：支持同义词（男主↔主角）+ 包含匹配
      const aliasMap: Record<string, string[]> = {
        '主角': ['主角', '男主', '男主/女主'],
        '女主': ['女主', '女主角'],
        '反派/对手': ['反派/对手', '反派', '对手', ' antagonist'],
        '导师': ['导师', '老师', '师父', 'mentor'],
        '关键NPC': ['关键NPC', 'NPC', '重要配角'],
      }
      const aliases = aliasMap[roleFilter] || [roleFilter]
      result = result.filter((c) => aliases.some((a) => c.role.includes(a)))
    }
    return result
  }, [bookCharacters, searchQuery, roleFilter])

  const selectedChar = filteredCharacters.find((c) => c.id === selectedId) || null

  const handleCreateCharacter = async () => {
    if (!currentBookId || !newChar.name.trim()) return
    setCreating(true)
    await createCharacter(currentBookId, {
      name: newChar.name,
      role: newChar.role,
      tag: newChar.tag,
      background: newChar.description,
    })
    setShowCreateModal(false)
    setNewChar({ name: '', role: '主角', tag: '', description: '' })
    setCreating(false)
  }

  // Delete character
  const handleDeleteCharacter = useCallback(async (charId: string, charName: string) => {
    if (!currentBookId) return
    if (!window.confirm(`确定删除角色「${charName}」吗？此操作不可恢复。`)) return
    const ok = await deleteCharacter(currentBookId, charId)
    if (ok) {
      if (selectedId === charId) setSelectedId(null)
      fetchCharacters(currentBookId)
    }
  }, [currentBookId, selectedId, deleteCharacter, fetchCharacters])

  // Handle chat stage data update - refresh character list
  const handleStageDataUpdate = useCallback((_data: Record<string, unknown>) => {
    if (currentBookId) {
      fetchCharacters(currentBookId)
    }
  }, [currentBookId, fetchCharacters])

  // Handle structured data updates from chat
  const handleDataUpdate = useCallback(async (updates: Record<string, string>, ctx: string) => {
    if (!currentBookId || !updates) return
    // If we have a name update, create or update a character
    if (updates.name) {
      // Try to find existing character by name
      const existing = characters.find(c => c.name === updates.name)
      if (existing) {
        await updateCharacter(currentBookId, existing.id, {
          personality: updates.personality || existing.personality,
          background: updates.background || existing.background,
          motivation: updates.motivation || existing.motivation,
          abilities: updates.abilities || existing.abilities,
          role: updates.role || existing.role,
        })
      } else {
        await createCharacter(currentBookId, {
          name: updates.name,
          role: updates.role || '待定',
          personality: updates.personality || '',
          background: updates.background || '',
          motivation: updates.motivation || '',
          abilities: updates.abilities || '',
        })
      }
      fetchCharacters(currentBookId)
      notify('对话已更新角色数据', 'success')
    }
  }, [currentBookId, characters, updateCharacter, createCharacter, fetchCharacters, notify])

  // Confirm current stage
  const handleConfirm = useCallback(async () => {
    if (!currentBookId || confirming) return
    setConfirming(true)
    try {
      const { api } = await import('../api/client')
      const res = await api.confirmChatStage(currentBookId, 'character')
      if (res.success) {
        notify(res.message || '角色成果已确认', 'success')
        setConfirmed(true)
        fetchCharacters(currentBookId)
        setTimeout(() => setConfirmed(false), 5000)
      }
    } catch {
      notify('确认失败，请重试', 'error')
    } finally {
      setConfirming(false)
    }
  }, [currentBookId, confirming, notify, fetchCharacters])

  // Sync: analyze chat → structured data
  const handleAnalyzeSync = useCallback(async () => {
    if (!currentBookId || syncAnalyzing) return
    setSyncAnalyzing(true)
    try {
      const res = await api.analyzeSync(currentBookId, 'character')
      if (res.fields.length === 0) {
        notify('暂无可同步的内容，请先与AI讨论角色设定', 'info')
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

  // Sync: after applying, refresh character list
  const handleSyncApplied = useCallback(() => {
    if (currentBookId) fetchCharacters(currentBookId)
  }, [currentBookId, fetchCharacters])

  // Inline edit: start editing a field
  const startEditField = useCallback((field: string, value: string) => {
    setEditingField(field)
    setEditValue(value || '')
  }, [])

  // Inline edit: save field value
  const saveEditField = useCallback(async () => {
    if (!currentBookId || !selectedChar || !editingField) return
    setSavingField(true)
    try {
      await updateCharacter(currentBookId, selectedChar.id, { [editingField]: editValue })
      await fetchCharacters(currentBookId)
    } catch {
      notify('保存失败', 'error')
    } finally {
      setSavingField(false)
      setEditingField(null)
      setEditValue('')
    }
  }, [currentBookId, selectedChar, editingField, editValue, updateCharacter, fetchCharacters, notify])

  // Inline edit: cancel editing
  const cancelEditField = useCallback(() => {
    setEditingField(null)
    setEditValue('')
  }, [])

  // Render an editable field row
  const renderEditField = (label: string, field: string, value: string, icon: React.ReactNode, isItalic?: boolean) => (
    <div>
      <h4 className="nw-label mb-1.5 flex items-center gap-1.5">
        {icon}
        {label}
        <button
          onClick={() => editingField === field ? cancelEditField() : startEditField(field, value)}
          className="ml-auto p-0.5 text-nw-text-muted hover:text-white transition-colors"
        >
          {editingField === field ? (
            <X className="w-3 h-3" strokeWidth={1.5} />
          ) : (
            <Pencil className="w-3 h-3" strokeWidth={1.5} />
          )}
        </button>
      </h4>
      {editingField === field ? (
        <div className="space-y-1.5">
          <textarea
            className="nw-textarea w-full min-h-[60px] text-xs"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            autoFocus
          />
          <div className="flex gap-1.5">
            <button
              onClick={saveEditField}
              disabled={savingField}
              className="flex items-center gap-1 px-2 py-1 text-[10px] border border-white/30 text-white hover:bg-white/10 transition-colors"
            >
              {savingField ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <Save className="w-2.5 h-2.5" strokeWidth={1.5} />}
              保存
            </button>
            <button
              onClick={cancelEditField}
              className="px-2 py-1 text-[10px] border border-nw-border text-nw-text-muted hover:text-white transition-colors"
            >
              取消
            </button>
          </div>
        </div>
      ) : isItalic ? (
        <p className="text-xs text-white italic border-l-2 border-white pl-3">
          「{value}」
        </p>
      ) : (
        <p className="text-xs text-nw-text-secondary leading-relaxed">{value}</p>
      )}
    </div>
  )

  // Growth arc timeline / SVG
  function GrowthArcChart({ arc }: { arc: GrowthNode[] }) {
    const width = 500
    const height = 120
    const padding = 30
    const chartWidth = width - padding * 2
    const chartHeight = height - padding - 10

    const points = arc.map((node, i) => {
      const x = padding + (chartWidth / (arc.length - 1 || 1)) * i
      const progress = i / (arc.length - 1 || 1)
      const y = padding + chartHeight - Math.sin(progress * Math.PI) * chartHeight * 0.7
      return { x, y, node }
    })

    const path = points
      .map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`))
      .join(' ')

    return (
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <line
          x1={padding}
          y1={padding + chartHeight}
          x2={width - padding}
          y2={padding + chartHeight}
          stroke="#222222"
          strokeWidth="1"
        />
        <path d={path} fill="none" stroke="#ffffff" strokeWidth="1.5" />
        {points.map((p, i) => (
          <g key={i}>
            <line
              x1={p.x}
              y1={p.y}
              x2={p.x}
              y2={padding + chartHeight}
              stroke="#222222"
              strokeWidth="1"
              strokeDasharray="2,2"
            />
            <circle cx={p.x} cy={p.y} r="5" fill="#ffffff" stroke="#0a0a0a" strokeWidth="2" />
            <text
              x={p.x}
              y={p.y - 10}
              textAnchor="middle"
              className="fill-white text-[9px] font-medium"
            >
              {p.node.milestone}
            </text>
            <text
              x={p.x}
              y={padding + chartHeight + 14}
              textAnchor="middle"
              className="fill-nw-text-muted text-[9px] font-mono"
            >
              Ch.{p.node.chapter_range}
            </text>
          </g>
        ))}
      </svg>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="px-8 pt-8 pb-4 border-b border-nw-border">
        <div className="flex items-start justify-between">
          <div>
            <p className="nw-label mb-1">characters</p>
            <h1 className="text-xl font-semibold text-white tracking-wide">角色工坊</h1>
            <p className="text-xs text-nw-text-secondary mt-1">
              当前项目 · {bookCharacters.length} 位角色
              {loading && <span className="ml-2 text-nw-text-muted">(加载中...)</span>}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Confirm button */}
            <button
              onClick={handleConfirm}
              className={`nw-btn nw-btn-primary flex items-center gap-1.5 ${confirmed ? '!border-nw-success !text-nw-success' : ''}`}
              disabled={confirming || !currentBookId}
            >
              {confirming ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
              ) : confirmed ? (
                <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
              )}
              {confirmed ? '已确认' : '确认当前成果'}
            </button>
            {/* Sync button */}
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
            {/* View toggle */}
            <div className="flex border border-nw-border">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-1.5 text-xs transition-colors flex items-center gap-1.5 ${
                  viewMode === 'grid' ? 'bg-white text-nw-bg' : 'text-nw-text-secondary hover:text-white'
                }`}
              >
                <Users className="w-3 h-3" strokeWidth={1.5} />
                列表
              </button>
              <button
                onClick={() => setViewMode('graph')}
                className={`px-3 py-1.5 text-xs transition-colors flex items-center gap-1.5 ${
                  viewMode === 'graph' ? 'bg-white text-nw-bg' : 'text-nw-text-secondary hover:text-white'
                }`}
              >
                <Network className="w-3 h-3" strokeWidth={1.5} />
                关系图
              </button>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="nw-btn nw-btn-primary"
            >
              <Plus className="w-3.5 h-3.5" strokeWidth={2} />
              新建角色
            </button>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-4 mt-4">
          {/* Search */}
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-nw-text-muted" strokeWidth={1.5} />
            <input
              type="text"
              className="nw-input pl-9"
              placeholder="搜索角色名、标签..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Role filter */}
          <div className="flex items-center gap-1">
            <Filter className="w-3.5 h-3.5 text-nw-text-muted" strokeWidth={1.5} />
            <div className="flex gap-1">
              {ROLE_FILTERS.map((role) => (
                <button
                  key={role}
                  onClick={() => setRoleFilter(role)}
                  className={`px-2 py-1 text-[11px] border transition-colors ${
                    roleFilter === role
                      ? 'border-white text-white bg-white/5'
                      : 'border-transparent text-nw-text-secondary hover:text-white'
                  }`}
                >
                  {role}
                </button>
              ))}
            </div>
          </div>

          <div className="ml-auto text-[11px] text-nw-text-muted">
            共 {filteredCharacters.length} 位角色
          </div>
        </div>
      </div>

      {/* Confirmed banner */}
      {confirmed && (
        <div className="px-8 py-2 bg-nw-success/10 border-b border-nw-success/20 flex items-center gap-2 text-xs text-nw-success">
          <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
          角色成果已确认，数据已刷新
        </div>
      )}

      {/* Main Content: Left panel (40%) + ChatPanel (60%) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Character list / graph + Detail (40%) */}
        <div className="w-[40%] flex flex-col overflow-hidden border-r border-nw-border">
          {/* Character grid / graph */}
          <div className="flex-1 overflow-y-auto p-4">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-5 h-5 text-nw-text-muted animate-spin" />
                <span className="ml-2 text-sm text-nw-text-muted">加载角色中...</span>
              </div>
            ) : viewMode === 'grid' ? (
              <div className="grid grid-cols-2 gap-3">
                {filteredCharacters.map((char) => (
                  <CharacterCard
                    key={char.id}
                    character={char}
                    selected={selectedId === char.id}
                    onClick={() => setSelectedId(selectedId === char.id ? null : char.id)}
                  />
                ))}
                {filteredCharacters.length === 0 && (
                  <div className="col-span-2 text-center py-12 text-nw-text-muted text-sm">
                    未找到匹配的角色
                  </div>
                )}
                {/* Add new card */}
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="nw-card p-4 flex items-center justify-center gap-2 text-nw-text-muted hover:text-white hover:border-white transition-all group"
                >
                  <Plus className="w-4 h-4 group-hover:scale-110 transition-transform" strokeWidth={1.5} />
                  <span className="text-xs">添加新角色</span>
                </button>
              </div>
            ) : (
              <div className="nw-card h-full flex items-center justify-center p-4">
                <RelationGraph characters={filteredCharacters} width={420} height={340} />
              </div>
            )}
          </div>

          {/* Detail panel (below character grid) */}
          {selectedChar && (
            <div className="border-t border-nw-border bg-nw-bg-secondary flex flex-col max-h-[50%] overflow-hidden">
              {/* Panel header */}
              <div className="px-4 py-3 border-b border-nw-border flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                  <div
                    className="w-8 h-8 flex items-center justify-center text-xs font-bold border border-white/10"
                    style={{ backgroundColor: selectedChar.avatar_color }}
                  >
                    {selectedChar.name[0]}
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-white">{selectedChar.name}</h3>
                    <p className="text-[10px] text-nw-text-muted">{selectedChar.role} · {selectedChar.tag}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleDeleteCharacter(selectedChar.id, selectedChar.name)}
                    className="p-1 text-nw-text-muted hover:text-red-400 transition-colors"
                    title="删除角色"
                  >
                    <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                  </button>
                  <button
                    onClick={() => setSelectedId(null)}
                    className="p-1 text-nw-text-muted hover:text-white transition-colors"
                  >
                    <X className="w-4 h-4" strokeWidth={1.5} />
                  </button>
                </div>
              </div>

              {/* Detail tabs */}
              <div className="nw-tabs px-4 shrink-0">
                <button
                  className={`nw-tab ${detailTab === 'profile' ? 'active' : ''}`}
                  onClick={() => setDetailTab('profile')}
                >
                  档案
                </button>
                <button
                  className={`nw-tab ${detailTab === 'growth' ? 'active' : ''}`}
                  onClick={() => setDetailTab('growth')}
                >
                  成长弧线
                </button>
              </div>

              {/* Detail content */}
              <div className="flex-1 overflow-y-auto p-4">
                {detailTab === 'profile' && (
                  <div className="space-y-4">
                    {renderEditField('角色名', 'name', selectedChar.name,
                      <User className="w-3 h-3" strokeWidth={1.5} />)}
                    {renderEditField('角色定位', 'role', selectedChar.role,
                      <Target className="w-3 h-3" strokeWidth={1.5} />)}
                    {renderEditField('标签', 'tag', selectedChar.tag,
                      <Filter className="w-3 h-3" strokeWidth={1.5} />)}
                    {renderEditField('外貌描写', 'portrait', selectedChar.portrait,
                      <User className="w-3 h-3" strokeWidth={1.5} />)}
                    {renderEditField('性格特质', 'personality', selectedChar.personality,
                      <Brain className="w-3 h-3" strokeWidth={1.5} />)}
                    {renderEditField('背景故事', 'background', selectedChar.background,
                      <Heart className="w-3 h-3" strokeWidth={1.5} />)}
                    {renderEditField('核心动机', 'motivation', selectedChar.motivation,
                      <Target className="w-3 h-3" strokeWidth={1.5} />)}
                    {renderEditField('能力设定', 'abilities', selectedChar.abilities,
                      <Sparkles className="w-3 h-3" strokeWidth={1.5} />)}
                    {renderEditField('口头禅', 'catchphrase', selectedChar.catchphrase,
                      <MessageCircle className="w-3 h-3" strokeWidth={1.5} />, true)}
                    <div>
                      <h4 className="nw-label mb-1.5 flex items-center gap-1.5">
                        <Users className="w-3 h-3" strokeWidth={1.5} />
                        人物关系
                      </h4>
                      <div className="space-y-1.5">
                        {selectedChar.relationships.map((rel, i) => (
                          <div
                            key={i}
                            className="flex items-center justify-between p-2 border border-nw-border hover:border-nw-border-light transition-colors"
                          >
                            <div>
                              <span className="text-xs text-white">{rel.target_name}</span>
                              <span className="text-[10px] text-nw-text-muted ml-2">{rel.type}</span>
                            </div>
                            <ChevronRight className="w-3 h-3 text-nw-text-muted" strokeWidth={1.5} />
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {detailTab === 'growth' && (
                  <div className="space-y-4">
                    <div>
                      <h4 className="nw-label mb-2 flex items-center gap-1.5">
                        <TrendingUp className="w-3 h-3" strokeWidth={1.5} />
                        成长弧线
                      </h4>
                      <div className="nw-card p-2 -mx-1">
                        <GrowthArcChart arc={selectedChar.growth_arc} />
                      </div>
                    </div>
                    <div>
                      <h4 className="nw-label mb-2">成长节点</h4>
                      <div className="space-y-2">
                        {selectedChar.growth_arc.map((node) => (
                          <div
                            key={node.id}
                            className="p-2.5 border border-nw-border hover:border-nw-border-light transition-colors"
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <span className="nw-badge nw-badge-white">{node.milestone}</span>
                              <span className="text-[10px] text-nw-text-muted font-mono">
                                Ch.{node.chapter_range}
                              </span>
                            </div>
                            <p className="text-xs text-nw-text-secondary">{node.description}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right: ChatPanel (60%) */}
        {currentBookId ? (
          <div className="w-[60%] flex flex-col overflow-hidden">
            <ChatPanel
              bookId={currentBookId}
              context="character"
              suppressAutoSync={syncAnalyzing || syncOpen}
              onStageDataUpdate={handleStageDataUpdate}
              onDataUpdate={handleDataUpdate}
              entities={{
                characters: bookCharacters.map(c => ({ name: c.name, type: 'character' as const, id: c.id })),
                factions: [],
              }}
              hints={[
                '帮我设计主角的性格和背景',
                '创建反派角色，要有深度',
                '设计角色之间的关系网',
                '为现有角色添加成长弧线',
              ]}
            />
          </div>
        ) : (
          <div className="w-[60%] flex items-center justify-center">
            <p className="text-sm text-nw-text-muted">请先选择一本书</p>
          </div>
        )}
      </div>

      {/* Sync Modal */}
      {syncOpen && syncAnalysis && (
        <ChatSyncModal
          bookId={currentBookId!}
          context="character"
          analysis={syncAnalysis}
          onClose={() => { setSyncOpen(false); setSyncAnalysis(null) }}
          onApplied={handleSyncApplied}
        />
      )}

      {/* Create Character Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 nw-fade-in">
          <div className="nw-card w-[480px] max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-5 py-4 border-b border-nw-border">
              <div>
                <h3 className="text-sm font-medium text-white">新建角色</h3>
                <p className="text-[11px] text-nw-text-muted mt-0.5">
                  为当前项目创建新角色
                </p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1 text-nw-text-muted hover:text-white transition-colors"
              >
                <X className="w-4 h-4" strokeWidth={1.5} />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="nw-label block mb-1.5">角色姓名</label>
                  <input
                    type="text"
                    className="nw-input"
                    placeholder="输入姓名..."
                    value={newChar.name}
                    onChange={(e) => setNewChar({ ...newChar, name: e.target.value })}
                    autoFocus
                  />
                </div>
                <div>
                  <label className="nw-label block mb-1.5">角色定位</label>
                  <select
                    className="nw-input"
                    value={newChar.role}
                    onChange={(e) => setNewChar({ ...newChar, role: e.target.value })}
                  >
                    <option>主角</option>
                    <option>女主</option>
                    <option>反派/对手</option>
                    <option>导师</option>
                    <option>配角</option>
                    <option>关键NPC</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="nw-label block mb-1.5">标签 / 关键词</label>
                <input
                  type="text"
                  className="nw-input"
                  placeholder="如：少年成长/星辰师"
                  value={newChar.tag}
                  onChange={(e) => setNewChar({ ...newChar, tag: e.target.value })}
                />
              </div>
              <div>
                <label className="nw-label block mb-1.5">简短描述</label>
                <textarea
                  className="nw-textarea h-20"
                  placeholder="简要描述角色的外貌、性格和背景..."
                  value={newChar.description}
                  onChange={(e) => setNewChar({ ...newChar, description: e.target.value })}
                />
              </div>
              <div className="pt-2 border-t border-nw-border">
                <div className="flex items-start gap-2 text-[11px] text-nw-text-muted">
                  <Sparkles className="w-3.5 h-3.5 text-nw-text-secondary mt-0.5 shrink-0" strokeWidth={1.5} />
                  <p>
                    AI 将基于描述自动补全人物档案，包括性格、动机、能力和成长弧线。
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-nw-border">
              <button onClick={() => setShowCreateModal(false)} className="nw-btn" disabled={creating}>
                取消
              </button>
              <button
                onClick={handleCreateCharacter}
                className="nw-btn nw-btn-primary"
                disabled={!newChar.name.trim() || creating}
              >
                {creating ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" strokeWidth={1.5} />
                )}
                AI 生成
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

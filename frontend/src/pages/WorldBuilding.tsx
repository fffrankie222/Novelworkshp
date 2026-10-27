import { useState, useMemo, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Mountain,
  Swords,
  Zap,
  Clock,
  Scale,
  Edit3,
  Eye,
  Save,
  Network,
  Loader2,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react'
import ChatPanel from '../components/ChatPanel'
import ChatSyncModal from '../components/ChatSyncModal'
import { useStore } from '../store'
import { api } from '../api/client'
import { mockWorldBuilding } from '../data/mock'
import type { WorldBuilding as WorldBuildingType, FactionNode, SyncFieldAnalysis } from '../types'

const TABS = [
  { key: 'geography', label: '地理环境', icon: Mountain },
  { key: 'factions', label: '势力分布', icon: Swords },
  { key: 'power_system', label: '力量体系', icon: Zap },
  { key: 'history', label: '历史年表', icon: Clock },
  { key: 'social_rules', label: '社会规则', icon: Scale },
]

// Faction relation graph (pure SVG, B&W)
function FactionRelationGraph({
  factions,
  width = 380,
  height = 320,
}: {
  factions: FactionNode[]
  width?: number
  height?: number
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const cx = width / 2
  const cy = height / 2 - 10
  const radius = Math.min(width, height) * 0.32

  const nodes = factions.map((f, i) => {
    const angle = (2 * Math.PI * i) / factions.length - Math.PI / 2
    return {
      ...f,
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    }
  })

  const factionMap = new Map(nodes.map((n) => [n.name, n]))
  const edges: { source: FactionNode & { x: number; y: number }; target: FactionNode & { x: number; y: number }; type: string }[] = []

  nodes.forEach((node) => {
    node.relations.forEach((rel) => {
      const target = factionMap.get(rel.target)
      if (target) {
        const key = [node.id, target.id].sort().join('|')
        if (!edges.some((e) => [e.source.id, e.target.id].sort().join('|') === key)) {
          edges.push({ source: node, target, type: rel.type })
        }
      }
    })
  })

  const isHighlighted = (id: string) => selectedId === id
  const isEdgeHighlighted = (sId: string, tId: string) =>
    selectedId && (selectedId === sId || selectedId === tId)

  const selectedFaction = selectedId ? nodes.find((n) => n.id === selectedId) : null

  return (
    <div className="relative w-full h-full flex flex-col">
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="mx-auto block">
        <text
          x={cx}
          y={cy}
          textAnchor="middle"
          dominantBaseline="middle"
          className="fill-nw-text-muted text-[8px]"
          style={{ textTransform: 'uppercase', letterSpacing: '0.15em' }}
        >
          势力关系
        </text>

        {edges.map((edge, i) => {
          const highlighted = isEdgeHighlighted(edge.source.id, edge.target.id)
          const isHostile = edge.type.includes('对抗') || edge.type.includes('竞争')
          const midX = (edge.source.x + edge.target.x) / 2
          const midY = (edge.source.y + edge.target.y) / 2

          return (
            <g key={i} className="pointer-events-none">
              <line
                x1={edge.source.x}
                y1={edge.source.y}
                x2={edge.target.x}
                y2={edge.target.y}
                stroke={highlighted ? '#ffffff' : '#333333'}
                strokeWidth={highlighted ? 1.5 : 1}
                strokeDasharray={isHostile ? '3,3' : '0'}
                opacity={highlighted ? 1 : 0.5}
              />
              {highlighted && (
                <>
                  <rect
                    x={midX - 22}
                    y={midY - 7}
                    width="44"
                    height="14"
                    fill="#0a0a0a"
                    stroke="#ffffff"
                    strokeWidth="0.5"
                  />
                  <text
                    x={midX}
                    y={midY + 3}
                    textAnchor="middle"
                    className="fill-white text-[8px] pointer-events-none"
                  >
                    {edge.type}
                  </text>
                </>
              )}
            </g>
          )
        })}

        {nodes.map((node) => {
          const highlighted = isHighlighted(node.id)
          return (
            <g
              key={node.id}
              onClick={() => setSelectedId(selectedId === node.id ? null : node.id)}
              className="cursor-pointer"
            >
              {highlighted && (
                <rect
                  x={node.x - 42}
                  y={node.y - 16}
                  width="84"
                  height="32"
                  fill="none"
                  stroke="#ffffff"
                  strokeWidth="1"
                />
              )}
              <rect
                x={node.x - 36}
                y={node.y - 12}
                width="72"
                height="24"
                fill={highlighted ? '#ffffff' : '#141414'}
                stroke={highlighted ? '#ffffff' : '#222222'}
                strokeWidth="1"
              />
              <text
                x={node.x}
                y={node.y + 3}
                textAnchor="middle"
                className="text-[10px] pointer-events-none"
                fill={highlighted ? '#0a0a0a' : '#ffffff'}
              >
                {node.name}
              </text>
            </g>
          )
        })}
      </svg>

      <div className="mt-2 px-3 py-2 border-t border-nw-border min-h-[60px]">
        {selectedFaction ? (
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-medium text-white">{selectedFaction.name}</span>
            </div>
            <p className="text-[11px] text-nw-text-secondary mb-2">{selectedFaction.description}</p>
            <div className="space-y-1">
              {selectedFaction.relations.map((rel, i) => (
                <div key={i} className="flex items-center gap-2 text-[10px]">
                  <span className="w-4 h-px bg-nw-border-light" />
                  <span className="text-white">{rel.target}</span>
                  <span className="text-nw-text-muted">·</span>
                  <span className="text-nw-text-secondary">{rel.type}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-[11px] text-nw-text-muted text-center">
            点击势力方块查看详情
          </p>
        )}
      </div>
    </div>
  )
}

export default function WorldBuilding() {
  const { currentBookId, worldData, fetchWorld, saveWorld, notify, booksLoading, characters } = useStore()
  const [activeTab, setActiveTab] = useState('geography')
  const [viewMode, setViewMode] = useState<'edit' | 'preview'>('preview')
  const [editContent, setEditContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [confirming, setConfirming] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [graphExpanded, setGraphExpanded] = useState(false)
  const [syncOpen, setSyncOpen] = useState(false)
  const [syncAnalyzing, setSyncAnalyzing] = useState(false)
  const [syncAnalysis, setSyncAnalysis] = useState<{ context: string; fields: SyncFieldAnalysis[]; analyzed_message_count: number } | null>(null)

  // Fetch world data when book changes (only after books list is loaded)
  useEffect(() => {
    if (!booksLoading && currentBookId) {
      setLoading(true)
      fetchWorld(currentBookId).finally(() => setLoading(false))
    }
  }, [currentBookId, booksLoading])

  // Sync edit content when tab changes or data loads
  const displayData = worldData || mockWorldBuilding

  useEffect(() => {
    setEditContent(getContent(activeTab))
  }, [activeTab, worldData]) // eslint-disable-line react-hooks/exhaustive-deps

  const getContent = (tab: string): string => {
    const data = worldData || mockWorldBuilding
    switch (tab) {
      case 'geography':
        return data.geography
      case 'factions':
        return data.factions
      case 'power_system':
        return data.power_system
      case 'history':
        return data.history
      case 'social_rules':
        return data.social_rules
      default:
        return ''
    }
  }

  const handleTabChange = (tab: string) => {
    setActiveTab(tab)
  }

  const handleSave = async () => {
    if (!currentBookId) return
    setSaving(true)
    const updated: Partial<WorldBuildingType> = { [activeTab]: editContent } as Partial<WorldBuildingType>
    await saveWorld(currentBookId, updated)
    setViewMode('preview')
    setSaving(false)
  }

  // Handle chat stage data update - refresh left panel data
  const handleStageDataUpdate = useCallback((data: Record<string, unknown>) => {
    // If stage_data contains world fields, update local state
    const fields = ['geography', 'factions', 'power_system', 'history', 'social_rules']
    const hasWorldData = fields.some((f) => data[f] !== undefined)
    if (hasWorldData && currentBookId) {
      fetchWorld(currentBookId)
    }
  }, [currentBookId, fetchWorld])

  // Handle structured data updates extracted from chat
  const handleDataUpdate = useCallback(async (updates: Record<string, string>, ctx: string) => {
    if (!currentBookId || !updates || Object.keys(updates).length === 0) return
    // Apply updates to world data via API
    await saveWorld(currentBookId, updates as Partial<WorldBuildingType>)
    // Refresh from server
    fetchWorld(currentBookId)
    notify('对话已更新世界观数据', 'success')
  }, [currentBookId, saveWorld, fetchWorld, notify])

  // Confirm current stage
  const handleConfirm = useCallback(async () => {
    if (!currentBookId || confirming) return
    setConfirming(true)
    try {
      const { api } = await import('../api/client')
      const res = await api.confirmChatStage(currentBookId, 'worldbuilding')
      if (res.success) {
        notify(res.message || '世界观成果已确认', 'success')
        setConfirmed(true)
        fetchWorld(currentBookId)
        setTimeout(() => setConfirmed(false), 5000)
      }
    } catch {
      notify('确认失败，请重试', 'error')
    } finally {
      setConfirming(false)
    }
  }, [currentBookId, confirming, notify, fetchWorld])

  // Sync: analyze chat → structured data
  const handleAnalyzeSync = useCallback(async () => {
    if (!currentBookId || syncAnalyzing) return
    setSyncAnalyzing(true)
    try {
      const res = await api.analyzeSync(currentBookId, 'worldbuilding')
      if (res.fields.length === 0) {
        notify('暂无可同步的内容，请先与AI讨论世界观设定', 'info')
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

  // Sync: after applying, refresh world data
  const handleSyncApplied = useCallback(() => {
    if (currentBookId) fetchWorld(currentBookId)
  }, [currentBookId, fetchWorld])

  const wordCount = useMemo(() => {
    return Object.values(displayData)
      .filter((v) => typeof v === 'string')
      .reduce((sum, v) => sum + (v as string).length, 0)
  }, [displayData])

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="px-8 pt-8 pb-4 border-b border-nw-border">
        <div className="flex items-start justify-between">
          <div>
            <p className="nw-label mb-1">world building</p>
            <h1 className="text-xl font-semibold text-white tracking-wide">
              世界观构建
            </h1>
            <p className="text-xs text-nw-text-secondary mt-1">
              当前项目 · 共 {wordCount} 字设定
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
            {/* View mode toggle */}
            <div className="flex border border-nw-border">
              <button
                onClick={() => setViewMode('preview')}
                className={`px-3 py-1.5 text-xs transition-colors flex items-center gap-1.5 ${
                  viewMode === 'preview'
                    ? 'bg-white text-nw-bg'
                    : 'text-nw-text-secondary hover:text-white'
                }`}
              >
                <Eye className="w-3 h-3" strokeWidth={1.5} />
                预览
              </button>
              <button
                onClick={() => setViewMode('edit')}
                className={`px-3 py-1.5 text-xs transition-colors flex items-center gap-1.5 ${
                  viewMode === 'edit'
                    ? 'bg-white text-nw-bg'
                    : 'text-nw-text-secondary hover:text-white'
                }`}
              >
                <Edit3 className="w-3 h-3" strokeWidth={1.5} />
                编辑
              </button>
            </div>
            {viewMode === 'edit' && (
              <button onClick={handleSave} className="nw-btn nw-btn-primary" disabled={saving}>
                {saving ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
                ) : (
                  <Save className="w-3.5 h-3.5" strokeWidth={1.5} />
                )}
                保存
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Confirmed banner */}
      {confirmed && (
        <div className="px-8 py-2 bg-nw-success/10 border-b border-nw-success/20 flex items-center gap-2 text-xs text-nw-success">
          <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
          世界观成果已确认，数据已刷新
        </div>
      )}

      {/* Main Content: Left panel (40%) + ChatPanel (60%) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Tabs + Content + Faction Graph (40%) */}
        <div className="w-[40%] flex flex-col overflow-hidden border-r border-nw-border">
          {/* Tabs */}
          <div className="nw-tabs px-6 shrink-0">
            {TABS.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.key}
                  onClick={() => handleTabChange(tab.key)}
                  className={`nw-tab flex items-center gap-2 ${
                    activeTab === tab.key ? 'active' : ''
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" strokeWidth={1.5} />
                  {tab.label}
                </button>
              )
            })}
          </div>

          {/* Content Area — 弹性占据主要空间 */}
          <div className="flex-1 overflow-y-auto p-6 min-h-[120px]">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-5 h-5 text-nw-text-muted animate-spin" />
              </div>
            ) : viewMode === 'edit' ? (
              <textarea
                className="nw-textarea w-full h-full resize-none font-mono text-xs leading-relaxed"
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                placeholder="在此编辑 Markdown 格式的世界观设定..."
              />
            ) : (
              <div className="markdown-preview">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {getContent(activeTab)}
                </ReactMarkdown>
              </div>
            )}
          </div>

          {/* Faction Graph — 可折叠，默认收起 */}
          <div className="border-t border-nw-border shrink-0">
            <button
              onClick={() => setGraphExpanded(!graphExpanded)}
              className="w-full px-4 py-2 flex items-center justify-between hover:bg-white/5 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-white" strokeWidth={1.5} />
                <span className="text-xs font-medium text-white">势力关系图</span>
                <span className="nw-label ml-1">
                  {(displayData.factions_graph || []).length} 个势力
                </span>
              </div>
              <span className="text-[10px] text-nw-text-muted">
                {graphExpanded ? '▼ 收起' : '▲ 展开'}
              </span>
            </button>
            {graphExpanded && (
              <div className="px-3 py-2">
                <FactionRelationGraph factions={displayData.factions_graph} width={340} height={200} />
              </div>
            )}

            {/* World Stats — 紧凑版 */}
            <div className="px-4 py-2 border-t border-nw-border">
              <div className="space-y-1">
                {TABS.map((tab) => {
                  const content = getContent(tab.key)
                  const count = content.length
                  const Icon = tab.icon
                  const pct = Math.min(100, (count / 2000) * 100)
                  return (
                    <button
                      key={tab.key}
                      onClick={() => handleTabChange(tab.key)}
                      className="w-full flex items-center gap-2 p-1.5 border border-transparent hover:border-nw-border-light transition-all text-left"
                    >
                      <Icon
                        className={`w-3 h-3 shrink-0 ${
                          activeTab === tab.key ? 'text-white' : 'text-nw-text-muted'
                        }`}
                        strokeWidth={1.5}
                      />
                      <span
                        className={`text-[11px] flex-1 ${
                          activeTab === tab.key ? 'text-white' : 'text-nw-text-secondary'
                        }`}
                      >
                        {tab.label}
                      </span>
                      <div className="w-12 h-px bg-nw-border relative">
                        <div
                          className="absolute top-0 left-0 h-px bg-white/60"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-[9px] text-nw-text-muted font-mono w-8 text-right">
                        {count}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Right: ChatPanel (60%) */}
        {currentBookId ? (
          <div className="w-[60%] flex flex-col overflow-hidden">
            <ChatPanel
              bookId={currentBookId}
              context="worldbuilding"
              suppressAutoSync={syncAnalyzing || syncOpen}
              onStageDataUpdate={handleStageDataUpdate}
              onDataUpdate={handleDataUpdate}
              entities={{
                characters: characters.filter(c => c.book_id === currentBookId).map(c => ({ name: c.name, type: 'character' as const, id: c.id })),
                factions: (displayData.factions_graph || []).map((f: any) => ({ name: typeof f === 'string' ? f : f.name, type: 'faction' as const })),
              }}
              hints={[
                '帮我构建一个东方玄幻世界',
                '设计三大核心势力',
                '创建修炼境界体系',
                '编写千年历史年表',
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
          context="worldbuilding"
          analysis={syncAnalysis}
          onClose={() => { setSyncOpen(false); setSyncAnalysis(null) }}
          onApplied={handleSyncApplied}
        />
      )}
    </div>
  )
}

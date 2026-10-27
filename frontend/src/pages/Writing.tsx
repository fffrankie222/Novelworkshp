import { useState, useEffect, useCallback, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ChevronRight,
  ChevronDown,
  CheckCircle2,
  Circle,
  FileText,
  BookOpen,
  List,
  PenTool,
  Eye,
  Settings,
  Loader2,
  RefreshCw,
  Plus,
  Trash2,
  GripVertical,
  Sparkles,
  RotateCcw,
  AlertTriangle,
  CheckCircle,
  XCircle,
} from 'lucide-react'
import ChatPanel from '../components/ChatPanel'
import StyleGuideEditor from '../components/StyleGuideEditor'
import AuditModal from '../components/AuditModal'
import { api } from '../api/client'
import { useStore } from '../store'
import type { StyleGuide, WorkshopContext, ChapterOutline, ScenePlan, AuditResult } from '../types'
import { DEFAULT_STYLE_GUIDE } from '../types'

// ---- 步骤定义 ----
type StepId = 'context' | 'outline' | 'writing'

interface StepInfo {
  id: StepId
  label: string
  desc: string
  icon: typeof FileText
}

const STEPS: StepInfo[] = [
  { id: 'context', label: '确认上下文', desc: '检查并编辑写作素材', icon: BookOpen },
  { id: 'outline', label: '章节大纲', desc: '场景拆解+出场角色', icon: List },
  { id: 'writing', label: '正文写作', desc: '逐场景交互式写作', icon: PenTool },
]

// ============================================================
// 左侧：步骤导航 + 当前步骤编辑器
// ============================================================

function StepNav({
  currentStep,
  completedSteps,
  onStepClick,
}: {
  currentStep: StepId
  completedSteps: Set<StepId>
  onStepClick: (step: StepId) => void
}) {
  return (
    <div className="space-y-0.5">
      {STEPS.map((step, i) => {
        const Icon = step.icon
        const isActive = step.id === currentStep
        const isCompleted = completedSteps.has(step.id)

        return (
          <button
            key={step.id}
            onClick={() => onStepClick(step.id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-all border-l-2 ${
              isActive
                ? 'border-l-white bg-white/5 text-white'
                : isCompleted
                  ? 'border-l-nw-success text-nw-success/80 hover:bg-white/5'
                  : 'border-l-transparent text-nw-text-muted hover:text-nw-text-secondary hover:bg-white/5'
            }`}
          >
            <div className="flex flex-col items-center">
              {isCompleted ? (
                <CheckCircle2 className="w-4 h-4" strokeWidth={1.5} />
              ) : (
                <Circle className="w-4 h-4" strokeWidth={1.5} />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium">{step.label}</div>
              <div className="text-[10px] text-nw-text-muted mt-0.5">{step.desc}</div>
            </div>
            {isActive && <ChevronRight className="w-3 h-3 text-nw-text-muted" strokeWidth={1.5} />}
          </button>
        )
      })}
    </div>
  )
}

// ============================================================
// 步骤一：上下文编辑
// ============================================================

function ContextEditor({
  context,
  onChange,
  onGenerateOutline,
  loading,
}: {
  context: WorkshopContext
  onChange: (updates: Partial<WorkshopContext>) => void
  onGenerateOutline: () => void
  loading: boolean
}) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    previous_chapter_summary: true,
    world_summary: false,
    active_characters: false,
    active_foreshadows: false,
    recent_chapters_summary: false,
    custom_notes: true,
  })

  const sections = [
    { key: 'previous_chapter_summary', label: '前章摘要', placeholder: '上一章的关键情节…' },
    { key: 'recent_chapters_summary', label: '最近几章摘要', placeholder: '前3-5章的摘要…' },
    { key: 'world_summary', label: '世界观设定', placeholder: '地理、势力、力量体系…' },
    { key: 'active_characters', label: '出场角色', placeholder: '重要角色的背景、性格、动机…' },
    { key: 'active_foreshadows', label: '活跃伏笔', placeholder: '当前活跃的伏笔清单…' },
    { key: 'custom_notes', label: '自定义补充', placeholder: '你想额外告诉AI的内容…' },
  ]

  const toggle = (key: string) => {
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {sections.map((sec) => (
          <div key={sec.key} className="nw-card overflow-hidden">
            <button
              className="w-full px-3 py-2 flex items-center justify-between hover:bg-white/5 transition-colors"
              onClick={() => toggle(sec.key)}
            >
              <span className="text-xs font-medium text-white flex items-center gap-2">
                {expanded[sec.key] ? (
                  <ChevronDown className="w-3 h-3 text-nw-text-muted" strokeWidth={1.5} />
                ) : (
                  <ChevronRight className="w-3 h-3 text-nw-text-muted" strokeWidth={1.5} />
                )}
                {sec.label}
              </span>
              {(context as any)[sec.key] && (
                <span className="text-[10px] text-nw-text-muted">
                  {String((context as any)[sec.key]).length} 字
                </span>
              )}
            </button>
            {expanded[sec.key] && (
              <div className="border-t border-nw-border">
                <textarea
                  className="w-full p-3 bg-transparent text-[12px] text-nw-text-secondary leading-relaxed outline-none resize-none placeholder:text-nw-text-muted/50"
                  placeholder={sec.placeholder}
                  value={String((context as any)[sec.key] || '')}
                  onChange={(e) => onChange({ [sec.key]: e.target.value } as any)}
                  rows={8}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 底部字数统计和下一步按钮 */}
      <div className="p-3 border-t border-nw-border space-y-2">
        <div className="flex justify-between text-[11px]">
          <span className="text-nw-text-muted">预估 tokens</span>
          <span className="font-mono text-white">{context.total_tokens || '—'}</span>
        </div>
        <button
          className="nw-btn nw-btn-primary w-full flex items-center justify-center gap-1.5"
          onClick={onGenerateOutline}
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
          ) : (
            <Sparkles className="w-3.5 h-3.5" strokeWidth={1.5} />
          )}
          {loading ? '生成中…' : 'AI 生成章节大纲'}
        </button>
      </div>
    </div>
  )
}

// ============================================================
// 步骤二：章节大纲编辑
// ============================================================

function OutlineEditor({
  outline,
  onChange,
  onRegenerate,
  onStartWriting,
  generating,
}: {
  outline: ChapterOutline
  onChange: (updates: Partial<ChapterOutline>) => void
  onRegenerate: () => void
  onStartWriting: () => void
  generating: boolean
}) {
  const [editingSceneId, setEditingSceneId] = useState<string | null>(null)

  const updateScene = (sceneId: string, updates: Partial<ScenePlan>) => {
    const newScenes = outline.scenes.map((s) =>
      s.id === sceneId ? { ...s, ...updates } : s
    )
    onChange({ scenes: newScenes })
  }

  const addScene = () => {
    const newScene: ScenePlan = {
      id: `scene-${Date.now()}`,
      index: outline.scenes.length + 1,
      title: `新场景 ${outline.scenes.length + 1}`,
      purpose: '',
      location: '',
      time: '',
      pov: '',
      conflict: '',
      outcome: '',
      emotional_beat: '',
      word_target: 800,
      written: false,
      content: '',
    }
    onChange({ scenes: [...outline.scenes, newScene] })
  }

  const deleteScene = (sceneId: string) => {
    const filtered = outline.scenes.filter((s) => s.id !== sceneId)
    // 重新编号
    const reindexed = filtered.map((s, i) => ({ ...s, index: i + 1 }))
    onChange({ scenes: reindexed })
  }

  const moveScene = (fromIndex: number, direction: 'up' | 'down') => {
    const toIndex = direction === 'up' ? fromIndex - 1 : fromIndex + 1
    if (toIndex < 0 || toIndex >= outline.scenes.length) return
    const newScenes = [...outline.scenes]
    const [moved] = newScenes.splice(fromIndex, 1)
    newScenes.splice(toIndex, 0, moved)
    const reindexed = newScenes.map((s, i) => ({ ...s, index: i + 1 }))
    onChange({ scenes: reindexed })
  }

  return (
    <div className="flex flex-col h-full">
      {/* 基本信息 */}
      <div className="p-3 border-b border-nw-border space-y-2">
        <div>
          <label className="nw-label mb-1 block">章节标题</label>
          <input
            type="text"
            className="nw-input text-xs"
            value={outline.chapter_title}
            onChange={(e) => onChange({ chapter_title: e.target.value })}
          />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="nw-label mb-1 block">节奏类型</label>
            <input
              type="text"
              className="nw-input text-[11px]"
              value={outline.rhythm_type}
              onChange={(e) => onChange({ rhythm_type: e.target.value })}
              placeholder="铺垫/发展/高潮"
            />
          </div>
          <div>
            <label className="nw-label mb-1 block">目标字数</label>
            <input
              type="number"
              className="nw-input text-[11px]"
              value={outline.target_words}
              onChange={(e) => onChange({ target_words: Number(e.target.value) })}
            />
          </div>
        </div>
      </div>

      {/* 核心信息 */}
      <div className="px-3 py-2 border-b border-nw-border space-y-2">
        <div>
          <label className="nw-label mb-1 block">核心冲突</label>
          <textarea
            className="nw-input text-[11px] resize-none h-12"
            value={outline.core_conflict}
            onChange={(e) => onChange({ core_conflict: e.target.value })}
          />
        </div>
        <div>
          <label className="nw-label mb-1 block">章末钩子</label>
          <textarea
            className="nw-input text-[11px] resize-none h-12"
            value={outline.ending_hook}
            onChange={(e) => onChange({ ending_hook: e.target.value })}
          />
        </div>
      </div>

      {/* 出场角色 */}
      <div className="px-3 py-2 border-b border-nw-border">
        <label className="nw-label mb-1 block">出场角色</label>
        <div className="flex flex-wrap gap-1">
          {outline.characters.map((char, i) => (
            <span
              key={i}
              className="px-2 py-0.5 text-[10px] bg-nw-bg-secondary text-nw-text-secondary border border-nw-border rounded"
            >
              {char}
            </span>
          ))}
          {outline.characters.length === 0 && (
            <span className="text-[11px] text-nw-text-muted">暂无</span>
          )}
        </div>
      </div>

      {/* 场景列表 */}
      <div className="flex-1 overflow-y-auto p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="nw-label">场景拆解 ({outline.scenes.length} 个)</span>
          <button
            onClick={addScene}
            className="flex items-center gap-1 px-2 py-0.5 text-[10px] border border-nw-border text-nw-text-secondary hover:text-white hover:border-white/30 transition-colors"
          >
            <Plus className="w-3 h-3" strokeWidth={1.5} />
            添加场景
          </button>
        </div>

        <div className="space-y-2">
          {outline.scenes.map((scene, index) => (
            <div key={scene.id} className="nw-card overflow-hidden">
              {/* 场景标题栏 */}
              <div
                className="flex items-center gap-2 px-2.5 py-2 cursor-pointer hover:bg-white/5 transition-colors"
                onClick={() => setEditingSceneId(editingSceneId === scene.id ? null : scene.id)}
              >
                <GripVertical className="w-3 h-3 text-nw-text-muted" strokeWidth={1.5} />
                <span className="font-mono text-[10px] text-nw-text-muted w-5">
                  {scene.index}
                </span>
                <span className="flex-1 text-xs text-white truncate">{scene.title}</span>
                {scene.written ? (
                  <CheckCircle className="w-3 h-3 text-nw-success" strokeWidth={1.5} />
                ) : (
                  <span className="text-[10px] text-nw-text-muted">
                    {scene.word_target}字
                  </span>
                )}
                <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                  <button
                    className="p-1 text-nw-text-muted hover:text-white transition-colors"
                    onClick={(e) => {
                      e.stopPropagation()
                      moveScene(index, 'up')
                    }}
                    title="上移"
                  >
                    <ChevronRight className="w-3 h-3 -rotate-90" strokeWidth={1.5} />
                  </button>
                  <button
                    className="p-1 text-nw-text-muted hover:text-white transition-colors"
                    onClick={(e) => {
                      e.stopPropagation()
                      moveScene(index, 'down')
                    }}
                    title="下移"
                  >
                    <ChevronRight className="w-3 h-3 rotate-90" strokeWidth={1.5} />
                  </button>
                  <button
                    className="p-1 text-nw-text-muted hover:text-red-400 transition-colors"
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteScene(scene.id)
                    }}
                    title="删除"
                  >
                    <Trash2 className="w-3 h-3" strokeWidth={1.5} />
                  </button>
                </div>
              </div>

              {/* 展开的编辑区 */}
              {editingSceneId === scene.id && (
                <div className="border-t border-nw-border p-2.5 space-y-2">
                  <input
                    type="text"
                    className="nw-input text-[11px]"
                    value={scene.title}
                    onChange={(e) => updateScene(scene.id, { title: e.target.value })}
                    placeholder="场景标题"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="text"
                      className="nw-input text-[10px]"
                      value={scene.pov}
                      onChange={(e) => updateScene(scene.id, { pov: e.target.value })}
                      placeholder="POV 角色"
                    />
                    <input
                      type="text"
                      className="nw-input text-[10px]"
                      value={scene.location}
                      onChange={(e) => updateScene(scene.id, { location: e.target.value })}
                      placeholder="地点"
                    />
                  </div>
                  <textarea
                    className="nw-input text-[10px] resize-none h-10"
                    value={scene.conflict}
                    onChange={(e) => updateScene(scene.id, { conflict: e.target.value })}
                    placeholder="核心冲突"
                  />
                  <textarea
                    className="nw-input text-[10px] resize-none h-10"
                    value={scene.outcome}
                    onChange={(e) => updateScene(scene.id, { outcome: e.target.value })}
                    placeholder="结果走向"
                  />
                  <div className="flex items-center gap-2">
                    <label className="text-[10px] text-nw-text-muted shrink-0">
                      目标字数
                    </label>
                    <input
                      type="number"
                      className="nw-input text-[10px] flex-1"
                      value={scene.word_target}
                      onChange={(e) =>
                        updateScene(scene.id, { word_target: Number(e.target.value) })
                      }
                    />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 底部操作 */}
      <div className="p-3 border-t border-nw-border space-y-2">
        <button
          className="nw-btn w-full flex items-center justify-center gap-1.5 text-[11px]"
          onClick={onRegenerate}
          disabled={generating}
        >
          <RefreshCw className="w-3.5 h-3.5" strokeWidth={1.5} />
          {generating ? '重新生成中…' : '重新生成大纲'}
        </button>
        <button
          className="nw-btn nw-btn-primary w-full flex items-center justify-center gap-1.5"
          onClick={onStartWriting}
        >
          <PenTool className="w-3.5 h-3.5" strokeWidth={1.5} />
          开始写作
        </button>
      </div>
    </div>
  )
}

// ============================================================
// 步骤三：逐场景写作
// ============================================================

function WritingEditor({
  outline,
  onRewriteScene,
  onAudit,
  writingScene,
  auditing,
}: {
  outline: ChapterOutline
  onRewriteScene: (sceneIndex: number, instructions: string) => void
  onAudit: () => void
  writingScene: number | null
  auditing: boolean
}) {
  const [activeSceneId, setActiveSceneId] = useState<string | null>(
    outline.scenes[0]?.id || null
  )
  const [rewriteInput, setRewriteInput] = useState('')
  const [showRewrite, setShowRewrite] = useState<string | null>(null)

  const writtenCount = outline.scenes.filter((s) => s.written).length
  const totalWords = outline.scenes.reduce((sum, s) => sum + s.content.length, 0)
  const progress = outline.scenes.length > 0
    ? Math.round((writtenCount / outline.scenes.length) * 100)
    : 0

  const activeScene = outline.scenes.find((s) => s.id === activeSceneId)

  const handleWriteScene = (scene: ScenePlan) => {
    onRewriteScene(scene.index, '')
  }

  const handleRewrite = (scene: ScenePlan) => {
    onRewriteScene(scene.index, rewriteInput)
    setShowRewrite(null)
    setRewriteInput('')
  }

  return (
    <div className="flex flex-col h-full">
      {/* 进度条 */}
      <div className="p-3 border-b border-nw-border">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-medium text-white">写作进度</span>
          <span className="text-[11px] text-nw-text-secondary">
            {writtenCount}/{outline.scenes.length} 场景 · {totalWords.toLocaleString()} 字
          </span>
        </div>
        <div className="w-full h-1.5 bg-nw-bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full bg-nw-success transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* 场景列表 */}
      <div className="flex-1 overflow-y-auto p-3">
        <div className="space-y-1.5">
          {outline.scenes.map((scene) => {
            const isActive = scene.id === activeSceneId
            const isWriting = writingScene === scene.index

            return (
              <div key={scene.id}>
                {/* 场景标题行 */}
                <button
                  className={`w-full flex items-center gap-2 px-2.5 py-2 text-left transition-all rounded ${
                    isActive
                      ? 'bg-white/10 text-white'
                      : 'text-nw-text-secondary hover:bg-white/5 hover:text-white'
                  }`}
                  onClick={() => setActiveSceneId(scene.id)}
                >
                  <span className="font-mono text-[10px] text-nw-text-muted w-5 shrink-0">
                    {scene.index}
                  </span>
                  <span className="flex-1 text-xs truncate">{scene.title}</span>
                  {isWriting ? (
                    <Loader2 className="w-3 h-3 text-nw-warning animate-spin" strokeWidth={1.5} />
                  ) : scene.written ? (
                    <CheckCircle className="w-3 h-3 text-nw-success" strokeWidth={1.5} />
                  ) : (
                    <span className="text-[10px] text-nw-text-muted">未写</span>
                  )}
                  <ChevronRight
                    className={`w-3 h-3 text-nw-text-muted transition-transform ${isActive ? 'rotate-90' : ''}`}
                    strokeWidth={1.5}
                  />
                </button>

                {/* 展开内容 */}
                {isActive && (
                  <div className="ml-4 mt-1 mb-2 pl-3 border-l border-nw-border space-y-2">
                    {scene.written && scene.content ? (
                      <>
                        <div className="nw-card p-3 max-h-40 overflow-y-auto">
                          <p className="text-[11px] text-nw-text-secondary leading-relaxed">
                            {scene.content.slice(0, 300)}
                            {scene.content.length > 300 ? '…' : ''}
                          </p>
                        </div>
                        <div className="flex items-center justify-between text-[10px]">
                          <span className="text-nw-text-muted">
                            {scene.content.length.toLocaleString()} 字
                          </span>
                          <button
                            className="text-nw-text-secondary hover:text-white transition-colors"
                            onClick={() => setShowRewrite(showRewrite === scene.id ? null : scene.id)}
                          >
                            修改重写
                          </button>
                        </div>
                        {showRewrite === scene.id && (
                          <div className="space-y-2">
                            <textarea
                              className="nw-input text-[11px] resize-none h-16"
                              value={rewriteInput}
                              onChange={(e) => setRewriteInput(e.target.value)}
                              placeholder="告诉AI怎么改…（比如：节奏加快、增加对话、改结局走向）"
                            />
                            <div className="flex gap-2">
                              <button
                                className="nw-btn nw-btn-primary flex-1 text-[11px]"
                                onClick={() => handleRewrite(scene)}
                                disabled={isWriting}
                              >
                                {isWriting ? '改写中…' : '提交修改'}
                              </button>
                            </div>
                          </div>
                        )}
                      </>
                    ) : (
                      <button
                        className="nw-btn nw-btn-primary w-full text-[11px]"
                        onClick={() => handleWriteScene(scene)}
                        disabled={isWriting}
                      >
                        {isWriting ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin mr-1.5 inline" strokeWidth={1.5} />
                            写作中…
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-3 h-3 mr-1.5 inline" strokeWidth={1.5} />
                            生成此场景
                          </>
                        )}
                      </button>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* 底部：审核按钮 */}
      <div className="p-3 border-t border-nw-border">
        <button
          className="nw-btn w-full flex items-center justify-center gap-1.5"
          onClick={onAudit}
          disabled={auditing || writtenCount === 0}
        >
          {auditing ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
          ) : (
            <AlertTriangle className="w-3.5 h-3.5" strokeWidth={1.5} />
          )}
          {auditing ? '审核中…' : 'AI 审核本章'}
        </button>
      </div>
    </div>
  )
}

// ============================================================
// 主组件
// ============================================================

export default function Writing() {
  const { currentBookId, chapters, booksLoading, notify, fetchChapters, outlineData, fetchOutline, worldData, fetchWorld, characters, fetchCharacters, selectedChapter, chapterMetas, selectChapter, fetchChapterMetas } = useStore()

  const [currentStep, setCurrentStep] = useState<StepId>('context')
  const [completedSteps, setCompletedSteps] = useState<Set<StepId>>(new Set())
  const [showStyleGuide, setShowStyleGuide] = useState(false)
  const [styleGuide, setShowStyleGuideState] = useState<StyleGuide>(DEFAULT_STYLE_GUIDE)

  // 写作工坊数据
  const [context, setContext] = useState<WorkshopContext>({
    chapter_number: 1,
    chapter_title: '',
    volume_info: '',
    previous_chapter_summary: '',
    recent_chapters_summary: '',
    world_summary: '',
    active_characters: '',
    active_foreshadows: '',
    timeline_context: '',
    custom_notes: '',
    total_tokens: 0,
  })
  const [outline, setOutline] = useState<ChapterOutline>({
    chapter_number: 1,
    chapter_title: '',
    core_conflict: '',
    chapter_purpose: '',
    rhythm_type: '',
    emotional_arc: '',
    ending_hook: '',
    characters: [],
    character_roles: {},
    active_foreshadows: [],
    new_foreshadows: [],
    scenes: [],
    target_words: 3000,
  })
  const [auditResult, setAuditResult] = useState<AuditResult | null>(null)
  const [showAuditModal, setShowAuditModal] = useState(false)

  // 加载状态
  const [contextLoading, setContextLoading] = useState(false)
  const [outlineGenerating, setOutlineGenerating] = useState(false)
  const [writingScene, setWritingScene] = useState<number | null>(null)
  const [auditing, setAuditing] = useState(false)

  // 数据加载
  useEffect(() => {
    if (!booksLoading && currentBookId) {
      fetchChapters(currentBookId)
      fetchOutline(currentBookId)
      fetchWorld(currentBookId)
      fetchCharacters(currentBookId)
      fetchChapterMetas(currentBookId)
    }
  }, [currentBookId, booksLoading]) // eslint-disable-line react-hooks/exhaustive-deps

  // 切换章节时加载上下文
  useEffect(() => {
    if (!currentBookId || !selectedChapter) return
    loadContext(selectedChapter)
    loadOutline(selectedChapter)
  }, [currentBookId, selectedChapter]) // eslint-disable-line react-hooks/exhaustive-deps

  const loadContext = async (chNum: number) => {
    if (!currentBookId) return
    setContextLoading(true)
    try {
      const res = await api.getWorkshopContext(currentBookId, chNum)
      setContext(res)
    } catch {
      notify('加载上下文失败', 'error')
    } finally {
      setContextLoading(false)
    }
  }

  const loadOutline = async (chNum: number) => {
    if (!currentBookId) return
    try {
      const res = await api.getWorkshopOutline(currentBookId, chNum)
      if (res && res.scenes && res.scenes.length > 0) {
        setOutline(res)
        markStepCompleted('outline')
        if (res.scenes.some((s: ScenePlan) => s.written)) {
          setCurrentStep('writing')
        }
      }
    } catch {
      // 大纲不存在很正常，忽略
    }
  }

  const markStepCompleted = (step: StepId) => {
    setCompletedSteps((prev) => new Set(prev).add(step))
  }

  const handleContextChange = (updates: Partial<WorkshopContext>) => {
    setContext((prev) => ({ ...prev, ...updates }))
    // 保存
    if (currentBookId && selectedChapter) {
      api.updateWorkshopContext(currentBookId, selectedChapter, { ...context, ...updates }).catch(() => {})
    }
  }

  const handleOutlineChange = (updates: Partial<ChapterOutline>) => {
    setOutline((prev) => ({ ...prev, ...updates }))
    // 保存
    if (currentBookId && selectedChapter) {
      api.updateWorkshopOutline(currentBookId, selectedChapter, { ...outline, ...updates }).catch(() => {})
    }
  }

  const handleGenerateOutline = async () => {
    if (!currentBookId || !selectedChapter) return
    setOutlineGenerating(true)
    try {
      const res = await api.generateWorkshopOutline(currentBookId, {
        chapter_number: selectedChapter,
        target_words: outline.target_words,
      })
      setOutline(res)
      markStepCompleted('context')
      setCurrentStep('outline')
      notify('章节大纲已生成', 'success')
    } catch {
      notify('生成大纲失败，请重试', 'error')
    } finally {
      setOutlineGenerating(false)
    }
  }

  const handleRegenerateOutline = async () => {
    await handleGenerateOutline()
  }

  const handleStartWriting = () => {
    markStepCompleted('outline')
    setCurrentStep('writing')
  }

  const handleWriteScene = async (sceneIndex: number, instructions: string) => {
    if (!currentBookId || !selectedChapter) return
    setWritingScene(sceneIndex)
    try {
      const res = await api.writeScene(currentBookId, {
        chapter_number: selectedChapter,
        scene_index: sceneIndex,
        instructions,
      })
      // 更新 outline 中的场景内容
      setOutline((prev) => {
        const newScenes = prev.scenes.map((s) =>
          s.index === sceneIndex
            ? { ...s, content: res.content, written: true }
            : s
        )
        return { ...prev, scenes: newScenes }
      })
      notify(`场景 ${sceneIndex} 写作完成`, 'success')
    } catch {
      notify('写作失败，请重试', 'error')
    } finally {
      setWritingScene(null)
    }
  }

  const handleAudit = async () => {
    if (!currentBookId || !selectedChapter) return
    setAuditing(true)
    try {
      const res = await api.auditChapter(currentBookId, selectedChapter)
      setAuditResult(res)
      setShowAuditModal(true)
    } catch {
      notify('审核失败，请重试', 'error')
    } finally {
      setAuditing(false)
    }
  }

  const handleStepClick = (step: StepId) => {
    // 只允许跳转到已完成或当前步骤
    setCurrentStep(step)
  }

  // 无书籍
  if (!currentBookId) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <BookOpen className="w-10 h-10 mx-auto mb-4 text-nw-text-muted" strokeWidth={1} />
          <p className="text-sm text-nw-text-muted">请先在左侧选择一本书籍</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="px-8 pt-8 pb-4 border-b border-nw-border">
        <div className="flex items-start justify-between">
          <div>
            <p className="nw-label mb-1">writing · 写作工坊</p>
            <h1 className="text-xl font-semibold text-white tracking-wide">
              三步式协作写作
            </h1>
            <p className="text-xs text-nw-text-secondary mt-1">
              当前步骤：
              <span className="text-white font-medium ml-1">
                {STEPS.find((s) => s.id === currentStep)?.label}
              </span>
            </p>
          </div>
          <div className="flex items-center gap-3 text-[11px] text-nw-text-muted">
            {/* 章节选择 */}
            <div className="flex items-center gap-2">
              <label className="text-nw-text-muted">章节</label>
              <select
                value={selectedChapter || 1}
                onChange={(e) => {
                  const n = Number(e.target.value)
                  selectChapter(n)
                }}
                className="px-2 py-1 bg-nw-bg-secondary border border-nw-border text-white text-[11px] rounded outline-none focus:border-white/30"
              >
                {chapterMetas.map((ch: any) => (
                  <option key={ch.number} value={ch.number}>
                    第 {ch.number} 章 - {ch.title || `章节 ${ch.number}`}
                  </option>
                ))}
                {chapterMetas.length === 0 && <option value={1}>第 1 章</option>}
              </select>
            </div>
            <button
              onClick={() => setShowStyleGuide(!showStyleGuide)}
              className="flex items-center gap-1.5 px-2 py-1 border border-nw-border hover:border-white hover:text-white transition-colors"
              title="写作规范设置"
            >
              <Settings className="w-3.5 h-3.5" strokeWidth={1.5} />
              <span>写作规范</span>
            </button>
            <Eye className="w-3.5 h-3.5" strokeWidth={1.5} />
            <span>当前项目 · {chapters.length} 章</span>
          </div>
        </div>
      </div>

      {/* 主体：左栏编辑器(45%) + 右栏AI对话(55%) */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左栏：步骤导航 + 当前步骤编辑器 */}
        <div className="w-[45%] border-r border-nw-border bg-nw-bg-secondary flex flex-col overflow-hidden">
          {/* 步骤导航 */}
          <div className="px-3 py-2 border-b border-nw-border">
            <span className="text-[11px] font-medium text-nw-text-muted">写作步骤</span>
          </div>
          <div className="px-2 py-2 border-b border-nw-border">
            <StepNav
              currentStep={currentStep}
              completedSteps={completedSteps}
              onStepClick={handleStepClick}
            />
          </div>

          {/* 当前步骤内容 */}
          <div className="flex-1 overflow-hidden min-h-0">
            {currentStep === 'context' && (
              <ContextEditor
                context={context}
                onChange={handleContextChange}
                onGenerateOutline={handleGenerateOutline}
                loading={outlineGenerating}
              />
            )}
            {currentStep === 'outline' && (
              <OutlineEditor
                outline={outline}
                onChange={handleOutlineChange}
                onRegenerate={handleRegenerateOutline}
                onStartWriting={handleStartWriting}
                generating={outlineGenerating}
              />
            )}
            {currentStep === 'writing' && (
              <WritingEditor
                outline={outline}
                onRewriteScene={handleWriteScene}
                onAudit={handleAudit}
                writingScene={writingScene}
                auditing={auditing}
              />
            )}
          </div>
        </div>

        {/* 右栏：AI 对话 */}
        <div className="w-[55%] flex flex-col overflow-hidden">
          <ChatPanel
            bookId={currentBookId}
            context="writing"
            chapterNumber={selectedChapter}
            hints={[
              currentStep === 'context' ? '帮我梳理这一章的上下文要点' : currentStep === 'outline' ? '帮我调整场景节奏' : '这个场景的对话写得有点生硬',
              '增加更多感官描写',
              '让这段更有张力',
              '加一个伏笔',
            ]}
          />
        </div>
      </div>

      {/* 审核弹窗 */}
      {showAuditModal && auditResult && (
        <AuditModal
          auditResult={auditResult}
          onClose={() => setShowAuditModal(false)}
        />
      )}

      {/* 写作规范抽屉 */}
      {showStyleGuide && currentBookId && (
        <div className="fixed inset-0 z-50 flex">
          <div className="flex-1 bg-black/40" onClick={() => setShowStyleGuide(false)} />
          <div className="w-[420px] bg-nw-bg border-l border-nw-border overflow-y-auto">
            <div className="p-4 border-b border-nw-border flex items-center justify-between">
              <h3 className="text-sm font-medium text-white">写作规范</h3>
              <button onClick={() => setShowStyleGuide(false)} className="p-1 text-nw-text-muted hover:text-white">
                <ChevronRight className="w-4 h-4" strokeWidth={1.5} />
              </button>
            </div>
            <div className="p-4">
              <StyleGuideEditor
                bookId={currentBookId}
                value={styleGuide}
                onChange={setShowStyleGuideState}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

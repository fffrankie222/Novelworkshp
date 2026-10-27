import { useState } from 'react'
import { BookOpen, Save, RotateCcw, ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import { api } from '../api/client'
import { useStore } from '../store'
import type { StyleGuide } from '../types'
import { DEFAULT_STYLE_GUIDE } from '../types'

// ---- Section types ----
interface SectionProps {
  title: string
  icon: React.ReactNode
  defaultOpen?: boolean
  children: React.ReactNode
}

function Section({ title, icon, defaultOpen = false, children }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-nw-border">
      <button
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-white/[0.02] transition-colors"
        onClick={() => setOpen(!open)}
      >
        {open ? (
          <ChevronDown className="w-3.5 h-3.5 text-nw-text-muted" strokeWidth={1.5} />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-nw-text-muted" strokeWidth={1.5} />
        )}
        {icon}
        <span className="text-xs font-medium text-white">{title}</span>
      </button>
      {open && <div className="px-3 pb-3 pt-1 space-y-3 border-t border-nw-border">{children}</div>}
    </div>
  )
}

// ---- Field helper ----
function Field({ label, hint }: { label: string; hint?: string }) {
  return (
    <div>
      <label className="block text-[11px] text-nw-text-muted mb-1">{label}</label>
      {hint && <p className="text-[10px] text-nw-text-muted mb-1.5 italic">{hint}</p>}
    </div>
  )
}

// ---- Props ----
interface StyleGuideEditorProps {
  bookId: string
  value: StyleGuide
  onChange: (guide: StyleGuide) => void
  compact?: boolean
}

// ---- Summary (read-only) ----
export function StyleGuideSummary({ guide }: { guide: StyleGuide }) {
  return (
    <div className="space-y-3">
      <div>
        <h4 className="nw-label mb-1.5">文风语言</h4>
        <div className="space-y-1 text-[11px]">
          <div className="flex gap-2">
            <span className="text-nw-text-muted shrink-0">视角</span>
            <span className="text-nw-text-secondary">{guide.narrative_pov}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-nw-text-muted shrink-0">调性</span>
            <span className="text-nw-text-secondary">{guide.tone}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-nw-text-muted shrink-0">对话</span>
            <span className="text-nw-text-secondary">{guide.dialogue_style}</span>
          </div>
        </div>
      </div>

      <div>
        <h4 className="nw-label mb-1.5">章节结尾</h4>
        <div className="flex items-center gap-2 text-[11px]">
          <span className={`nw-badge ${guide.chapter_ending_hook ? 'nw-badge-success' : ''}`}>
            {guide.chapter_ending_hook ? '开启' : '关闭'}
          </span>
          {guide.chapter_ending_hook && (
            <span className="text-nw-text-secondary">{guide.chapter_ending_hook_instruction}</span>
          )}
        </div>
      </div>

      <div>
        <h4 className="nw-label mb-1.5">节奏</h4>
        <div className="space-y-1 text-[11px]">
          <div className="flex gap-2">
            <span className="text-nw-text-muted shrink-0">曲线</span>
            <span className="text-nw-text-secondary">{guide.pacing.overall_curve}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-nw-text-muted shrink-0">冲突</span>
            <span className="text-nw-text-secondary">{guide.pacing.tension_density}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-nw-text-muted shrink-0">高潮</span>
            <span className="text-nw-text-secondary">{guide.pacing.climax_frequency}</span>
          </div>
        </div>
      </div>

      <div>
        <h4 className="nw-label mb-1.5">网文惯例</h4>
        <div className="space-y-1 text-[11px]">
          <div className="flex gap-2">
            <span className="text-nw-text-muted shrink-0">打脸</span>
            <span className="text-nw-text-secondary">{guide.webnovel_conventions.face_slapping_rhythm}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-nw-text-muted shrink-0">升级</span>
            <span className="text-nw-text-secondary">{guide.webnovel_conventions.power_progression}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-nw-text-muted shrink-0">伏笔</span>
            <span className="text-nw-text-secondary">{guide.webnovel_conventions.foreshadowing_rules}</span>
          </div>
        </div>
      </div>

      {guide.custom_rules && (
        <div>
          <h4 className="nw-label mb-1.5">自定义规则</h4>
          <p className="text-[11px] text-nw-text-secondary">{guide.custom_rules}</p>
        </div>
      )}
    </div>
  )
}

// ---- Main Editor ----
export default function StyleGuideEditor({ bookId, value, onChange, compact }: StyleGuideEditorProps) {
  const { notify } = useStore()
  const [saving, setSaving] = useState(false)
  const [local, setLocal] = useState<StyleGuide>({ ...value })

  // Sync when value prop changes
  const update = (patch: Partial<StyleGuide>) => {
    const next = { ...local, ...patch }
    setLocal(next)
    onChange(next)
  }

  const updatePacing = (patch: Partial<StyleGuide['pacing']>) => {
    const next = { ...local, pacing: { ...local.pacing, ...patch } }
    setLocal(next)
    onChange(next)
  }

  const updateWebnovel = (patch: Partial<StyleGuide['webnovel_conventions']>) => {
    const next = { ...local, webnovel_conventions: { ...local.webnovel_conventions, ...patch } }
    setLocal(next)
    onChange(next)
  }

  const handleReset = () => {
    setLocal({ ...DEFAULT_STYLE_GUIDE })
    onChange({ ...DEFAULT_STYLE_GUIDE })
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.updateConfig(bookId, { style_guide: local })
      notify('风格指南已保存', 'success')
    } catch {
      notify('保存失败', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-white" strokeWidth={1.5} />
          <span className="text-xs font-medium text-white">风格指南</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            className="text-nw-text-muted hover:text-white transition-colors p-1"
            onClick={handleReset}
            title="恢复默认"
          >
            <RotateCcw className="w-3.5 h-3.5" strokeWidth={1.5} />
          </button>
          <button
            className="nw-btn nw-btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
            ) : (
              <Save className="w-3.5 h-3.5" strokeWidth={1.5} />
            )}
            保存
          </button>
        </div>
      </div>

      {/* Section: 文风语言 */}
      <Section title="文风语言" icon={<BookOpen className="w-3 h-3 text-nw-text-muted" strokeWidth={1.5} />} defaultOpen>
        <div>
          <Field label="叙事视角" hint="如：第三人称全知视角、第一人称限制视角..." />
          <input
            className="nw-input w-full text-xs"
            value={local.narrative_pov}
            onChange={(e) => update({ narrative_pov: e.target.value })}
          />
        </div>
        <div>
          <Field label="语言调性" hint="如：轻松幽默、严肃写实、黑暗压抑..." />
          <input
            className="nw-input w-full text-xs"
            value={local.tone}
            onChange={(e) => update({ tone: e.target.value })}
          />
        </div>
        <div>
          <Field label="对话风格" hint="如：口语化、文言交杂、网络用语..." />
          <input
            className="nw-input w-full text-xs"
            value={local.dialogue_style}
            onChange={(e) => update({ dialogue_style: e.target.value })}
          />
        </div>
      </Section>

      {/* Section: 章节结构惯例 */}
      <Section title="章节结尾惯例" icon={<span className="text-[10px] text-nw-text-muted">⚓</span>}>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-white cursor-pointer">
            <input
              type="checkbox"
              checked={local.chapter_ending_hook}
              onChange={(e) => update({ chapter_ending_hook: e.target.checked })}
              className="w-3.5 h-3.5 accent-white"
            />
            每章结尾必须设钩子/悬念
          </label>
        </div>
        {local.chapter_ending_hook && (
          <div>
            <Field label="钩子指导" hint="描述你期望的结尾悬念形式" />
            <textarea
              className="nw-textarea w-full text-xs h-16 resize-none"
              value={local.chapter_ending_hook_instruction}
              onChange={(e) => update({ chapter_ending_hook_instruction: e.target.value })}
            />
          </div>
        )}
      </Section>

      {/* Section: 整体节奏 */}
      <Section title="整体节奏" icon={<span className="text-[10px] text-nw-text-muted">〰</span>}>
        <div>
          <Field label="整体节奏曲线" />
          <textarea
            className="nw-textarea w-full text-xs h-14 resize-none"
            value={local.pacing.overall_curve}
            onChange={(e) => updatePacing({ overall_curve: e.target.value })}
          />
        </div>
        <div>
          <Field label="冲突密度" />
          <input
            className="nw-input w-full text-xs"
            value={local.pacing.tension_density}
            onChange={(e) => updatePacing({ tension_density: e.target.value })}
          />
        </div>
        <div>
          <Field label="高潮频率" />
          <input
            className="nw-input w-full text-xs"
            value={local.pacing.climax_frequency}
            onChange={(e) => updatePacing({ climax_frequency: e.target.value })}
          />
        </div>
      </Section>

      {/* Section: 网文惯例 */}
      <Section title="网文惯例" icon={<span className="text-[10px] text-nw-text-muted">⚡</span>}>
        <div>
          <Field label="打脸节奏" hint="压抑多久后打脸一次" />
          <input
            className="nw-input w-full text-xs"
            value={local.webnovel_conventions.face_slapping_rhythm}
            onChange={(e) => updateWebnovel({ face_slapping_rhythm: e.target.value })}
          />
        </div>
        <div>
          <Field label="升级节奏" hint="多久可见一次实力提升" />
          <input
            className="nw-input w-full text-xs"
            value={local.webnovel_conventions.power_progression}
            onChange={(e) => updateWebnovel({ power_progression: e.target.value })}
          />
        </div>
        <div>
          <Field label="伏笔回收规则" hint="伏笔埋下后多久需要回收" />
          <input
            className="nw-input w-full text-xs"
            value={local.webnovel_conventions.foreshadowing_rules}
            onChange={(e) => updateWebnovel({ foreshadowing_rules: e.target.value })}
          />
        </div>
      </Section>

      {/* Section: 自定义规则 */}
      {!compact && (
        <Section title="自定义规则" icon={<span className="text-[10px] text-nw-text-muted">✎</span>}>
          <textarea
            className="nw-textarea w-full text-xs h-20 resize-none"
            placeholder="添加你自己的写作规则，AI将遵循这些规则进行创作..."
            value={local.custom_rules}
            onChange={(e) => update({ custom_rules: e.target.value })}
          />
        </Section>
      )}
    </div>
  )
}

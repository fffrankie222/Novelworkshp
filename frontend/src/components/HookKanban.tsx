import type { Hook } from '../types'
import { Flag, Zap, ArrowRight, CheckCircle2 } from 'lucide-react'

interface HookKanbanProps {
  hooks: Hook[]
}

const columns = [
  { key: 'planted' as const, label: '已埋下', icon: Flag },
  { key: 'activated' as const, label: '已激活', icon: Zap },
  { key: 'advancing' as const, label: '推进中', icon: ArrowRight },
  { key: 'resolved' as const, label: '已回收', icon: CheckCircle2 },
]

export default function HookKanban({ hooks }: HookKanbanProps) {
  const getPriorityBadge = (priority: string) => {
    if (priority === 'high') return 'nw-badge nw-badge-error'
    if (priority === 'medium') return 'nw-badge nw-badge-warning'
    return 'nw-badge'
  }

  const priorityLabel = (p: string) => (p === 'high' ? '高' : p === 'medium' ? '中' : '低')

  return (
    <div className="grid grid-cols-4 gap-3 h-full">
      {columns.map((col) => {
        const columnHooks = hooks.filter((h) => h.status === col.key)
        const Icon = col.icon
        const isResolved = col.key === 'resolved'

        return (
          <div
            key={col.key}
            className="kanban-column flex flex-col"
          >
            {/* Column Header */}
            <div className="flex items-center gap-2 px-3 py-2 border-b border-nw-border">
              <Icon
                className={`w-3.5 h-3.5 ${isResolved ? 'text-nw-success' : 'text-white'}`}
                strokeWidth={1.5}
              />
              <span className="text-xs font-medium text-white">{col.label}</span>
              <span className="ml-auto text-[10px] text-nw-text-muted font-mono">
                {columnHooks.length}
              </span>
            </div>

            {/* Items */}
            <div className="flex-1 p-2 space-y-2 overflow-y-auto">
              {columnHooks.length === 0 && (
                <div className="text-center py-6 text-[11px] text-nw-text-muted">
                  暂无伏笔
                </div>
              )}
              {columnHooks.map((hook) => (
                <div
                  key={hook.id}
                  className="kanban-item p-3 group"
                >
                  <p className="text-xs font-medium text-white mb-1 truncate">
                    {hook.title}
                  </p>
                  <p className="text-[11px] text-nw-text-secondary line-clamp-2 mb-2">
                    {hook.description}
                  </p>
                  <div className="flex items-center justify-between">
                    <span className={getPriorityBadge(hook.priority)}>
                      {priorityLabel(hook.priority)}
                    </span>
                    <span className="text-[10px] text-nw-text-muted font-mono">
                      Ch.{hook.planted_chapter} → {hook.target_chapter}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

import { useState } from 'react'
import { ChevronRight, ChevronDown, FileText, Folder, BookOpen } from 'lucide-react'
import type { OutlineNode } from '../types'

interface ChapterNodeProps {
  node: OutlineNode
  level?: number
  selectedId?: string
  onSelect?: (id: string) => void
}

const STATUS_LABELS: Record<string, { label: string; className: string }> = {
  draft: { label: '草稿', className: 'nw-badge' },
  writing: { label: '写作中', className: 'nw-badge nw-badge-info' },
  reviewing: { label: '审核中', className: 'nw-badge nw-badge-warning' },
  polishing: { label: '润色中', className: 'nw-badge nw-badge-info' },
  final: { label: '已定稿', className: 'nw-badge nw-badge-success' },
}

export default function ChapterNode({
  node,
  level = 0,
  selectedId,
  onSelect,
}: ChapterNodeProps) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = node.children && node.children.length > 0

  const iconMap = {
    book: BookOpen,
    volume: Folder,
    chapter: FileText,
  }
  const Icon = iconMap[node.type]

  const isSelected = selectedId === node.id
  const isChapter = node.type === 'chapter'
  const isVolume = node.type === 'volume'

  return (
    <div>
      <div
        className={`flex items-center gap-1.5 px-2 py-1.5 cursor-pointer text-xs transition-all border ${
          isSelected
            ? 'border-white bg-white/5 text-white'
            : isChapter
              ? 'border-transparent text-nw-text-secondary hover:border-nw-border-light hover:text-white'
              : 'border-transparent text-white hover:text-nw-text-secondary'
        }`}
        style={{ paddingLeft: `${level * 14 + 8}px` }}
        onClick={() => {
          if (hasChildren) setExpanded(!expanded)
          onSelect?.(node.id)
        }}
      >
        {/* Expand toggle */}
        {hasChildren ? (
          <button
            className="p-0.5 text-nw-text-muted hover:text-white transition-colors"
            onClick={(e) => {
              e.stopPropagation()
              setExpanded(!expanded)
            }}
          >
            {expanded ? (
              <ChevronDown className="w-3 h-3" strokeWidth={1.5} />
            ) : (
              <ChevronRight className="w-3 h-3" strokeWidth={1.5} />
            )}
          </button>
        ) : (
          <span className="w-4" />
        )}

        <Icon
          className={`w-3.5 h-3.5 shrink-0 ${
            isVolume ? 'text-white' : 'text-nw-text-muted'
          }`}
          strokeWidth={1.5}
        />

        <span className="truncate flex-1">
          {isChapter && node.chapter_number && (
            <span className="text-nw-text-muted font-mono mr-1">
              {node.chapter_number.toString().padStart(2, '0')}.
            </span>
          )}
          {node.title}
        </span>

        {node.chapter_number && (
          <span className="text-[10px] text-nw-text-muted font-mono shrink-0">
            #{node.chapter_number}
          </span>
        )}
      </div>

      {hasChildren && expanded && (
        <div>
          {node.children!.map((child) => (
            <ChapterNode
              key={child.id}
              node={child}
              level={level + 1}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  )
}

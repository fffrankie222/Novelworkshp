import type { Book } from '../types'
import { FileText, BookOpen, Clock, ChevronRight } from 'lucide-react'
import { format } from 'date-fns'

interface BookCardProps {
  book: Book
  onClick?: () => void
  active?: boolean
}

export default function BookCard({ book, onClick, active }: BookCardProps) {
  const progress = book.total_chapters > 0
    ? Math.round((book.total_words / (book.total_chapters * 3000)) * 100)
    : 0

  return (
    <div
      onClick={onClick}
      className={`nw-card nw-card-hover cursor-pointer group relative overflow-hidden transition-all ${
        active ? 'border-white' : ''
      }`}
    >
      {/* Top accent line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-white/0 group-hover:bg-white transition-colors" />

      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="nw-badge">{book.genre}</span>
              <span className="nw-label">
                {book.total_chapters} 章
              </span>
            </div>
            <h3 className="text-base font-semibold text-white truncate group-hover:underline underline-offset-2 decoration-1">
              {book.title}
            </h3>
          </div>
          <ChevronRight
            className="w-4 h-4 text-nw-text-muted shrink-0 mt-1 group-hover:text-white group-hover:translate-x-0.5 transition-all"
            strokeWidth={1.5}
          />
        </div>

        {/* Description */}
        <p className="text-xs text-nw-text-secondary line-clamp-2 mb-4 leading-relaxed">
          {book.description}
        </p>

        {/* Progress bar */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-nw-text-muted uppercase tracking-wider">
              写作进度
            </span>
            <span className="text-[10px] text-nw-text-secondary font-mono">
              {progress}%
            </span>
          </div>
          <div className="w-full h-px bg-nw-border">
            <div
              className="h-full bg-white transition-all"
              style={{ width: `${Math.min(100, progress)}%` }}
            />
          </div>
        </div>

        {/* Stats */}
        <div className="flex items-center justify-between pt-3 border-t border-nw-border">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1 text-[11px] text-nw-text-muted">
              <FileText className="w-3 h-3" strokeWidth={1.5} />
              <span className="font-mono text-nw-text-secondary">{book.total_chapters}</span>
              <span>章</span>
            </div>
            <div className="flex items-center gap-1 text-[11px] text-nw-text-muted">
              <BookOpen className="w-3 h-3" strokeWidth={1.5} />
              <span className="font-mono text-nw-text-secondary">
                {(book.total_words / 1000).toFixed(1)}k
              </span>
              <span>字</span>
            </div>
          </div>
          <div className="flex items-center gap-1 text-[10px] text-nw-text-muted">
            <Clock className="w-3 h-3" strokeWidth={1.5} />
            <span>{format(new Date(book.updated_at), 'yyyy/MM/dd')}</span>
          </div>
        </div>

        {/* Active hooks indicator */}
        {book.active_hooks > 0 && (
          <div className="absolute top-3 right-3">
            <span className="nw-badge nw-badge-warning">
              {book.active_hooks} 伏笔
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

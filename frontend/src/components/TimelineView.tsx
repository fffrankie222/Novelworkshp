import type { TimelineEvent } from '../types'

interface TimelineViewProps {
  events: TimelineEvent[]
  compact?: boolean
}

export default function TimelineView({ events, compact }: TimelineViewProps) {
  return (
    <div className="relative py-2">
      {/* Vertical line */}
      <div className="absolute left-[11px] top-2 bottom-2 w-px bg-nw-border" />

      <div className="space-y-3">
        {events.map((event, idx) => (
          <div key={event.id} className="relative flex gap-3 pl-7">
            {/* Dot */}
            <div
              className={`absolute left-2 top-1.5 w-2 h-2 border border-white shrink-0 z-10 ${
                idx === 0 ? 'bg-white' : 'bg-nw-bg'
              }`}
            />

            {/* Content */}
            <div className="flex-1 border border-nw-border bg-nw-card p-3 hover:border-nw-border-light transition-colors">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className="nw-badge nw-badge-white">
                  {event.time_point}
                </span>
                <span className="nw-label">{event.category}</span>
              </div>
              <h4 className="text-sm font-medium text-white mb-1">{event.title}</h4>
              {!compact && (
                <p className="text-xs text-nw-text-secondary leading-relaxed">
                  {event.description}
                </p>
              )}
              {event.chapter_ref > 0 && (
                <span className="text-[10px] text-nw-text-muted mt-2 inline-block font-mono">
                  关联章节 #{event.chapter_ref}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

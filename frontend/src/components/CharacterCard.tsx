import type { Character } from '../types'

interface CharacterCardProps {
  character: Character
  selected?: boolean
  onClick?: () => void
  compact?: boolean
  onDelete?: () => void
}

// 角色定位 → 标签颜色映射（value 为完整的 Tailwind 类名串，统一放在 bg 字段）
const ROLE_TAG_STYLE: Record<string, { bg: string }> = {
  '主角': { bg: 'bg-blue-500/20 text-blue-300 border-blue-500/30' },
  '男主': { bg: 'bg-blue-500/20 text-blue-300 border-blue-500/30' },
  '女主': { bg: 'bg-pink-500/20 text-pink-300 border-pink-500/30' },
  '反派/对手': { bg: 'bg-red-500/20 text-red-300 border-red-500/30' },
  '反派': { bg: 'bg-red-500/20 text-red-300 border-red-500/30' },
  '导师': { bg: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
  '关键NPC': { bg: 'bg-purple-500/20 text-purple-300 border-purple-500/30' },
  '待定': { bg: 'bg-white/5 text-nw-text-muted border-white/10' },
}

function getRoleStyle(role: string) {
  return ROLE_TAG_STYLE[role] || ROLE_TAG_STYLE['待定']
}

export default function CharacterCard({
  character,
  selected,
  onClick,
  compact,
}: CharacterCardProps) {
  const isLight = character.avatar_color >= '#888888'
  const textColor = isLight ? '#0a0a0a' : '#ffffff'
  const roleStyle = getRoleStyle(character.role)

  return (
    <div
      onClick={onClick}
      className={`group relative flex flex-col p-3.5 cursor-pointer transition-all border ${
        selected
          ? 'border-white bg-white/5 shadow-lg shadow-white/5'
          : 'border-nw-border bg-nw-card hover:border-white/30 hover:bg-white/[0.02]'
      }`}
    >
      {/* Top row: Avatar + Name + Role tag */}
      <div className="flex items-start gap-3 mb-2.5">
        <div
          className="flex items-center justify-center font-bold text-sm shrink-0 border border-white/10"
          style={{
            backgroundColor: character.avatar_color,
            color: textColor,
            width: compact ? 28 : 40,
            height: compact ? 28 : 40,
          }}
        >
          {character.name[0]}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-white truncate">
              {character.name}
            </p>
            <span
              className={`px-1.5 py-0.5 text-[10px] border leading-tight ${roleStyle.bg}`}
            >
              {character.role}
            </span>
          </div>
          {character.tag && (
            <p className="text-[11px] text-nw-text-muted truncate mt-0.5">
              {character.tag}
            </p>
          )}
        </div>
      </div>

      {/* Personality snippet */}
      {!compact && character.personality && (
        <div className="mb-2">
          <div className="flex items-center gap-1 mb-1">
            <span className="text-[10px] text-nw-text-muted font-medium">性格</span>
          </div>
          <p className="text-[11px] text-nw-text-secondary leading-relaxed line-clamp-2">
            {character.personality}
          </p>
        </div>
      )}

      {/* Bottom row: relationship count + catchphrase */}
      {!compact && (
        <div className="mt-auto pt-2 border-t border-nw-border/50">
          {character.catchphrase && (
            <p className="text-[10px] text-nw-text-muted italic truncate">
              "{character.catchphrase}"
            </p>
          )}
          <div className="flex items-center gap-3 mt-1.5">
            {character.relationships && character.relationships.length > 0 && (
              <span className="text-[10px] text-nw-text-muted">
                {character.relationships.length} 段关系
              </span>
            )}
            {character.abilities && (
              <span className="text-[10px] text-nw-text-muted truncate">
                {character.abilities.split('\n')[0].slice(0, 20)}
                {character.abilities.length > 20 ? '...' : ''}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Selected indicator */}
      {selected && (
        <div className="absolute top-2 right-2 w-1.5 h-1.5 bg-white rounded-full" />
      )}
    </div>
  )
}

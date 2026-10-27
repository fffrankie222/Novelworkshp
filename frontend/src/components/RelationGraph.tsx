import { useState } from 'react'
import type { Character, Relationship } from '../types'

interface RelationGraphProps {
  characters: Character[]
  width?: number
  height?: number
}

// Grayscale palette for relations
const RELATION_STYLES: Record<string, { stroke: string; dash: string }> = {
  '羁绊': { stroke: '#ffffff', dash: '0' },
  '对手': { stroke: '#888888', dash: '4,2' },
  '亲情': { stroke: '#cccccc', dash: '0' },
  '同门': { stroke: '#666666', dash: '2,2' },
  '追求': { stroke: '#aaaaaa', dash: '4,2' },
  '信任': { stroke: '#ffffff', dash: '2,2' },
  '探索': { stroke: '#555555', dash: '1,1' },
}

export default function RelationGraph({
  characters,
  width = 420,
  height = 360,
}: RelationGraphProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const cx = width / 2
  const cy = height / 2
  const radius = Math.min(width, height) * 0.35

  const nodes = characters.map((c, i) => {
    const angle = (2 * Math.PI * i) / characters.length - Math.PI / 2
    return {
      ...c,
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    }
  })

  const charMap = new Map(nodes.map((n) => [n.id, n]))
  const edges: { source: typeof nodes[0]; target: typeof nodes[0]; rel: Relationship }[] = []
  const seenEdges = new Set<string>()

  nodes.forEach((node) => {
    node.relationships.forEach((rel) => {
      const target = charMap.get(rel.target_id)
      if (!target) return
      const key = [node.id, target.id].sort().join('|')
      if (seenEdges.has(key)) return
      seenEdges.add(key)
      edges.push({ source: node, target, rel })
    })
  })

  const isNodeHighlighted = (id: string) =>
    selectedId === id || hoveredId === id

  const isEdgeHighlighted = (sId: string, tId: string) => {
    if (selectedId) return selectedId === sId || selectedId === tId
    if (hoveredId) return hoveredId === sId || hoveredId === tId
    return false
  }

  const selectedChar = selectedId ? charMap.get(selectedId) : null

  return (
    <div className="relative w-full h-full flex flex-col">
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="mx-auto block"
      >
        {/* Center label */}
        <text
          x={cx}
          y={cy - 8}
          textAnchor="middle"
          className="fill-nw-text-muted text-[9px]"
          style={{ textTransform: 'uppercase', letterSpacing: '0.1em' }}
        >
          人物关系
        </text>
        <line
          x1={cx - 20}
          y1={cy + 4}
          x2={cx + 20}
          y2={cy + 4}
          stroke="#222222"
          strokeWidth="1"
        />

        {/* Edges */}
        {edges.map((edge, i) => {
          const highlighted = isEdgeHighlighted(edge.source.id, edge.target.id)
          const style = RELATION_STYLES[edge.rel.type] || { stroke: '#333333', dash: '0' }
          const midX = (edge.source.x + edge.target.x) / 2
          const midY = (edge.source.y + edge.target.y) / 2

          return (
            <g key={i} className="pointer-events-none">
              <line
                x1={edge.source.x}
                y1={edge.source.y}
                x2={edge.target.x}
                y2={edge.target.y}
                stroke={highlighted ? '#ffffff' : style.stroke}
                strokeWidth={highlighted ? 1.5 : 1}
                strokeDasharray={style.dash}
                opacity={highlighted ? 1 : 0.6}
              />
              {highlighted && (
                <>
                  <rect
                    x={midX - 20}
                    y={midY - 7}
                    width="40"
                    height="14"
                    fill="#0a0a0a"
                    stroke={style.stroke}
                    strokeWidth="0.5"
                  />
                  <text
                    x={midX}
                    y={midY + 3}
                    textAnchor="middle"
                    className="fill-white text-[9px] pointer-events-none"
                  >
                    {edge.rel.type}
                  </text>
                </>
              )}
            </g>
          )
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const highlighted = isNodeHighlighted(node.id)
          const isLight = node.avatar_color >= '#888888'
          const textColor = isLight ? '#0a0a0a' : '#ffffff'

          return (
            <g
              key={node.id}
              onClick={() => setSelectedId(selectedId === node.id ? null : node.id)}
              onMouseEnter={() => setHoveredId(node.id)}
              onMouseLeave={() => setHoveredId(null)}
              className="cursor-pointer"
            >
              {/* Outer ring when highlighted */}
              {highlighted && (
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={22}
                  fill="none"
                  stroke="#ffffff"
                  strokeWidth="1"
                />
              )}
              {/* Node circle */}
              <circle
                cx={node.x}
                cy={node.y}
                r={18}
                fill={node.avatar_color}
                stroke="#222222"
                strokeWidth="1"
              />
              {/* Initial */}
              <text
                x={node.x}
                y={node.y + 1}
                textAnchor="middle"
                dominantBaseline="central"
                className="text-[10px] font-medium pointer-events-none"
                fill={textColor}
              >
                {node.name.slice(0, 2)}
              </text>
              {/* Name label */}
              <text
                x={node.x}
                y={node.y + 32}
                textAnchor="middle"
                className="text-[10px] pointer-events-none"
                fill={highlighted ? '#ffffff' : '#888888'}
              >
                {node.name}
              </text>
            </g>
          )
        })}
      </svg>

      {/* Legend / Selected info */}
      <div className="mt-2 px-3 py-2 border-t border-nw-border">
        {selectedChar ? (
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs font-medium text-white">{selectedChar.name}</span>
              <span className="nw-label">的关系</span>
            </div>
            <div className="space-y-1">
              {selectedChar.relationships.map((rel, i) => (
                <div key={i} className="flex items-center gap-2 text-[11px]">
                  <span className="w-6 h-px bg-nw-border-light" />
                  <span className="text-white">{rel.target_name}</span>
                  <span className="text-nw-text-muted">·</span>
                  <span className="text-nw-text-secondary">{rel.type}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-nw-text-muted">
            {Object.entries(RELATION_STYLES).slice(0, 5).map(([name, style]) => (
              <div key={name} className="flex items-center gap-1.5">
                <svg width="16" height="8">
                  <line
                    x1="0"
                    y1="4"
                    x2="16"
                    y2="4"
                    stroke={style.stroke}
                    strokeWidth="1"
                    strokeDasharray={style.dash}
                  />
                </svg>
                <span>{name}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

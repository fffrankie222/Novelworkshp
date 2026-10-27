// ============ 核心类型定义 ============

export interface Book {
  id: string
  title: string
  genre: string
  description: string
  total_words: number
  total_chapters: number
  active_hooks: number
  created_at: string
  updated_at: string
}

export interface Chapter {
  id: string
  chapter_id: string
  book_id?: string  // mock 数据携带（R1 修复期间补齐，使 mock 回退路径类型通过）
  chapter_number: number
  title: string
  status: string
  word_count: number
  volume: string
  updated_at: string
  target_words: number
  content?: string
  summary?: string | Record<string, unknown>
}

export interface Character {
  id: string
  book_id: string
  name: string
  role: string
  tag: string
  avatar_color: string
  portrait: string
  personality: string
  background: string
  motivation: string
  abilities: string
  catchphrase: string
  growth_arc: GrowthNode[]
  relationships: Relationship[]
  created_at: string
  updated_at: string
}

export interface GrowthNode {
  id: string
  chapter_range: string
  description: string
  milestone: string
}

export interface Relationship {
  target_id: string
  target_name: string
  type: string
  description: string
}

export interface Hook {
  id: string
  book_id: string
  title: string
  description: string
  status: 'planted' | 'activated' | 'advancing' | 'resolved'
  planted_chapter: number
  target_chapter: number
  priority: 'high' | 'medium' | 'low'
  created_at: string
  updated_at: string
}

export interface TimelineEvent {
  id: string
  book_id: string
  title: string
  description: string
  time_point: string
  chapter_ref: number
  category: string
  created_at: string
}

export interface WorldBuilding {
  id: string
  book_id: string
  geography: string
  factions: string
  power_system: string
  history: string
  social_rules: string
  factions_graph: FactionNode[]
  timeline_events: TimelineEvent[]
}

export interface FactionNode {
  id: string
  name: string
  description: string
  relations: { target: string; type: string }[]
}

export interface OutlineNode {
  id: string
  title: string
  type: 'book' | 'volume' | 'chapter'
  summary?: string
  children?: OutlineNode[]
  chapter_number?: number
  beat_points?: BeatPoint[]
}

export interface BeatPoint {
  id: string
  label: string
  description: string
  act: 1 | 2 | 3
}

// ─── 简化版大纲结构（v3.6+）───
// 为写作模块的上下文查询而设计：按章节号即可拉取完整写作上下文

export interface OutlineVolume {
  id: string
  number: number
  title: string
  story_arc: string
  chapters: OutlineChapter[]
}

export interface OutlineChapter {
  id: string
  number: number
  title: string
  summary: string
  characters: string[]  // 出场角色名列表（写作用：拉取角色卡）
}

export interface Foreshadow {
  id: string
  purpose: string
  description: string
  start_chapter: number
  end_chapter: number
  characters: string[]
  status: 'planted' | 'active' | 'resolved'
}

/** 写作上下文：写第 N 章时，后端一次性返回所有需要的数据 */
export interface WritingContext {
  chapter_number: number
  volume: { number: number; title: string; story_arc: string } | null
  current_chapter: { title: string; summary: string; characters: string[] } | null
  prev_chapters: { number: number; title: string; summary: string }[]
  next_chapters: { number: number; title: string; summary: string }[]
  active_characters: { name: string; role: string; personality: string; background: string }[]
  active_foreshadows: { purpose: string; start_chapter: number; end_chapter: number; characters: string[] }[]
  world_summary: { geography: string; power_system: string; factions: string }
}

export interface WorkflowState {
  workflow_id: string
  workflow_type: string
  book_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'waiting_approval'
  current_node: string
  loop_count: number
  created_at: string
  updated_at: string
  error: string | null
  nodes: Record<string, NodeResult>
  pending_approval: PendingApproval | null
  artifact_summary?: Record<string, unknown>
}

export interface NodeResult {
  node_id: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'waiting_approval'
  summary: string
  output_files: string[]
  metadata: Record<string, unknown>
  error: string | null
}

export interface PendingApproval {
  node_id: string
  artifact_path: string
  [key: string]: unknown
}

export interface QualityScore {
  character_consistency: number
  plot_logic: number
  language_natural: number
  pacing: number
  ai_detection: number
}

export interface TokenBudget {
  total: number
  used: number
  breakdown: {
    label: string
    tokens: number
    color: string
  }[]
}

// ============ 风格指南 ============

export interface StyleGuide {
  narrative_pov: string
  tone: string
  dialogue_style: string
  chapter_ending_hook: boolean
  chapter_ending_hook_instruction: string
  pacing: {
    overall_curve: string
    tension_density: string
    climax_frequency: string
  }
  webnovel_conventions: {
    face_slapping_rhythm: string
    power_progression: string
    foreshadowing_rules: string
  }
  custom_rules: string
}

export const DEFAULT_STYLE_GUIDE: StyleGuide = {
  narrative_pov: '第三人称全知视角，偶尔切入主角内心独白',
  tone: '轻松幽默中带热血，日常温馨但战斗激烈',
  dialogue_style: '口语化、简洁有力，角色之间有明显语言风格差异',
  chapter_ending_hook: true,
  chapter_ending_hook_instruction: '每章结尾必须留一个悬念或未解决的冲突，驱动读者翻到下一章',
  pacing: {
    overall_curve: '起承转合结构，前3章快节奏引入，中段稳步推进，高潮前蓄势',
    tension_density: '每2000字至少一个小冲突或信息增量点',
    climax_frequency: '每5-8章一个小高潮，每卷末一个大高潮',
  },
  webnovel_conventions: {
    face_slapping_rhythm: '压抑不超过2章，打脸要干脆利落',
    power_progression: '每3-5章可见一次实力提升或新能力获取',
    foreshadowing_rules: '伏笔埋下后5章内必须有呼应，不可遗忘',
  },
  custom_rules: '',
}

export interface WritingConfig {
  target_words_per_chapter: number
  style_guide: StyleGuide
  token_limit: number
  auto_review: boolean
  quality_threshold: number
}

export interface ReviewReport {
  id: string
  chapter_id: string
  scores: QualityScore
  overall_score: number
  issues: ReviewIssue[]
  suggestions: string[]
  created_at: string
}

export interface ReviewIssue {
  type: string
  severity: 'high' | 'medium' | 'low'
  location: string
  description: string
  suggestion: string
}

export interface RecentActivity {
  id: string
  type: 'generate' | 'review' | 'polish' | 'final'
  chapter_title: string
  book_title: string
  timestamp: string
  status: 'success' | 'failed' | 'pending'
}

export interface WorkflowListItem {
  workflow_id: string
  workflow_type: string
  book_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'waiting_approval'
  current_node: string
  nodes: Record<string, NodeResult>
  loop_count: number
  created_at: string
  updated_at: string
  error: string | null
  pending_approval: PendingApproval | null
}

export interface ApprovalData {
  workflow_id: string
  workflow_type: string
  book_id: string
  node_id: string
  waiting_since: string
  prev_agent_node: string
  description: string
  artifact: {
    workflow_id: string
    workflow_type: string
    book_id: string
    node_id: string
    created_at: string
    description: string
    sources: Record<string, unknown>
    files_content: Record<string, string>
  }
}

export interface ApprovalSubmission {
  approved: boolean
  feedback?: string
  modifications?: Record<string, string>
}

export interface WorkflowStartResponse {
  workflow_id: string
  status: string
  book_id: string
  workflow_type: string
}
// ============ 通用对话类型 ============

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  stage?: string
}

export type ChatContext = 'worldbuilding' | 'character' | 'outline' | 'writing'

export const CONTEXT_LABELS: Record<ChatContext, string> = {
  worldbuilding: '世界观构建',
  character: '角色设计',
  outline: '大纲规划',
  writing: '写作工坊',
}

export interface ChatAPIResponse {
  reply: string
  context?: string
  stage?: string
  stage_data?: Record<string, unknown>
  data_updates?: Record<string, string>
  suggestions?: string[]
  model_used?: string
}

export interface ChatHistoryResponse {
  messages: ChatMessage[]
  stage?: string
  stage_data?: Record<string, unknown>
  checkpoint?: ChatCheckpoint | null
}

export interface ChatCheckpoint {
  message_index: number
  summary: string
  confirmed_data?: Record<string, unknown>
  created_at: string
}

export interface CheckpointResponse {
  success: boolean
  message: string
  checkpoint: {
    message_index: number
    created_at: string
  }
}

export interface ConfirmStageResponse {
  success: boolean
  next_stage?: string
  message: string
  checkpoint_created?: boolean
}

// ============ 对话同步分析类型 ============

export interface SyncFieldAnalysis {
  field: string
  label: string
  change_description: string
  proposed_value: string
  current_value: string
}

export interface AnalyzeSyncResponse {
  context: string
  fields: SyncFieldAnalysis[]
  analyzed_message_count: number
}

export interface ApplySyncResponse {
  success: boolean
  context: string
  applied_fields: string[]
  message: string
}

// ============ v4.0 新增类型 ============

export interface WritingContextItem {
  name: string
  content: any
  token_count: number
  truncated: boolean
}

export interface WritingContextResponse {
  chapter_number: number
  chapter_title: string
  items: WritingContextItem[]
  total_tokens: number
}

export interface ChapterMeta {
  number: number
  title: string
  word_count: number
  outline_chapter_id: string
  created_at: string
  updated_at: string
  status: 'draft' | 'completed' | 'revised'
}

// ========== 写作工坊 v2 类型 ==========

export interface ScenePlan {
  id: string
  index: number
  title: string
  purpose: string
  location: string
  time: string
  pov: string
  conflict: string
  outcome: string
  emotional_beat: string
  word_target: number
  written: boolean
  content: string
}

export interface ChapterOutline {
  chapter_number: number
  chapter_title: string
  core_conflict: string
  chapter_purpose: string
  rhythm_type: string
  emotional_arc: string
  ending_hook: string
  characters: string[]
  character_roles: Record<string, string>
  active_foreshadows: string[]
  new_foreshadows: string[]
  scenes: ScenePlan[]
  target_words: number
  raw_response?: string
}

export interface WorkshopContext {
  chapter_number: number
  chapter_title: string
  volume_info: string
  previous_chapter_summary: string
  recent_chapters_summary: string
  world_summary: string
  active_characters: string
  active_foreshadows: string
  timeline_context: string
  custom_notes: string
  total_tokens: number
}

export interface AuditIssue {
  id: string
  type: 'consistency' | 'quality' | 'ai_style' | 'pacing' | 'other'
  severity: 'high' | 'medium' | 'low'
  location: string
  description: string
  suggestion: string
}

export interface AuditResult {
  chapter_number: number
  total_words: number
  target_words: number
  scores: Record<string, number>
  overall_score: number
  issues: AuditIssue[]
  summary: string
  raw_response?: string
}

export interface WorkshopStatus {
  chapter_number: number
  current_step: 'context' | 'outline' | 'writing' | 'audit'
  context_done: boolean
  outline_done: boolean
  writing_progress: number
  total_words: number
  audit_done: boolean
}

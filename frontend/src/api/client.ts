import type {
  Book,
  Character,
  Chapter,
  Hook,
  TimelineEvent,
  WorldBuilding,
  OutlineNode,
  OutlineVolume,
  WritingContext,
  WritingContextResponse,
  ChapterMeta,
  WorkflowState,
  WorkflowListItem,
  WorkflowStartResponse,
  ApprovalData,
  ApprovalSubmission,
  WritingConfig,
  ChatAPIResponse,
  ChatHistoryResponse,
  ConfirmStageResponse,
  CheckpointResponse,
} from '../types'

const BASE_URL = '/api'

interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
}

class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = options

  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  }

  if (body) {
    config.body = JSON.stringify(body)
  }

  const response = await fetch(`${BASE_URL}${path}`, config)

  if (!response.ok) {
    throw new ApiError(`API Error: ${response.status} ${response.statusText}`, response.status)
  }

  return response.json()
}

export const api = {
  // Books
  getBooks: () =>
    request<{ books: Book[]; total: number }>('/books'),
  getBook: (bookId: string) =>
    request<{ book_id: string; config: WritingConfig; stats: Record<string, unknown> }>(`/books/${bookId}`),
  createBook: (data: {
    title: string
    genre: string
    description: string
    target_words_per_chapter: number
    total_target_chapters: number
  }) => request<Book>('/books', { method: 'POST', body: data }),

  // World
  getWorld: (bookId: string) =>
    request<WorldBuilding>(`/books/${bookId}/world`),
  updateWorld: (bookId: string, data: Partial<WorldBuilding>) =>
    request<WorldBuilding>(`/books/${bookId}/world`, { method: 'PUT', body: data }),

  // Characters
  getCharacters: (bookId: string) =>
    request<{ characters: Character[]; total: number }>(`/books/${bookId}/characters`),
  createCharacter: (bookId: string, data: Partial<Character>) =>
    request<Character>(`/books/${bookId}/characters`, { method: 'POST', body: data }),
  getCharacter: (bookId: string, charId: string) =>
    request<Character>(`/books/${bookId}/characters/${charId}`),
  updateCharacter: (bookId: string, charId: string, data: Partial<Character>) =>
    request<Character>(`/books/${bookId}/characters/${charId}`, { method: 'PUT', body: data }),
  deleteCharacter: (bookId: string, charId: string) =>
    request<{ ok: boolean; deleted_id: string }>(`/books/${bookId}/characters/${charId}`, { method: 'DELETE' }),

  // Outline
  getOutline: (bookId: string) =>
    request<{ outline: OutlineVolume[] }>(`/books/${bookId}/outline`),
  updateOutline: (bookId: string, data: { outline: OutlineVolume[] } | { volumes: OutlineVolume[]; foreshadowing: unknown[] }) =>
    request<unknown>(`/books/${bookId}/outline`, { method: 'PUT', body: data }),
  getWritingContext: (bookId: string, chapterNumber: number) =>
    request<WritingContext>(`/books/${bookId}/writing-context/${chapterNumber}`),

  // Hooks
  getHooks: (bookId: string) =>
    request<{ hooks: Hook[]; total: number }>(`/books/${bookId}/hooks`),
  createHook: (bookId: string, data: Partial<Hook>) =>
    request<Hook>(`/books/${bookId}/hooks`, { method: 'POST', body: data }),
  updateHook: (bookId: string, hookId: string, data: Partial<Hook>) =>
    request<Hook>(`/books/${bookId}/hooks/${hookId}`, { method: 'PUT', body: data }),

  // Timeline
  getTimeline: (bookId: string) =>
    request<{ events: TimelineEvent[]; total: number }>(`/books/${bookId}/timeline`),
  addTimelineEvent: (bookId: string, data: Partial<TimelineEvent>) =>
    request<TimelineEvent>(`/books/${bookId}/timeline`, { method: 'POST', body: data }),

  // Chapters
  getChapters: (bookId: string) =>
    request<{ chapters: Chapter[]; total: number }>(`/books/${bookId}/chapters`),
  getChapter: (bookId: string, chapterId: string) =>
    request<Chapter>(`/books/${bookId}/chapters/${chapterId}`),
  getChapterMetas: (bookId: string) =>
    request<import('../types').ChapterMeta[]>(`/books/${bookId}/chapters`),
  getChapterByNumber: (bookId: string, number: number) =>
    request<Chapter>(`/books/${bookId}/chapters/${number}`),

  // Workflows
  startNovelSetup: (bookId: string, data?: { genre?: string; description?: string; character_ideas?: object[] }) =>
    request<WorkflowStartResponse>(`/books/${bookId}/workflow/novel-setup`, { method: 'POST', body: data || {} }),
  startChapterProduction: (bookId: string, data?: { chapter_number?: number; target_words?: number }) =>
    request<WorkflowStartResponse>(`/books/${bookId}/workflow/chapter-production`, { method: 'POST', body: data || {} }),
  startRevision: (bookId: string, data?: { chapter_number?: number; revision_mode?: string; instructions?: string }) =>
    request<WorkflowStartResponse>(`/books/${bookId}/workflow/revision`, { method: 'POST', body: data || {} }),
  getWorkflowStatus: (workflowId: string) =>
    request<WorkflowState>(`/workflows/${workflowId}/status`),
  getAllWorkflows: () =>
    request<{ workflows: WorkflowListItem[]; total: number }>('/workflows/list'),

  // Approval
  getApproval: (workflowId: string) =>
    request<ApprovalData>(`/workflows/${workflowId}/approval`),
  submitApproval: (workflowId: string, data: ApprovalSubmission) =>
    request<{ success: boolean; message: string }>(`/workflows/${workflowId}/approval`, {
      method: 'POST',
      body: data,
    }),

  // Config
  getConfig: (bookId: string) =>
    request<WritingConfig>(`/books/${bookId}/config`),
  updateConfig: (bookId: string, data: Partial<WritingConfig>) =>
    request<WritingConfig>(`/books/${bookId}/config`, { method: 'PUT', body: data }),

  // 通用对话
  // chapterNumber：writing 场景下当前选中的章节号，随消息回传后端以同步 stage_data.current_chapter（R1 修复）
  sendChatMessage: (
    bookId: string,
    context: string,
    message: string,
    contextId?: string,
    suppressAutoSync?: boolean,
    chapterNumber?: number,
  ) =>
    request<ChatAPIResponse>(`/books/${bookId}/chat`, {
      method: 'POST',
      body: {
        context,
        message,
        context_id: contextId,
        ...(suppressAutoSync ? { suppress_auto_sync: true } : {}),
        ...(chapterNumber != null ? { chapter_number: chapterNumber } : {}),
      },
    }),
  getChatHistory: (bookId: string, context: string, contextId?: string) => {
    let url = `/books/${bookId}/chat/history?context=${context}`
    if (contextId) url += `&context_id=${contextId}`
    return request<ChatHistoryResponse>(url)
  },
  confirmChatStage: (bookId: string, context: string, contextId?: string) =>
    request<ConfirmStageResponse>(`/books/${bookId}/chat/confirm-stage`, {
      method: 'POST',
      body: { context, context_id: contextId },
    }),
  createCheckpoint: (bookId: string, context: string) =>
    request<CheckpointResponse>(`/books/${bookId}/chat/checkpoint`, {
      method: 'POST',
      body: { context },
    }),
  getAllContextsStatus: (bookId: string) =>
    request<{ contexts: Record<string, { message_count: number; confirmed: boolean; stage_data: Record<string, unknown> }> }>(`/books/${bookId}/chat/all-contexts`),

  // 跨模块同步通知
  getSyncNotifications: (bookId: string, forContext: string) =>
    request<{ notifications: Array<{ source: string; source_label: string; timestamp: string; summary: string }> }>(
      `/books/${bookId}/chat/sync-notifications?for_context=${forContext}`
    ),

  // 对话同步分析 — 分析对话提取结构化数据变更 / 应用变更到数据文件
  analyzeSync: (bookId: string, context: string) =>
    request<import('../types').AnalyzeSyncResponse>(`/books/${bookId}/chat/analyze-sync`, {
      method: 'POST',
      body: { context },
    }),
  applySync: (bookId: string, context: string, selectedFields: Record<string, string>) =>
    request<import('../types').ApplySyncResponse>(`/books/${bookId}/chat/apply-sync`, {
      method: 'POST',
      body: { context, selected_fields: selectedFields },
    }),

  // ===== 写作工坊 v2 API =====
  getWorkshopContext: (bookId: string, chapterNumber: number) =>
    request<import('../types').WorkshopContext>(`/books/${bookId}/workshop/context/${chapterNumber}`),
  updateWorkshopContext: (bookId: string, chapterNumber: number, data: Partial<import('../types').WorkshopContext>) =>
    request<{ success: boolean; message: string }>(`/books/${bookId}/workshop/context/${chapterNumber}`, {
      method: 'PUT',
      body: data,
    }),
  generateWorkshopOutline: (bookId: string, data: { chapter_number: number; target_words?: number }) =>
    request<import('../types').ChapterOutline>(`/books/${bookId}/workshop/outline/generate`, {
      method: 'POST',
      body: data,
    }),
  getWorkshopOutline: (bookId: string, chapterNumber: number) =>
    request<import('../types').ChapterOutline>(`/books/${bookId}/workshop/outline/${chapterNumber}`),
  updateWorkshopOutline: (bookId: string, chapterNumber: number, data: import('../types').ChapterOutline | Record<string, unknown>) =>
    request<{ success: boolean; message: string }>(`/books/${bookId}/workshop/outline/${chapterNumber}`, {
      method: 'PUT',
      body: data,
    }),
  writeScene: (bookId: string, data: { chapter_number: number; scene_index: number; instructions?: string }) =>
    request<{ success: boolean; scene_index: number; content: string; word_count: number }>(`/books/${bookId}/workshop/write-scene`, {
      method: 'POST',
      body: data,
    }),
  rewriteScene: (bookId: string, data: { chapter_number: number; scene_index: number; instructions?: string }) =>
    request<{ success: boolean; scene_index: number; content: string; word_count: number }>(`/books/${bookId}/workshop/rewrite-scene`, {
      method: 'POST',
      body: data,
    }),
  getFullChapter: (bookId: string, chapterNumber: number) =>
    request<{ chapter_number: number; content: string; word_count: number }>(`/books/${bookId}/workshop/full-chapter/${chapterNumber}`),
  auditChapter: (bookId: string, chapterNumber: number) =>
    request<import('../types').AuditResult>(`/books/${bookId}/workshop/audit/${chapterNumber}`, {
      method: 'POST',
    }),
  getAuditResult: (bookId: string, chapterNumber: number) =>
    request<import('../types').AuditResult>(`/books/${bookId}/workshop/audit/${chapterNumber}`),
  getWorkshopStatus: (bookId: string, chapterNumber: number) =>
    request<import('../types').WorkshopStatus>(`/books/${bookId}/workshop/status/${chapterNumber}`),
}

export default api
import { create } from 'zustand'
import { api } from '../api/client'
import {
  mockBooks,
  mockCharacters,
  mockChapters,
  mockHooks,
  mockTimelineEvents,
  mockWorldBuilding,
  mockOutline,
  mockWorkflow,
} from '../data/mock'
import type {
  Book,
  Chapter,
  Character,
  Hook,
  TimelineEvent,
  WorldBuilding,
  OutlineVolume,
  OutlineNode,
  WorkflowState,
  WorkflowListItem,
  ApprovalData,
} from '../types'

// localStorage helpers
// v3.3: versioned key to auto-invalidate stale book IDs from older versions
const LS_BOOK_KEY = 'nw-book-id-v3r2'

function loadBookId(): string | null {
  try {
    return localStorage.getItem(LS_BOOK_KEY)
  } catch {
    return null
  }
}

function saveBookId(id: string | null) {
  try {
    if (id) {
      localStorage.setItem(LS_BOOK_KEY, id)
    } else {
      localStorage.removeItem(LS_BOOK_KEY)
    }
  } catch {
    // ignore
  }
}

// Toast helper
type ToastType = 'success' | 'error' | 'info'
type ToastFn = ((msg: string, type?: ToastType) => void) | null
let toastFn: ToastFn = null

export function setToastHandler(fn: ToastFn) {
  toastFn = fn
}

function notify(msg: string, type: ToastType = 'info') {
  if (toastFn) toastFn(msg, type)
}

// External notify — allows components outside the store to trigger toasts
export { notify as notifyToast }
export type { ToastType }

interface AppState {
  // Book
  currentBookId: string | null
  books: Book[]
  booksLoading: boolean

  // Detail
  currentChapterId: string | null
  chapters: Chapter[]
  characters: Character[]
  hooks: Hook[]
  timelineEvents: TimelineEvent[]
  worldData: WorldBuilding | null
  outlineData: OutlineVolume[]
  outlineLoading: boolean
  selectedChapter: number
  writingContext: any  // WritingContextResponse | null
  chapterMetas: any[]  // ChapterMeta[]

  // Workflow
  workflow: WorkflowState | null
  allWorkflows: WorkflowListItem[]
  approvalData: ApprovalData | null
  workflowPolling: boolean

  // UI
  sidebarCollapsed: boolean
  rightPanelCollapsed: boolean
  useMockData: boolean

  // Actions - setters
  setCurrentBook: (bookId: string | null) => void
  setCurrentChapter: (chapterId: string | null) => void
  toggleSidebar: () => void
  toggleRightPanel: () => void

  // Async actions - data fetching
  selectChapter: (n: number) => void
  fetchChapterMetas: (bookId: string) => Promise<void>
  fetchWritingContext: (bookId: string, chapterNumber: number) => Promise<void>
  fetchBooks: () => Promise<void>
  fetchBookDetail: (bookId: string) => Promise<void>
  fetchWorld: (bookId: string) => Promise<void>
  saveWorld: (bookId: string, data: Partial<WorldBuilding>) => Promise<boolean>
  fetchCharacters: (bookId: string) => Promise<void>
  createCharacter: (bookId: string, data: Partial<Character>) => Promise<boolean>
  updateCharacter: (bookId: string, charId: string, data: Partial<Character>) => Promise<boolean>
  deleteCharacter: (bookId: string, charId: string) => Promise<boolean>
  fetchOutline: (bookId: string) => Promise<void>
  saveOutline: (bookId: string, outline: OutlineNode[] | OutlineVolume[]) => Promise<boolean>
  fetchHooks: (bookId: string) => Promise<void>
  fetchTimeline: (bookId: string) => Promise<void>
  fetchChapters: (bookId: string) => Promise<void>
  fetchChapterContent: (bookId: string, chapterId: string) => Promise<Chapter | null>
  createBook: (data: {
    title: string
    genre: string
    description: string
    target_words_per_chapter: number
    total_target_chapters: number
  }) => Promise<Book | null>

  // Workflow actions
  startWorkflow: (bookId: string, type: 'novel-setup' | 'chapter-production' | 'revision', opts?: { chapter_number?: number; revision_mode?: string }) => Promise<void>
  fetchWorkflowStatus: (workflowId: string) => Promise<void>
  fetchAllWorkflows: () => Promise<void>
  fetchApproval: (workflowId: string) => Promise<void>
  submitApproval: (workflowId: string, data: { approved: boolean; feedback?: string; modifications?: Record<string, string> }) => Promise<boolean>
  startWorkflowPolling: (workflowId: string) => void
  stopWorkflowPolling: () => void

  // Setters
  setBooks: (books: Book[]) => void
  setChapters: (chapters: Chapter[]) => void
  setCharacters: (characters: Character[]) => void
  setHooks: (hooks: Hook[]) => void
  setWorkflow: (workflow: WorkflowState | null) => void

  // Toast
  notify: (msg: string, type?: ToastType) => void
}

let pollTimer: ReturnType<typeof setInterval> | null = null

export const useStore = create<AppState>((set, get) => ({
  currentBookId: loadBookId(),
  currentChapterId: null,
  sidebarCollapsed: false,
  rightPanelCollapsed: false,
  books: [],
  booksLoading: false,
  chapters: [],
  characters: [],
  hooks: [],
  timelineEvents: [],
  worldData: null,
  outlineData: [],
  outlineLoading: false,
  selectedChapter: 1,
  writingContext: null as any,
  chapterMetas: [] as any[],
  workflow: null,
  allWorkflows: [],
  approvalData: null,
  workflowPolling: false,
  useMockData: true,

  setCurrentBook: (bookId) => {
    saveBookId(bookId)
    set({ currentBookId: bookId })
  },
  setCurrentChapter: (chapterId) => set({ currentChapterId: chapterId }),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  toggleRightPanel: () => set((state) => ({ rightPanelCollapsed: !state.rightPanelCollapsed })),

  // ---- Fetchers ----

  selectChapter: (n: number) => set({ selectedChapter: n }),

  fetchChapterMetas: async (bookId: string) => {
    try {
      const res = await api.getChapters(bookId)
      const metas = (res.chapters || []).map((ch) => ({
        number: ch.chapter_number,
        title: ch.title,
        status: ch.status,
        word_count: ch.word_count,
      }))
      set({ chapterMetas: metas })
    } catch(e) { console.error(e) }
  },

  fetchWritingContext: async (bookId: string, chapterNumber: number) => {
    try {
      const ctx = await api.getWritingContext(bookId, chapterNumber)
      set({ writingContext: ctx })
    } catch(e) { console.error(e) }
  },

  fetchBooks: async () => {
    set({ booksLoading: true })
    try {
      const res = await api.getBooks()
      const booksList = res.books || []
      const { currentBookId } = get()

      // Validate currentBookId against fetched books
      let validBookId = currentBookId
      if (booksList.length === 0) {
        // No books at all — clear selection
        validBookId = null
      } else if (!currentBookId || !booksList.find((b) => b.id === currentBookId)) {
        // currentBookId is null or doesn't exist in books — select first
        validBookId = booksList[0].id
      }

      set({ books: booksList, useMockData: false, currentBookId: validBookId })
      // Also persist to localStorage
      if (validBookId !== currentBookId) {
        saveBookId(validBookId)
      }
    } catch {
      set({ books: [], useMockData: false })
      console.warn('[API] fetchBooks failed')
    } finally {
      set({ booksLoading: false })
    }
  },

  fetchBookDetail: async (bookId: string) => {
    try {
      await api.getBook(bookId)
    } catch {
      console.warn('[API] fetchBookDetail failed')
    }
  },

  fetchWorld: async (bookId: string) => {
    try {
      const data = await api.getWorld(bookId)
      set({ worldData: data })
    } catch {
      set({ worldData: mockWorldBuilding })
      console.warn('[API] fetchWorld failed, using mock')
    }
  },

  saveWorld: async (bookId: string, data: Partial<WorldBuilding>) => {
    try {
      const updated = await api.updateWorld(bookId, data)
      set({ worldData: updated })
      notify('世界观已保存', 'success')
      return true
    } catch {
      set({ worldData: { ...mockWorldBuilding, ...data } })
      notify('保存失败，已使用本地数据', 'error')
      return false
    }
  },

  fetchCharacters: async (bookId: string) => {
    try {
      const res = await api.getCharacters(bookId)
      set({ characters: res.characters })
    } catch {
      set({ characters: mockCharacters.filter((c) => c.book_id === bookId) })
      console.warn('[API] fetchCharacters failed, using mock')
    }
  },

  createCharacter: async (bookId: string, data: Partial<Character>) => {
    try {
      const created = await api.createCharacter(bookId, data)
      set((s) => ({ characters: [...s.characters, created] }))
      notify('角色已创建', 'success')
      return true
    } catch {
      // fallback: add locally
      const local: Character = {
        id: `char-${Date.now()}`,
        book_id: bookId,
        name: data.name || '未命名',
        role: data.role || '配角',
        tag: data.tag || '',
        avatar_color: data.avatar_color || '#666666',
        portrait: data.portrait || '',
        personality: data.personality || '',
        background: data.background || '',
        motivation: data.motivation || '',
        abilities: data.abilities || '',
        catchphrase: data.catchphrase || '',
        growth_arc: [],
        relationships: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
      set((s) => ({ characters: [...s.characters, local] }))
      notify('角色创建失败，已本地添加', 'error')
      return false
    }
  },

  updateCharacter: async (bookId: string, charId: string, data: Partial<Character>) => {
    try {
      const updated = await api.updateCharacter(bookId, charId, data)
      set((s) => ({
        characters: s.characters.map((c) => (c.id === charId ? updated : c)),
      }))
      notify('角色已更新', 'success')
      return true
    } catch {
      set((s) => ({
        characters: s.characters.map((c) =>
          c.id === charId ? { ...c, ...data, updated_at: new Date().toISOString() } : c
        ),
      }))
      notify('更新失败，已使用本地数据', 'error')
      return false
    }
  },

  deleteCharacter: async (bookId: string, charId: string) => {
    try {
      await api.deleteCharacter(bookId, charId)
      set((s) => ({
        characters: s.characters.filter((c) => c.id !== charId),
      }))
      notify('角色已删除', 'success')
      return true
    } catch {
      notify('删除失败', 'error')
      return false
    }
  },

  fetchOutline: async (bookId: string) => {
    set({ outlineLoading: true })
    try {
      const res = await api.getOutline(bookId)
      set({ outlineData: res.outline })
    } catch {
      set({ outlineData: mockOutline as unknown as OutlineVolume[] })
      console.warn('[API] fetchOutline failed, using mock')
    } finally {
      set({ outlineLoading: false })
    }
  },

  saveOutline: async (bookId: string, outline: OutlineNode[] | OutlineVolume[]) => {
    try {
      const updated = await api.updateOutline(bookId, { outline: outline as unknown as OutlineVolume[] })
      set({ outlineData: updated as OutlineVolume[] })
      notify('大纲已保存', 'success')
      return true
    } catch {
      set({ outlineData: outline as unknown as OutlineVolume[] })
      notify('保存失败，已使用本地数据', 'error')
      return false
    }
  },

  fetchHooks: async (bookId: string) => {
    try {
      const res = await api.getHooks(bookId)
      set({ hooks: res.hooks })
    } catch {
      set({ hooks: mockHooks.filter((h) => h.book_id === bookId) })
      console.warn('[API] fetchHooks failed, using mock')
    }
  },

  fetchTimeline: async (bookId: string) => {
    try {
      const res = await api.getTimeline(bookId)
      set({ timelineEvents: res.events })
    } catch {
      set({ timelineEvents: mockTimelineEvents.filter((e) => e.book_id === bookId) })
      console.warn('[API] fetchTimeline failed, using mock')
    }
  },

  fetchChapters: async (bookId: string) => {
    try {
      const res = await api.getChapters(bookId)
      set({ chapters: res.chapters })
    } catch {
      set({ chapters: mockChapters.filter((c) => c.book_id === bookId) })
      console.warn('[API] fetchChapters failed, using mock')
    }
  },

  fetchChapterContent: async (bookId: string, chapterId: string) => {
    try {
      const ch = await api.getChapter(bookId, chapterId)
      set((s) => ({
        chapters: s.chapters.map((c) => (c.id === chapterId ? ch : c)),
      }))
      return ch
    } catch {
      const local = mockChapters.find((c) => c.id === chapterId)
      if (local) {
        set((s) => ({
          chapters: s.chapters.map((c) => (c.id === chapterId ? local : c)),
        }))
      }
      return local || null
    }
  },

  createBook: async (data) => {
    try {
      const book = await api.createBook(data)
      if (!book || !book.id) {
        notify('创建失败：返回数据无效', 'error')
        return null
      }
      set((s) => ({ books: [book, ...s.books], currentBookId: book.id }))
      saveBookId(book.id)
      notify('书籍已创建', 'success')
      return book
    } catch {
      const local: Book = {
        id: `book-${Date.now()}`,
        title: data.title,
        genre: data.genre,
        description: data.description,
        total_words: 0,
        total_chapters: 0,
        active_hooks: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
      set((s) => ({ books: [local, ...s.books], currentBookId: local.id }))
      saveBookId(local.id)
      notify('创建失败，已本地添加', 'error')
      return local
    }
  },

  // ---- Workflow ----

  startWorkflow: async (bookId: string, type: 'novel-setup' | 'chapter-production' | 'revision', opts?: { chapter_number?: number; revision_mode?: string }) => {
    try {
      let res: { workflow_id: string; status: string; book_id: string; workflow_type: string }
      switch (type) {
        case 'novel-setup':
          res = await api.startNovelSetup(bookId)
          break
        case 'chapter-production':
          res = await api.startChapterProduction(bookId, { chapter_number: opts?.chapter_number })
          break
        case 'revision':
          res = await api.startRevision(bookId, { chapter_number: opts?.chapter_number, revision_mode: opts?.revision_mode })
          break
      }
      // Build initial WorkflowState from the start response
      const initialWf: WorkflowState = {
        workflow_id: res.workflow_id,
        workflow_type: res.workflow_type,
        book_id: res.book_id,
        status: 'running',
        current_node: '',
        loop_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        error: null,
        nodes: {},
        pending_approval: null,
      }
      set({ workflow: initialWf })
      get().startWorkflowPolling(res.workflow_id)
      notify('工作流已启动', 'success')
    } catch {
      set({ workflow: mockWorkflow })
      notify('工作流启动失败，显示模拟数据', 'error')
    }
  },

  fetchWorkflowStatus: async (workflowId: string) => {
    try {
      const status = await api.getWorkflowStatus(workflowId)
      set({ workflow: status })
      // If waiting for approval, fetch approval data
      if (status.status === 'waiting_approval') {
        get().fetchApproval(workflowId)
      }
    } catch {
      console.warn('[API] fetchWorkflowStatus failed')
    }
  },

  fetchAllWorkflows: async () => {
    try {
      const res = await api.getAllWorkflows()
      set({ allWorkflows: res.workflows })
    } catch {
      set({ allWorkflows: [] })
      console.warn('[API] fetchAllWorkflows failed')
    }
  },

  fetchApproval: async (workflowId: string) => {
    try {
      const data = await api.getApproval(workflowId)
      set({ approvalData: data })
    } catch {
      set({ approvalData: null })
      console.warn('[API] fetchApproval failed')
    }
  },

  submitApproval: async (workflowId: string, data) => {
    try {
      await api.submitApproval(workflowId, data)
      set({ approvalData: null })
      // Refresh workflow status
      get().fetchWorkflowStatus(workflowId)
      notify(data.approved ? '审批已通过' : '审批已驳回', data.approved ? 'success' : 'info')
      return true
    } catch {
      notify('审批提交失败', 'error')
      return false
    }
  },

  startWorkflowPolling: (workflowId: string) => {
    get().stopWorkflowPolling()
    set({ workflowPolling: true })
    pollTimer = setInterval(() => {
      const { workflow } = get()
      if (!workflow || workflow.status === 'completed' || workflow.status === 'failed') {
        get().stopWorkflowPolling()
        return
      }
      get().fetchWorkflowStatus(workflowId)
    }, 5000)
  },

  stopWorkflowPolling: () => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    set({ workflowPolling: false })
  },

  // Setters
  setBooks: (books) => set({ books }),
  setChapters: (chapters) => set({ chapters }),
  setCharacters: (characters) => set({ characters }),
  setHooks: (hooks) => set({ hooks }),
  setWorkflow: (workflow) => set({ workflow }),

  // Toast
  notify: (msg: string, type?: ToastType) => notify(msg, type),
}))

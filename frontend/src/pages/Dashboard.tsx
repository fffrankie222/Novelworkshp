import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Plus,
  BookOpen,
  FileText,
  Sparkles,
  TrendingUp,
  Clock,
  X,
  ChevronRight,
  Target,
  AlertCircle,
  Wand2,
  Loader2,
} from 'lucide-react'
import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import BookCard from '../components/BookCard'
import WorkflowStatus from '../components/WorkflowStatus'
import { useStore } from '../store'
import type { Book } from '../types'

const ACTIVITY_TYPE_LABELS: Record<string, { label: string; icon: string }> = {
  generate: { label: '生成章节', icon: '✎' },
  review: { label: '质量审核', icon: '◈' },
  polish: { label: '润色优化', icon: '✦' },
  final: { label: '定稿确认', icon: '✓' },
}

export default function Dashboard() {
  const navigate = useNavigate()
  const {
    currentBookId, setCurrentBook,
    books, booksLoading, allWorkflows,
    fetchBooks, fetchAllWorkflows, createBook,
    hooks, chapters, fetchHooks, fetchChapters,
  } = useStore()

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newBook, setNewBook] = useState({
    title: '',
    genre: '玄幻',
    description: '',
    target_words_per_chapter: 3000,
    total_target_chapters: 50,
  })
  const [creating, setCreating] = useState(false)

  // Fetch books and workflows on mount
  useEffect(() => {
    fetchBooks()
    fetchAllWorkflows()
  }, [])

  // Fetch current book data (only after books list is loaded)
  useEffect(() => {
    if (!booksLoading && currentBookId) {
      fetchHooks(currentBookId)
      fetchChapters(currentBookId)
    }
  }, [currentBookId, booksLoading]) // eslint-disable-line react-hooks/exhaustive-deps

  const currentBook = books.find((b) => b.id === currentBookId) || books[0]
  const bookHooks = hooks.length > 0 ? hooks.filter((h) => h.book_id === currentBook?.id) : []
  const bookChapters = chapters.length > 0 ? chapters.slice(0, 8) : []
  const activeHooks = bookHooks.filter(
    (h) => h.status === 'activated' || h.status === 'advancing'
  )
  const completedChapters = bookChapters.filter((c) => c.status === 'final').length

  // Running workflows for current book
  const runningWorkflows = allWorkflows.filter(
    (wf) => wf.book_id === currentBook?.id && (wf.status === 'running' || wf.status === 'waiting_approval')
  )

  const totalWords = books.reduce((sum, b) => sum + b.total_words, 0)
  const totalChapters = books.reduce((sum, b) => sum + b.total_chapters, 0)
  const totalActiveHooks = books.reduce((sum, b) => sum + b.active_hooks, 0)

  const handleBookClick = (book: Book) => {
    setCurrentBook(book.id)
    navigate('/writing')
  }

  const handleCreateBook = async () => {
    if (!newBook.title.trim()) return
    setCreating(true)
    const book = await createBook(newBook)
    if (book && book.id) {
      // createBook already set currentBookId in the store
      setShowCreateModal(false)
      setNewBook({
        title: '',
        genre: '玄幻',
        description: '',
        target_words_per_chapter: 3000,
        total_target_chapters: 50,
      })
      navigate('/world')
    }
    setCreating(false)
  }

  return (
    <div className="min-h-screen">
      {/* Page Header */}
      <div className="px-8 pt-8 pb-6 border-b border-nw-border">
        <div className="flex items-start justify-between">
          <div>
            <p className="nw-label mb-1">dashboard</p>
            <h1 className="text-xl font-semibold text-white tracking-wide">
              写作工作台
            </h1>
            <p className="text-xs text-nw-text-secondary mt-1">
              {format(new Date(), 'yyyy年M月d日 EEEE', { locale: zhCN })}
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="nw-btn nw-btn-primary"
          >
            <Plus className="w-3.5 h-3.5" strokeWidth={2} />
            新建项目
          </button>
        </div>
      </div>

      <div className="p-8 space-y-8">
        {/* Stats Overview */}
        <section>
          <h2 className="nw-label mb-3">全局概览</h2>
          <div className="grid grid-cols-4 gap-4">
            {[
              {
                label: '项目总数',
                value: books.length,
                unit: '部',
                icon: BookOpen,
                trend: '+1 本月',
              },
              {
                label: '累计字数',
                value: (totalWords / 10000).toFixed(1),
                unit: '万字',
                icon: FileText,
                trend: `+${Math.round(totalWords * 0.08 / 1000)}k 本周`,
              },
              {
                label: '章节总数',
                value: totalChapters,
                unit: '章',
                icon: Target,
                trend: `${completedChapters} 已定稿`,
              },
              {
                label: '活跃伏笔',
                value: totalActiveHooks,
                unit: '条',
                icon: AlertCircle,
                trend: '需关注回收',
              },
            ].map((stat, i) => (
              <div
                key={i}
                className="nw-card p-4 hover:border-nw-border-light transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <span className="nw-label">{stat.label}</span>
                  <stat.icon
                    className="w-4 h-4 text-nw-text-muted"
                    strokeWidth={1.5}
                  />
                </div>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-2xl font-semibold text-white font-mono">
                    {stat.value}
                  </span>
                  <span className="text-xs text-nw-text-muted">{stat.unit}</span>
                </div>
                <div className="mt-2 flex items-center gap-1 text-[10px] text-nw-text-secondary">
                  <TrendingUp
                    className="w-3 h-3 text-nw-text-muted"
                    strokeWidth={1.5}
                  />
                  {stat.trend}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Books Grid + Sidebar */}
        <section className="grid grid-cols-3 gap-6">
          {/* Books */}
          <div className="col-span-2">
            <div className="flex items-center justify-between mb-3">
              <h2 className="nw-label">我的项目</h2>
              <button
                onClick={() => setShowCreateModal(true)}
                className="text-[11px] text-nw-text-secondary hover:text-white transition-colors flex items-center gap-1"
              >
                <Plus className="w-3 h-3" strokeWidth={1.5} />
                新建
              </button>
            </div>
            {booksLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-5 h-5 text-nw-text-muted animate-spin" />
                <span className="ml-2 text-sm text-nw-text-muted">加载中...</span>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {books.map((book) => (
                  <BookCard
                    key={book.id}
                    book={book}
                    active={book.id === currentBookId}
                    onClick={() => handleBookClick(book)}
                  />
                ))}
                {/* New Book Card */}
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="nw-card p-5 flex flex-col items-center justify-center min-h-[180px] text-nw-text-muted hover:text-white hover:border-white transition-all group"
                >
                  <Plus
                    className="w-6 h-6 mb-2 group-hover:scale-110 transition-transform"
                    strokeWidth={1}
                  />
                  <span className="text-xs">创建新项目</span>
                </button>
              </div>
            )}
          </div>

          {/* Recent Activity */}
          <div>
            <h2 className="nw-label mb-3">最近活动</h2>
            {books.length === 0 ? (
              <div className="nw-card p-8 text-center text-nw-text-muted">
                <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">创建第一个项目后，活动记录将在此显示</p>
              </div>
            ) : (
              <div className="nw-card divide-y divide-nw-border">
                {books.map((book) => (
                  <button
                    key={book.id}
                    onClick={() => handleBookClick(book)}
                    className="w-full p-3 hover:bg-white/[0.02] transition-colors text-left flex items-center gap-3"
                  >
                    <BookOpen className="w-4 h-4 text-nw-text-muted shrink-0" />
                    <span className="text-xs text-white truncate">{book.title}</span>
                    <span className="nw-badge text-[10px]">
                      {book.total_words ? `${(book.total_words / 10000).toFixed(1)}万字` : '未开始'}
                    </span>
                    <ChevronRight className="w-3 h-3 ml-auto text-nw-text-muted" />
                  </button>
                ))}
              </div>
            )}

            {/* Running Workflows */}
            {runningWorkflows.length > 0 && (
              <div className="mt-4">
                <h2 className="nw-label mb-3">运行中的工作流</h2>
                <div className="space-y-3">
                  {runningWorkflows.map((wf) => (
                    <WorkflowStatus key={wf.workflow_id} workflow={wf} showApproval={wf.status === 'waiting_approval'} />
                  ))}
                </div>
              </div>
            )}

            {/* Current Book Quick Stats */}
            {currentBook && (
              <div className="mt-4">
                <h2 className="nw-label mb-3">当前项目速览</h2>
                <div className="nw-card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium text-white">
                      {currentBook.title}
                    </span>
                    <span className="nw-badge">{currentBook.genre}</span>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[11px] text-nw-text-muted">
                          写作进度
                        </span>
                        <span className="text-[11px] font-mono text-white">
                          {completedChapters}/{currentBook.total_chapters} 章
                        </span>
                      </div>
                      <div className="w-full h-px bg-nw-border">
                        <div
                          className="h-px bg-white"
                          style={{
                            width: `${
                              currentBook.total_chapters > 0
                                ? (completedChapters / currentBook.total_chapters) * 100
                                : 0
                            }%`,
                          }}
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 pt-2 border-t border-nw-border">
                      <div>
                        <p className="nw-label">总字数</p>
                        <p className="text-sm font-mono text-white mt-0.5">
                          {(currentBook.total_words / 1000).toFixed(1)}k
                        </p>
                      </div>
                      <div>
                        <p className="nw-label">活跃伏笔</p>
                        <p className="text-sm font-mono text-white mt-0.5">
                          {activeHooks.length}
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() => navigate('/writing')}
                      className="nw-btn w-full mt-2"
                    >
                      <Wand2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                      继续写作
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Create Book Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 nw-fade-in">
          <div className="nw-card w-[480px] max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-nw-border">
              <div>
                <h3 className="text-sm font-medium text-white">新建项目</h3>
                <p className="text-[11px] text-nw-text-muted mt-0.5">
                  创建一个新的小说项目，开启创作之旅
                </p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1 text-nw-text-muted hover:text-white transition-colors"
              >
                <X className="w-4 h-4" strokeWidth={1.5} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-4">
              <div>
                <label className="nw-label block mb-1.5">作品名称</label>
                <input
                  type="text"
                  className="nw-input"
                  placeholder="输入作品名称..."
                  value={newBook.title}
                  onChange={(e) =>
                    setNewBook({ ...newBook, title: e.target.value })
                  }
                  autoFocus
                />
              </div>

              <div>
                <label className="nw-label block mb-1.5">题材类型</label>
                <select
                  className="nw-input"
                  value={newBook.genre}
                  onChange={(e) =>
                    setNewBook({ ...newBook, genre: e.target.value })
                  }
                >
                  <option value="玄幻">玄幻</option>
                  <option value="科幻">科幻</option>
                  <option value="都市">都市</option>
                  <option value="仙侠">仙侠</option>
                  <option value="历史">历史</option>
                  <option value="悬疑">悬疑</option>
                  <option value="言情">言情</option>
                  <option value="其他">其他</option>
                </select>
              </div>

              <div>
                <label className="nw-label block mb-1.5">作品简介</label>
                <textarea
                  className="nw-textarea h-20"
                  placeholder="简要描述你的故事设定、主角和核心冲突..."
                  value={newBook.description}
                  onChange={(e) =>
                    setNewBook({ ...newBook, description: e.target.value })
                  }
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="nw-label block mb-1.5">
                    每章目标字数
                  </label>
                  <input
                    type="number"
                    className="nw-input"
                    value={newBook.target_words_per_chapter}
                    onChange={(e) =>
                      setNewBook({
                        ...newBook,
                        target_words_per_chapter: parseInt(e.target.value) || 3000,
                      })
                    }
                  />
                </div>
                <div>
                  <label className="nw-label block mb-1.5">
                    预计总章节数
                  </label>
                  <input
                    type="number"
                    className="nw-input"
                    value={newBook.total_target_chapters}
                    onChange={(e) =>
                      setNewBook({
                        ...newBook,
                        total_target_chapters: parseInt(e.target.value) || 50,
                      })
                    }
                  />
                </div>
              </div>

              <div className="pt-2 border-t border-nw-border">
                <div className="flex items-start gap-2 text-[11px] text-nw-text-muted">
                  <Sparkles
                    className="w-3.5 h-3.5 text-nw-text-secondary mt-0.5 shrink-0"
                    strokeWidth={1.5}
                  />
                  <p>
                    创建后 AI 将自动启动"新书建立"工作流，帮你生成世界观框架、主角设定和初始大纲。
                  </p>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-nw-border">
              <button
                onClick={() => setShowCreateModal(false)}
                className="nw-btn"
                disabled={creating}
              >
                取消
              </button>
              <button
                onClick={handleCreateBook}
                className="nw-btn nw-btn-primary"
                disabled={!newBook.title.trim() || creating}
              >
                {creating ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" strokeWidth={1.5} />
                )}
                创建并启动 AI
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

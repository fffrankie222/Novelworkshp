import { useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Globe,
  Users,
  ListTree,
  PenTool,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from 'lucide-react'
import { useStore } from '../store'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: '总览' },
  { to: '/world', icon: Globe, label: '世界观' },
  { to: '/characters', icon: Users, label: '角色' },
  { to: '/outline', icon: ListTree, label: '大纲' },
  { to: '/writing', icon: PenTool, label: '写作' },
]

export default function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, currentBookId, setCurrentBook, books, fetchBooks } = useStore()
  const navigate = useNavigate()

  useEffect(() => {
    fetchBooks()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleBookSelect = (bookId: string) => {
    setCurrentBook(bookId)
    navigate('/')
  }

  return (
    <aside
      className={`fixed left-0 top-0 h-full bg-nw-bg-secondary border-r border-nw-border flex flex-col transition-all duration-200 z-50 ${
        sidebarCollapsed ? 'w-14' : 'w-56'
      }`}
    >
      {/* Header / Logo */}
      <div className="flex items-center justify-between px-4 h-14 border-b border-nw-border shrink-0">
        <div className="flex items-center gap-2 overflow-hidden">
          <BookOpen className="w-4 h-4 text-white shrink-0" strokeWidth={1.5} />
          {!sidebarCollapsed && (
            <span className="text-sm font-semibold tracking-wide text-white truncate">
              NOVEL<span className="text-nw-text-muted font-normal">WORKSHOP</span>
            </span>
          )}
        </div>
        {!sidebarCollapsed && (
          <button
            onClick={toggleSidebar}
            className="p-1 text-nw-text-muted hover:text-white transition-colors"
            aria-label="收起侧边栏"
          >
            <ChevronLeft className="w-4 h-4" strokeWidth={1.5} />
          </button>
        )}
        {sidebarCollapsed && (
          <button
            onClick={toggleSidebar}
            className="p-1 text-nw-text-muted hover:text-white transition-colors mx-auto"
            aria-label="展开侧边栏"
          >
            <ChevronRight className="w-4 h-4" strokeWidth={1.5} />
          </button>
        )}
      </div>

      {/* Book Selector */}
      {!sidebarCollapsed && (
        <div className="px-3 py-3 border-b border-nw-border">
          <p className="nw-label mb-2 px-1">项目</p>
          <div className="space-y-0.5">
            {books.length === 0 ? (
              <p className="text-[11px] text-nw-text-muted px-2 py-1">暂无项目，请先创建</p>
            ) : (
              books.map((book) => {
                const active = currentBookId === book.id
                return (
                  <button
                    key={book.id}
                    onClick={() => handleBookSelect(book.id)}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 text-xs transition-all border ${
                      active
                        ? 'border-white text-white bg-white/5'
                        : 'border-transparent text-nw-text-secondary hover:border-nw-border-light hover:text-white'
                    }`}
                  >
                    <div className="w-1.5 h-1.5 bg-current shrink-0" />
                    <span className="truncate">{book.title}</span>
                  </button>
                )
              })
            )}
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3">
        {!sidebarCollapsed && <p className="nw-label mb-2 px-2">功能</p>}
        <div className="space-y-0.5">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-2 py-2 text-xs transition-all border ${
                  isActive
                    ? 'border-white text-white bg-white/5'
                    : 'border-transparent text-nw-text-secondary hover:border-nw-border-light hover:text-white'
                } ${sidebarCollapsed ? 'justify-center' : ''}`
              }
            >
              <item.icon className="w-4 h-4 shrink-0" strokeWidth={1.5} />
              {!sidebarCollapsed && <span className="tracking-wide">{item.label}</span>}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Footer / AI Status */}
      <div className="border-t border-nw-border px-3 py-3 shrink-0">
        {sidebarCollapsed ? (
          <div className="flex justify-center">
            <div className="flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-nw-success" strokeWidth={1.5} />
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-1">
            <div className="w-1.5 h-1.5 rounded-full bg-nw-success nw-pulse" />
            <span className="text-[10px] text-nw-text-muted uppercase tracking-wider">
              AI 在线
            </span>
          </div>
        )}
      </div>
    </aside>
  )
}

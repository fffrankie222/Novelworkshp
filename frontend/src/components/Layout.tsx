import { useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import { useStore } from '../store'

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const sidebarCollapsed = useStore((s) => s.sidebarCollapsed)
  const currentBookId = useStore((s) => s.currentBookId)
  const books = useStore((s) => s.books)
  const booksLoading = useStore((s) => s.booksLoading)
  const setCurrentBook = useStore((s) => s.setCurrentBook)
  const fetchBooks = useStore((s) => s.fetchBooks)

  // Validate currentBookId on mount and whenever books change
  useEffect(() => {
    fetchBooks()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!booksLoading && currentBookId && books.length >= 0) {
      // Check if currentBookId still exists in the books list
      if (currentBookId && !books.find((b) => b.id === currentBookId)) {
        console.warn(`[BookGuard] Book "${currentBookId}" not found, clearing selection`)
        setCurrentBook(null)
        if (location.pathname !== '/') {
          navigate('/')
        }
      }
    }
  }, [currentBookId, books, booksLoading, navigate, location.pathname, setCurrentBook])

  return (
    <div className="flex h-screen overflow-hidden bg-nw-bg text-nw-text">
      <Sidebar />
      <main
        className={`flex-1 overflow-auto transition-all duration-200 ${
          sidebarCollapsed ? 'ml-14' : 'ml-56'
        }`}
      >
        <div className="min-h-full">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'nw-bg': '#0a0a0a',
        'nw-bg-secondary': '#111111',
        'nw-bg-tertiary': '#1a1a1a',
        'nw-card': '#141414',
        'nw-border': '#222222',
        'nw-border-light': '#2a2a2a',
        'nw-text': '#ffffff',
        'nw-text-secondary': '#888888',
        'nw-text-muted': '#555555',
        'nw-success': '#4ade80',
        'nw-warning': '#fbbf24',
        'nw-error': '#ef4444',
        'nw-info': '#60a5fa',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'SF Mono', 'Menlo', 'monospace'],
      },
      borderRadius: {
        'sm': '2px',
        'DEFAULT': '2px',
        'md': '2px',
        'lg': '2px',
      },
    },
  },
  plugins: [],
}

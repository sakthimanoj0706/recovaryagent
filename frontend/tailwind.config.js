/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        fintech: {
          bg: '#080b11',
          surface: '#0f141f',
          surfaceLight: '#182030',
          border: 'rgba(255, 255, 255, 0.08)',
          emerald: '#10b981',
          emeraldGlow: 'rgba(16, 185, 129, 0.15)',
          amber: '#f59e0b',
          amberGlow: 'rgba(245, 158, 11, 0.15)',
          ruby: '#ef4444',
          rubyGlow: 'rgba(239, 68, 68, 0.15)',
          cyan: '#06b6d4',
          cyanGlow: 'rgba(6, 182, 212, 0.15)',
          indigo: '#6366f1',
          indigoGlow: 'rgba(99, 102, 241, 0.15)',
          textMuted: '#94a3b8',
          textBright: '#f8fafc',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'glow-emerald': '0 0 20px rgba(16, 185, 129, 0.3)',
        'glow-cyan': '0 0 20px rgba(6, 182, 212, 0.3)',
        'glow-ruby': '0 0 20px rgba(239, 68, 68, 0.3)',
        'glow-amber': '0 0 20px rgba(245, 158, 11, 0.3)',
      }
    },
  },
  plugins: [],
}

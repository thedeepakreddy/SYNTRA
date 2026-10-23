/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"Geist Mono"', '"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        cyber: {
          cyan: "#00F0FF",
          "cyan-dim": "#0891B2",
          "cyan-glow": "rgba(0, 240, 255, 0.35)",
          emerald: "#00FF9D",
          "emerald-dim": "#059669",
          amber: "#FFB800",
          "amber-dim": "#D97706",
          crimson: "#FF0055",
          "crimson-dim": "#E11D48",
          obsidian: "#020408",
          dark: "#050914",
          surface: "rgba(8, 14, 28, 0.75)",
          card: "rgba(12, 20, 38, 0.65)",
          border: "rgba(255, 255, 255, 0.12)",
          "border-cyan": "rgba(0, 240, 255, 0.25)",
        },
        syntra: {
          bg: "#020408",
          surface: "#070C18",
          panel: "#0B1326",
          card: "#0F1A34",
          border: "rgba(255, 255, 255, 0.12)",
          hover: "rgba(0, 240, 255, 0.08)",
          accent: "#00F0FF",
          muted: "#94A3B8",
          emerald: "#00FF9D",
          amber: "#FFB800",
          rose: "#FF0055",
          cyan: "#00F0FF",
        },
      },
      boxShadow: {
        'liquid-glass': 'inset 0 1.5px 1.5px 0 rgba(255, 255, 255, 0.35), inset 0 -1px 1px 0 rgba(0, 240, 255, 0.18), 0 10px 32px -4px rgba(0, 0, 0, 0.75), 0 0 0 1px rgba(255, 255, 255, 0.1)',
        'liquid-glass-hover': 'inset 0 1.5px 2px 0 rgba(255, 255, 255, 0.5), inset 0 -1.5px 2px 0 rgba(0, 240, 255, 0.35), 0 16px 40px -4px rgba(0, 0, 0, 0.85), 0 0 24px -2px rgba(0, 240, 255, 0.25), 0 0 0 1px rgba(0, 240, 255, 0.35)',
        'liquid-button': 'inset 0 1px 1px 0 rgba(255, 255, 255, 0.45), inset 0 -1px 1px 0 rgba(0, 240, 255, 0.3), 0 4px 16px -2px rgba(0, 240, 255, 0.35), 0 0 0 1px rgba(0, 240, 255, 0.4)',
        'liquid-pill': 'inset 0 1px 1px 0 rgba(255, 255, 255, 0.28), inset 0 -1px 1px 0 rgba(0, 240, 255, 0.1), 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.12)',
        'bezel': '0 0 0 1px rgba(0, 240, 255, 0.15), 0 2px 4px rgba(0, 0, 0, 0.6), 0 12px 28px -4px rgba(0, 0, 0, 0.8)',
        'inner-highlight': 'inset 0 1.5px 1.5px 0 rgba(255, 255, 255, 0.25)',
        'glow-cyan': '0 0 32px -4px rgba(0, 240, 255, 0.35)',
        'glow-emerald': '0 0 32px -4px rgba(0, 255, 157, 0.35)',
        'glow-amber': '0 0 32px -4px rgba(255, 184, 0, 0.35)',
        'glow-crimson': '0 0 32px -4px rgba(255, 0, 85, 0.35)',
        'layered-sm': '0px 2px 4px -1px rgba(0,0,0,0.4), 0px 1px 0px 0px rgba(255,255,255,0.1), 0px 0px 0px 1px rgba(255,255,255,0.08)',
        'layered-md': '0px 0px 0px 1px rgba(255,255,255,0.1), 0px 1px 2px rgba(0,0,0,0.5), 0px 4px 8px rgba(0,0,0,0.4), 0px 16px 32px rgba(0,0,0,0.6)',
      },
      animation: {
        'pulse-subtle': 'pulseSubtle 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2.5s linear infinite',
        'laser-scan': 'laserScan 6s ease-in-out infinite',
      },
      keyframes: {
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        laserScan: {
          '0%, 100%': { transform: 'translateY(-100%)' },
          '50%': { transform: 'translateY(100%)' },
        },
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.23, 1, 0.32, 1)',
        'drawer': 'cubic-bezier(0.32, 0.72, 0, 1)',
      },
    },
  },
  plugins: [],
}

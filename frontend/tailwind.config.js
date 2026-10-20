/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        syntra: {
          bg: "#0B0F17",
          panel: "#111827",
          border: "#1F2937",
          accent: "#3B82F6",
          hover: "#1E293B",
          text: "#F3F4F6",
          muted: "#9CA3AF",
          success: "#10B981",
          warning: "#F59E0B",
          danger: "#EF4444",
        },
      },
    },
  },
  plugins: [],
}

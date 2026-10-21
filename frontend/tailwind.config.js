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
        cyber: {
          cyan: '#00E5FF',
          blue: '#38BDF8',
          indigo: '#4F46E5',
          purple: '#8B5CF6',
          emerald: '#10B981',
          rose: '#F43F5E',
          dark: '#080C16',
          card: '#0F172A',
        }
      }
    },
  },
  plugins: [],
}

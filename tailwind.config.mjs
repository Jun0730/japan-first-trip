/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        indigo: {
          950: '#1a1a3d',
        },
        sakura: {
          50: '#fff5f7',
          100: '#ffe4ea',
          200: '#ffc9d7',
          300: '#ffa1bd',
          400: '#f472a0',
          500: '#ec4d80',
          600: '#d6336c',
        },
      },
      fontFamily: {
        sans: ['"Noto Sans JP"', 'Inter', 'system-ui', 'sans-serif'],
        serif: ['"Noto Serif JP"', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
};

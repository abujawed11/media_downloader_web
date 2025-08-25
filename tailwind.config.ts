import type { Config } from 'tailwindcss'

export default {
  content: [
    './index.html',
    './src/**/*.{ts,tsx,js,jsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          yellow: '#FAD90E',
          black: '#0B0B0B',
          gray: '#1C1C1C',
        },
      },
      borderRadius: {
        '2xl': '1rem',
      },
      boxShadow: {
        soft: '0 8px 24px rgba(0,0,0,0.12)',
      },
    },
    fontFamily: {
      sans: ['ui-sans-serif', 'system-ui', 'Segoe UI', 'Roboto', 'Inter', 'Arial', 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol'],
    },
    container: {
      center: true,
      padding: '1rem',
      screens: {
        sm: '640px',
        md: '768px',
        lg: '1024px',
        xl: '1200px',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/line-clamp'),
  ],
} satisfies Config

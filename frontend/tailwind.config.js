/**
 * Tailwind CSS configuration.
 *
 * The palette mirrors the Material UI theme so both styling systems stay in
 * sync. Custom colours are exposed as Tailwind utilities, e.g. `bg-brand-600`.
 *
 * @type {import('tailwindcss').Config}
 */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef4ff',
          100: '#d9e6ff',
          200: '#bcd3ff',
          300: '#8eb6ff',
          400: '#598eff',
          500: '#3366ff',
          600: '#1f45f5',
          700: '#1a34e1',
          800: '#1c2eb6',
          900: '#1d2e8f',
        },
        ink: {
          50: '#f6f7f9',
          100: '#eceef2',
          200: '#d5dae3',
          300: '#b0bacb',
          400: '#8595ae',
          500: '#657795',
          600: '#50607c',
          700: '#424f65',
          800: '#394354',
          900: '#323a48',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(16, 24, 40, 0.06), 0 1px 3px rgba(16, 24, 40, 0.1)',
      },
    },
  },
  plugins: [],
};

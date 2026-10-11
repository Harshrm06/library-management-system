/**
 * Tailwind CSS configuration with cohesive, premium library aesthetic.
 * Deep Navy, Forest Green accents, Warm Cream backgrounds, Warm Ink typography.
 *
 * @type {import('tailwindcss').Config}
 */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Deep Navy / Midnight Library primary
        brand: {
          50: '#f0f5fa',
          100: '#dbe7f3',
          200: '#bad0e6',
          300: '#8eb2d4',
          400: '#5a8ebf',
          500: '#3871a8',
          600: '#1e3a5f',
          700: '#18304f',
          800: '#12243d',
          900: '#0c1728',
          950: '#070e1a',
        },
        // Forest Green secondary / accent
        forest: {
          50: '#f0f9f4',
          100: '#dcf0e4',
          200: '#bae2cb',
          300: '#8dceaa',
          400: '#57b382',
          500: '#329663',
          600: '#23774e',
          700: '#1e5f40',
          800: '#1a4c35',
          900: '#173f2d',
        },
        // Warm Cream backgrounds & parchment tones
        cream: {
          50: '#fdfcf9',
          100: '#f9f7f1',
          200: '#f3efe3',
          300: '#e9e3d0',
          400: '#ddd2b8',
          500: '#cbba9a',
          600: '#b7a27e',
          700: '#9b8463',
          800: '#7f6c51',
          900: '#685944',
        },
        // Warm Ink text colors
        ink: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
        // Amber / Gold accents
        amber: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
        serif: ['Georgia', 'Cambria', 'Times New Roman', 'serif'],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgba(15, 23, 42, 0.06), 0 1px 2px -1px rgba(15, 23, 42, 0.06)',
        'card-hover': '0 10px 25px -5px rgba(15, 23, 42, 0.08), 0 8px 10px -6px rgba(15, 23, 42, 0.04)',
        elevation: '0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.1)',
      },
    },
  },
  plugins: [],
};

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#2563EB',  // Modern blue, more vibrant
          hover: '#1D4ED8',    // Deeper blue for hover
          light: '#60A5FA',    // Lighter blue for accents
          dark: '#1E40AF',     // Dark blue for emphasis
        },
        success: {
          DEFAULT: '#10B981',  // Modern green
          hover: '#059669',    // Deeper green for hover
          light: '#D1FAE5',    // Light green background
        },
        danger: {
          DEFAULT: '#EF4444',  // Vibrant red
          hover: '#DC2626',    // Deeper red for hover
          light: '#FEE2E2',    // Light red background
        },
        ui: {
          dark: '#111827',     // Near black
          DEFAULT: '#374151',  // Medium gray
          light: '#D1D5DB',    // Light gray
          lighter: '#F3F4F6',  // Very light gray
          hover: '#030712',    // Darkest gray for hover
        },
        league: {
          blue: '#4F46E5',     // Indigo, modern feel
          hover: '#4338CA',    // Deeper indigo for hover
          text: '#E0E7FF',     // Light indigo for text
        },
        notice: {
          orange: '#F97316',   // Vibrant orange
          yellow: '#EAB308',   // Modern yellow
          yellowBg: '#FEF3C7', // Light yellow background
        }
      },
      spacing: {
        '72': '18rem',
        '84': '21rem',
        '96': '24rem',
      },
      borderRadius: {
        '4xl': '2rem',
      },
      transitionDuration: {
        '400': '400ms',
      }
    },
  },
  plugins: [],
}
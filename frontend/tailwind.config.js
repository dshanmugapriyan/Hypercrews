/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkbg: "#040814",      // deep near-black navy background
        darkcard: "#0d1326",    // dark card container navy
        darkborder: "#1c253d",  // subtle borders
        accentcyan: "#00f0ff",  // cybersecurity neon cyan
        accentemerald: "#10b981", // safe emerald
        accentamber: "#f59e0b",   // warning amber
        accentred: "#ef4444"      // critical risk red
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["Geist Mono", "monospace"]
      }
    },
  },
  plugins: [],
}

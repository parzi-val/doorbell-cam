/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            },
            colors: {
                background: "#f8fafc", // Slate 50
                card: "#ffffff",       // White
                primary: "#0f172a",    // Slate 900
                secondary: "#64748b",  // Slate 500
                border: "#e2e8f0",     // Slate 200
                accent: {
                    red: "#ef4444",
                    orange: "#f97316",
                    green: "#22c55e",
                }
            }
        },
    },
    plugins: [],
}

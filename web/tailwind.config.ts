/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    theme: {
        extend: {
            colors: {
                // Couleurs migrées depuis constants.py
                bg: {
                    DEFAULT: "#19192B",
                    light: "#232340",
                    panel: "#28283C",
                },
                accent: {
                    DEFAULT: "#50A0FF",
                    hover: "#64B4FF",
                },
                gold: "#FFC832",
                "game-green": "#50C878",
                "game-red": "#DC3C3C",
            },
            fontFamily: {
                game: ["Inter", "Arial", "sans-serif"],
            },
            maxWidth: {
                mobile: "405px",
            },
        },
    },
    plugins: [],
};

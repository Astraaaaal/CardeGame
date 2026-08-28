/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    theme: {
        extend: {
            colors: {
                // Couleurs migrées depuis prototype/src/utils/constants.py
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
                // Alias explicites utilisés dans les composants (bg-game-bg, bg-game-surface…)
                "game-bg": "#19192B",
                "game-surface": "#232340",
                "game-panel": "#28283C",
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

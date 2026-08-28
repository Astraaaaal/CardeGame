import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import path from "path";

export default defineConfig({
    plugins: [
        react(),
        VitePWA({
            registerType: "autoUpdate",
            includeAssets: ["favicon.ico", "icons/*.png"],
            manifest: {
                name: "CardeGame",
                short_name: "CardeGame",
                description: "Jeu de collection de cartes en ligne",
                start_url: "/",
                display: "standalone",
                orientation: "portrait",
                background_color: "#19192B",
                theme_color: "#50A0FF",
                icons: [
                    { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
                    { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
                ],
            },
            workbox: {
                globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
                runtimeCaching: [
                    {
                        // Cache-first pour les images Cloudinary (elles ne changent pas)
                        urlPattern: /^https:\/\/res\.cloudinary\.com\/.*/i,
                        handler: "CacheFirst",
                        options: {
                            cacheName: "card-images",
                            expiration: { maxEntries: 500, maxAgeSeconds: 60 * 60 * 24 * 30 },
                        },
                    },
                    {
                        // Stale-while-revalidate pour les données API
                        urlPattern: /^https:\/\/.*\/api\/(boosters|collection).*/i,
                        handler: "StaleWhileRevalidate",
                        options: {
                            cacheName: "api-data",
                            expiration: { maxEntries: 50, maxAgeSeconds: 60 * 5 },
                        },
                    },
                ],
            },
        }),
    ],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        port: 5173,
        proxy: {
            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true,
            },
        },
    },
});

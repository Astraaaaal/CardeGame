/**
 * Client API — Axios wrapper avec interceptors JWT.
 * Gère automatiquement l'ajout du Bearer token et le refresh.
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

export const API_URL = import.meta.env.VITE_API_URL || "";

const api = axios.create({
    baseURL: `${API_URL}/api`,
    headers: { "Content-Type": "application/json" },
});

// ── Request interceptor : ajoute le JWT ──
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem("access_token");
    if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    // Clé admin saisie dans le panneau admin (cet onglet) : permet de jouer
    // même quand le jeu est fermé (cf. backend services/game_status.py).
    const adminKey = sessionStorage.getItem("admin_key");
    if (adminKey && config.headers) config.headers["X-Admin-Key"] = adminKey;
    return config;
});

// ── Response interceptor : auto-refresh si 401 ──
const PUBLIC_PATHS = ["/login", "/legal", "/verify-email"];

let isRefreshing = false;
let failedQueue: Array<{
    resolve: (value: unknown) => void;
    reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: unknown) => {
    failedQueue.forEach((prom) => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(undefined);
        }
    });
    failedQueue = [];
};

api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & {
            _retry?: boolean;
        };

        // Un 401 sur une route d'authentification est une vraie réponse (mauvais
        // mot de passe, code invalide...) : on la laisse remonter au formulaire
        // au lieu de rediriger (ce qui rechargeait la page et effaçait le message).
        const isAuthRoute = /\/api\/auth\//.test(originalRequest?.url ?? "") || /^\/auth\//.test(originalRequest?.url ?? "");

        // Jeu fermé : on déconnecte et on renvoie vers la page de connexion,
        // qui affiche le message (sauf sur les routes d'auth, où le formulaire l'affiche).
        const detail = (error.response?.data as { detail?: { code?: string } } | undefined)?.detail;
        if (error.response?.status === 503 && detail?.code === "game_closed" && !isAuthRoute) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            localStorage.removeItem("auth-storage");
            if (!PUBLIC_PATHS.includes(window.location.pathname)) window.location.href = "/login";
            return Promise.reject(error);
        }

        if (error.response?.status === 401 && !originalRequest._retry && !isAuthRoute) {
            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                }).then(() => api(originalRequest));
            }

            originalRequest._retry = true;
            isRefreshing = true;

            const refreshToken = localStorage.getItem("refresh_token");
            if (!refreshToken) {
                isRefreshing = false;
                localStorage.clear();
                // Déjà sur une page publique : pas de rechargement (évite une boucle).
                if (!PUBLIC_PATHS.includes(window.location.pathname)) window.location.href = "/login";
                return Promise.reject(error);
            }

            try {
                const { data } = await axios.post(`${API_URL}/api/auth/refresh`, {
                    refresh_token: refreshToken,
                });

                localStorage.setItem("access_token", data.access_token);
                localStorage.setItem("refresh_token", data.refresh_token);

                if (originalRequest.headers) {
                    originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
                }

                processQueue(null);
                return api(originalRequest);
            } catch (refreshError) {
                processQueue(refreshError);
                localStorage.clear();
                window.location.href = "/login";
                return Promise.reject(refreshError);
            } finally {
                isRefreshing = false;
            }
        }

        return Promise.reject(error);
    }
);

export default api;

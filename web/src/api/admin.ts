/**
 * Client de l'API d'édition de contenu (panneau admin).
 * Auth par en-tête X-Admin-Key (indépendante du JWT joueur). La clé est
 * conservée en sessionStorage.
 */

import axios from "axios";
import type {
    GameSet,
    AdminBooster,
    AdminCharacter,
    Tuning,
} from "@/types/content";

const API_URL = import.meta.env.VITE_API_URL || "";
const KEY_STORE = "admin_key";

export const adminKey = {
    get: () => sessionStorage.getItem(KEY_STORE) || "",
    set: (k: string) => sessionStorage.setItem(KEY_STORE, k),
    clear: () => sessionStorage.removeItem(KEY_STORE),
};

const http = axios.create({ baseURL: `${API_URL}/api/admin/content` });
http.interceptors.request.use((config) => {
    config.headers.set("X-Admin-Key", adminKey.get());
    return config;
});

export const adminApi = {
    // renvoie true si la clé est acceptée
    check: async (key: string): Promise<boolean> => {
        try {
            await axios.get(`${API_URL}/api/admin/content/sets`, {
                headers: { "X-Admin-Key": key },
            });
            return true;
        } catch {
            return false;
        }
    },

    tuning: () => http.get<Tuning>("/tuning").then((r) => r.data),

    // ── Sets ──
    listSets: () => http.get<GameSet[]>("/sets").then((r) => r.data),
    createSet: (b: Pick<GameSet, "id" | "name" | "description">) =>
        http.post<GameSet>("/sets", b).then((r) => r.data),
    updateSet: (id: string, b: Partial<Pick<GameSet, "name" | "description">>) =>
        http.patch<GameSet>(`/sets/${id}`, b).then((r) => r.data),
    deleteSet: (id: string) => http.delete(`/sets/${id}`).then(() => undefined),

    // ── Boosters ──
    listBoosters: () => http.get<AdminBooster[]>("/boosters").then((r) => r.data),
    createBooster: (b: AdminBooster) =>
        http.post<AdminBooster>("/boosters", b).then((r) => r.data),
    updateBooster: (id: string, b: Partial<AdminBooster>) =>
        http.patch<AdminBooster>(`/boosters/${id}`, b).then((r) => r.data),
    deleteBooster: (id: string) =>
        http.delete(`/boosters/${id}`).then(() => undefined),

    // ── Personnages ──
    listCharacters: () =>
        http.get<AdminCharacter[]>("/characters").then((r) => r.data),
    createCharacter: (b: AdminCharacter) =>
        http.post<AdminCharacter>("/characters", b).then((r) => r.data),
    updateCharacter: (id: string, b: Partial<AdminCharacter>) =>
        http.patch<AdminCharacter>(`/characters/${id}`, b).then((r) => r.data),
    deleteCharacter: (id: string) =>
        http.delete(`/characters/${id}`).then(() => undefined),
};

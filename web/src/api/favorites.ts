import api from "./client";

export interface FavoriteCategory {
    id: number;
    name: string;
    color: string;
    count: number;
}

export const FAVORITE_COLORS = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899", "#ffffff", "#78716c"];

export const favoritesApi = {
    list: () => api.get<FavoriteCategory[]>("/favorites").then((r) => r.data),
    create: (name: string, color: string) => api.post<FavoriteCategory[]>("/favorites", { name, color }).then((r) => r.data),
    update: (id: number, name: string, color: string) =>
        api.patch<FavoriteCategory[]>(`/favorites/${id}`, { name, color }).then((r) => r.data),
    remove: (id: number) => api.delete<FavoriteCategory[]>(`/favorites/${id}`).then((r) => r.data),
    addCards: (id: number, cardIds: string[]) =>
        api.post<FavoriteCategory[]>(`/favorites/${id}/cards`, { card_ids: cardIds }).then((r) => r.data),
    removeCards: (id: number, cardIds: string[]) =>
        api.post<FavoriteCategory[]>(`/favorites/${id}/cards/remove`, { card_ids: cardIds }).then((r) => r.data),
    lock: (cardIds: string[], locked: boolean) => api.post("/favorites/lock", { card_ids: cardIds, locked }).then((r) => r.data),
};

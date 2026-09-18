import api from "./client";

export interface PresenceStatus {
    multiplier: number;
    max_multiplier: number;
    full_after_hours: number;
    present_seconds: number;
    chest: { coins: number; dust: number; hours: number; cap_hours: number };
}

export const activitiesApi = {
    presence: () => api.get<PresenceStatus>("/activities/presence").then((r) => r.data),
    ping: () => api.post<PresenceStatus>("/activities/presence/ping").then((r) => r.data),
    claimChest: () =>
        api.post<{ coins: number; dust: number; hours: number }>("/activities/presence/chest").then((r) => r.data),
};

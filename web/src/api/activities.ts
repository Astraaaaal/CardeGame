import api from "./client";
import type { Card } from "@/types/card";

export interface PresenceStatus {
    multiplier: number;
    max_multiplier: number;
    full_after_hours: number;
    present_seconds: number;
    chest: { coins: number; dust: number; hours: number; cap_hours: number };
}

export interface ExpeditionEstimate {
    coins: number;
    dust: number;
    booster_chance: number;
    rare_card_chance: number;
    power_factor: number;
}

export interface ExpeditionOut {
    id: number;
    slot: number;
    duration_minutes: number;
    ends_at: string;
    remaining_seconds: number;
    done: boolean;
    total_power: number;
    cards: Card[];
    estimate: ExpeditionEstimate;
}

export interface ExpeditionsOverview {
    slots: { slot: number; expedition: ExpeditionOut | null }[];
    durations: number[];
    max_cards: number;
    locked_card_ids: string[];
}

export interface ExpeditionReward {
    coins: number;
    dust: number;
    booster_id: string | null;
    booster_name: string | null;
    card: Card | null;
}

export interface WorkshopState {
    taps: number;
    taps_per_gauge: number;
    gauges_today: number;
    gauges_per_day: number;
    fragments: number;
    fragments_per_booster: number;
    coins_per_gauge: number;
    accepted?: number;
    reward: { coins: number; dust: number; gauges: number; boosters: number };
    booster_id?: string | null;
    booster_name?: string | null;
}

export const activitiesApi = {
    presence: () => api.get<PresenceStatus>("/activities/presence").then((r) => r.data),
    ping: () => api.post<PresenceStatus>("/activities/presence/ping").then((r) => r.data),
    expeditions: () => api.get<ExpeditionsOverview>("/activities/expeditions").then((r) => r.data),
    startExpedition: (slot: number, durationMinutes: number, cardIds: string[]) =>
        api.post<ExpeditionOut>("/activities/expeditions", {
            slot, duration_minutes: durationMinutes, card_ids: cardIds,
        }).then((r) => r.data),
    claimExpedition: (id: number) =>
        api.post<ExpeditionReward>(`/activities/expeditions/${id}/claim`).then((r) => r.data),
    workshop: () => api.get<WorkshopState>("/activities/workshop")
        .then((r) => ({ ...r.data, reward: { coins: 0, dust: 0, gauges: 0, boosters: 0 } })),
    workshopTaps: (count: number) =>
        api.post<WorkshopState>("/activities/workshop/taps", { count }).then((r) => r.data),
    claimChest: () =>
        api.post<{ coins: number; dust: number; hours: number }>("/activities/presence/chest").then((r) => r.data),
};

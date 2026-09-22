import api from "./client";
import type { Card } from "@/types/card";

export interface PresenceStatus {
    /** false tant que la chance de présence n'est pas débloquée (niveau). */
    unlocked?: boolean;
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

export interface HigherLowerGameState {
    id: number;
    status: "active" | "cashed" | "lost";
    resource_id: string;
    stake: number;
    step: number;
    max_steps: number;
    min_cashout_step: number;
    total_multiplier: number;
    current_card: Card;
    cashout_value: number;
    can_cashout: boolean;
    /** Gain d'une bonne réponse (null = réponse impossible). */
    odds: { higher?: number | null; lower?: number | null };
    outcome?: "win" | "tie" | "lose";
    won_multiplier?: number | null;
    previous_card?: Card;
}

export interface HigherLowerState {
    game: HigherLowerGameState | null;
    min_stake: number;
    max_stake: number;
    max_steps: number;
    min_cashout_step: number;
}

export interface WheelState {
    free_available: boolean;
    extra_spins_used: number;
    extra_spins_per_day: number;
    extra_spin_cost: number;
    segments: { label: string; kind: "resource" | "booster" | "reroll" }[];
}

export interface WheelSpin {
    index: number;
    reward: {
        kind: "resource" | "booster" | "reroll";
        label: string;
        amount: number;
        resource_id: string | null;
        booster_id: string | null;
        booster_name: string | null;
    };
    state: WheelState;
}

export interface MachineResourceNeed {
    resource_id: string;
    name: string;
    amount: number;
}

export interface MachineUpgrade {
    kind: string;
    label: string;
    next: string;
    level: number;
    cost: number;
    chance: number;
    /** Ressource obligatoire à ce cran (null avant le cran de départ). */
    required: MachineResourceNeed | null;
    /** Ressources qu'on peut ajouter pour augmenter la réussite (par unité). */
    bonus_options: { resource_id: string; name: string; per_unit: number }[];
    /** Réussite maximale atteignable en ajoutant des ressources, à ce cran. */
    cap: number;
}

export interface MachineItem {
    item: "booster" | "reroll";
    booster_id?: string;
    bonus_id?: number | null;
    token_id?: number;
    name: string;
    detail: string;
    quantity: number;
    upgrades: MachineUpgrade[];
}

export interface MachineState {
    day: number;
    length: number;
    today: { kind: string; label: string }[];
    event: { id: string; label: string } | null;
    cycle_upgrades: string[];
    cycle_events: string[];
    items: MachineItem[];
}

export interface MachineResult {
    success: boolean;
    destroyed: boolean;
    cost: number;
    chance: number;
    result: string | null;
    spent: Record<string, number>;
    state: MachineState;
}

export interface ConverterState {
    daily_uses: number;
    uses_left: number;
    pairs: { from: string; to: string; give: number; get: number; max_in: number }[];
}

export const activitiesApi = {
    machine: () => api.get<MachineState>("/activities/machine").then((r) => r.data),
    upgrade: (item: MachineItem, kind: string, extra: Record<string, number> = {}) =>
        api.post<MachineResult>("/activities/machine/upgrade", {
            item: item.item, kind, booster_id: item.booster_id, bonus_id: item.bonus_id ?? null, token_id: item.token_id, extra,
        }).then((r) => r.data),
    converter: () => api.get<ConverterState>("/activities/converter").then((r) => r.data),
    convert: (fromId: string, toId: string, amount: number) =>
        api.post<{ spent: number; gained: number; state: ConverterState }>("/activities/converter", {
            from_id: fromId, to_id: toId, amount,
        }).then((r) => r.data),
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
    higherLower: () => api.get<HigherLowerState>("/activities/higher-lower").then((r) => r.data),
    startHigherLower: (resourceId: string, stake: number) =>
        api.post<HigherLowerGameState>("/activities/higher-lower", { resource_id: resourceId, stake }).then((r) => r.data),
    guessHigherLower: (id: number, guess: "higher" | "lower") =>
        api.post<HigherLowerGameState>(`/activities/higher-lower/${id}/guess`, { guess }).then((r) => r.data),
    cashoutHigherLower: (id: number) =>
        api.post<HigherLowerGameState>(`/activities/higher-lower/${id}/cashout`).then((r) => r.data),
    wheel: () => api.get<WheelState>("/activities/wheel").then((r) => r.data),
    spinWheel: () => api.post<WheelSpin>("/activities/wheel/spin").then((r) => r.data),
    claimChest: () =>
        api.post<{ coins: number; dust: number; hours: number }>("/activities/presence/chest").then((r) => r.data),
};

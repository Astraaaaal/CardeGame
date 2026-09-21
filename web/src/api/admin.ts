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
    AdminType,
    AdminResource,
    AdminShopOffer,
    DailyFeature,
    Tuning,
    TuningEntry,
    TuningTable,
} from "@/types/content";
import type { Cosmetic, Grant, PremiumConfig, PremiumOrder, PremiumProduct } from "@/types/premium";

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
    updateTuning: (table: TuningTable, id: string, b: Partial<Pick<TuningEntry, "weight" | "recycle_value">>) =>
        http.patch<TuningEntry>(`/tuning/${table}/${id}`, b).then((r) => r.data),

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

    // ── Types ──
    listTypes: () => http.get<AdminType[]>("/types").then((r) => r.data),
    createType: (b: { id: string; name: string; color_r: number; color_g: number; color_b: number }) =>
        http.post<AdminType>("/types", b).then((r) => r.data),
    updateType: (id: string, b: Partial<{ name: string; color_r: number; color_g: number; color_b: number }>) =>
        http.patch<AdminType>(`/types/${id}`, b).then((r) => r.data),
    deleteType: (id: string) => http.delete(`/types/${id}`).then(() => undefined),

    // ── Ressources ──
    listResources: () => http.get<AdminResource[]>("/resources").then((r) => r.data),
    createResource: (b: AdminResource) =>
        http.post<AdminResource>("/resources", b).then((r) => r.data),
    updateResource: (id: string, b: Partial<Pick<AdminResource, "name" | "description" | "starting_amount">>) =>
        http.patch<AdminResource>(`/resources/${id}`, b).then((r) => r.data),
    deleteResource: (id: string) => http.delete(`/resources/${id}`).then(() => undefined),

    // ── Offres du shop ──
    listShopOffers: () => http.get<AdminShopOffer[]>("/shop-offers").then((r) => r.data),
    createShopOffer: (b: Partial<AdminShopOffer>) =>
        http.post<AdminShopOffer>("/shop-offers", b).then((r) => r.data),
    updateShopOffer: (id: string, b: Partial<AdminShopOffer>) =>
        http.patch<AdminShopOffer>(`/shop-offers/${id}`, b).then((r) => r.data),
    setShopOfferActive: (id: string, active: boolean) =>
        http.patch<AdminShopOffer>(`/shop-offers/${id}`, { active }).then((r) => r.data),
    deleteShopOffer: (id: string) => http.delete(`/shop-offers/${id}`).then(() => undefined),

    // ── Booster du jour ──
    getDailyFeature: () => http.get<DailyFeature | null>("/daily-feature").then((r) => r.data),
    setDailyFeature: (offerId: string) =>
        http.post<DailyFeature>("/daily-feature", { offer_id: offerId }).then((r) => r.data),
    clearDailyFeature: (isoDate: string) =>
        http.delete(`/daily-feature/${isoDate}`).then(() => undefined),

    // ── Progression (niveaux / achievements / quêtes) ──
    listLevelTiers: () => http.get<AdminLevelTier[]>("/level-tiers").then((r) => r.data),
    updateLevelTier: (level: number, b: Partial<Omit<AdminLevelTier, "level">>) =>
        http.patch<AdminLevelTier>(`/level-tiers/${level}`, b).then((r) => r.data),
    listAchievementDefs: () => http.get<AdminAchievementDef[]>("/achievements").then((r) => r.data),
    updateAchievementDef: (id: string, b: Partial<Pick<AdminAchievementDef, "threshold" | "reward_resource_id" | "reward_amount" | "reward_booster_id" | "active">>) =>
        http.patch<AdminAchievementDef>(`/achievements/${id}`, b).then((r) => r.data),
    listQuestDefs: () => http.get<AdminQuestDef[]>("/quest-defs").then((r) => r.data),
    updateQuestDef: (id: string, b: Partial<Pick<AdminQuestDef, "threshold" | "reward_resource_id" | "reward_amount" | "reward_booster_id" | "active">>) =>
        http.patch<AdminQuestDef>(`/quest-defs/${id}`, b).then((r) => r.data),

    // ── Réglages globaux du jeu ──
    getGameConfig: () => http.get<GameConfig>("/game-config").then((r) => r.data),
    updateGameConfig: (b: Partial<GameConfig>) => http.patch<GameConfig>("/game-config", b).then((r) => r.data),
};

export interface GameConfig {
    daily_base_reward: number;
    daily_streak_bonus: number;
}

export interface AdminLevelTier {
    level: number;
    power_required: number;
    reward_resource_id: string | null;
    reward_amount: number | null;
    reward_booster_id: string | null;
}

export interface AdminAchievementDef {
    id: string;
    name: string;
    description: string;
    category: string;
    metric: string;
    threshold: number;
    metric_param: string | null;
    reward_resource_id: string | null;
    reward_amount: number | null;
    reward_booster_id: string | null;
    active: boolean;
}

export interface AdminQuestDef {
    id: string;
    name: string;
    description: string;
    period: string;
    metric: string;
    threshold: number;
    reward_resource_id: string | null;
    reward_amount: number | null;
    reward_booster_id: string | null;
    active: boolean;
}

// Réglages des activités (présence, coffre, expéditions, atelier, mini-jeux).
const httpActivities = axios.create({ baseURL: `${API_URL}/api/admin/activities` });
httpActivities.interceptors.request.use((config) => {
    config.headers.set("X-Admin-Key", adminKey.get());
    return config;
});

export interface ActivitiesConfig {
    reward_booster_id: string;
    presence: { max_multiplier: number; full_after_hours: number; reset_after_minutes: number };
    chest: { coins_per_hour: number; dust_per_hour: number; cap_hours: number };
    expeditions: {
        slots: number; max_cards: number; durations: number[]; coins_per_minute: number; dust_ratio: number;
        power_scale: number; max_power_factor: number;
        booster_chance: Record<string, number>; rare_card_chance: Record<string, number>;
    };
    workshop: {
        taps_per_gauge: number; max_taps_per_second: number; coins_per_gauge: number; dust_chance: number;
        dust_amount: number; fragments_per_booster: number; gauges_per_day: number;
    };
    higher_lower: {
        min_stake: number; max_stake: number; max_steps: number;
        house_edge: number; min_cashout_step: number; max_step_multiplier: number;
    };
    machine: {
        rotation: Record<string, string[]>;
        events: { id: string; label: string; chance: number; cost_factor: number; success_bonus: number; lose_on_fail: boolean }[];
        base_cost: number; level_cost_factor: number; failure_cost_factor: number;
        base_chance: number; level_chance_factor: number; failure_chance_step: number; max_chance: number;
    };
    converter: {
        daily_uses: number;
        pairs: { from: string; to: string; give: number; get: number; max_in: number }[];
    };
    wheel: {
        extra_spin_cost: number; extra_spins_per_day: number;
        segments: { label: string; kind: "resource" | "booster" | "reroll"; id: string; amount: number; weight: number }[];
    };
}

export const adminActivitiesApi = {
    get: () => httpActivities.get<ActivitiesConfig>("/config").then((r) => r.data),
    save: (b: ActivitiesConfig) => httpActivities.put<ActivitiesConfig>("/config", b).then((r) => r.data),
};

// Route sœur de /api/admin/content, hors de son préfixe — client dédié.
const httpMessages = axios.create({ baseURL: `${API_URL}/api/admin/messages` });
httpMessages.interceptors.request.use((config) => {
    config.headers.set("X-Admin-Key", adminKey.get());
    return config;
});

export interface SendAdminMessageBody {
    usernames?: string[] | null;
    subject: string;
    body?: string;
    reward_resource_id?: string | null;
    reward_amount?: number | null;
    rewards?: AdminMessageReward[];
}

/** Récompense d'un message admin (cf. backend app/services/message_rewards.py). */
export type AdminMessageReward =
    | { kind: "resource"; id: string; amount: number }
    | { kind: "booster"; id: string; quantity: number; force_min_rarity_id?: string | null; rarity_weight_multiplier?: number | null; label?: string }
    | {
        kind: "reroll"; label: string; quantity: number;
        rules: {
            reroll_rarity: boolean; reroll_quality: boolean; reroll_specialty: boolean;
            reroll_jewelry: boolean; reroll_power: boolean; reroll_mode: "random" | "guaranteed_min";
        };
    }
    | {
        kind: "card"; character_id: string; rarity_id: string; quality_id: string;
        specialty_id: string; jewelry_id: string; power_mode: "rolled" | "fixed"; power?: number | null;
    };

export const adminMessagesApi = {
    send: (b: SendAdminMessageBody) =>
        httpMessages.post<{ sent_count: number }>("/", b).then((r) => r.data),
};

// Route sœur de /api/admin/content, hors de son préfixe — client dédié.
const httpBugReports = axios.create({ baseURL: `${API_URL}/api/admin/bug-reports` });
httpBugReports.interceptors.request.use((config) => {
    config.headers.set("X-Admin-Key", adminKey.get());
    return config;
});

export interface AdminBugReport {
    id: number;
    username: string;
    subject: string;
    body: string;
    page_context: string | null;
    created_at: string;
    resolved_at: string | null;
}

export const adminBugReportsApi = {
    list: () => httpBugReports.get<AdminBugReport[]>("/").then((r) => r.data),
    resolve: (id: number) => httpBugReports.post<AdminBugReport>(`/${id}/resolve`).then((r) => r.data),
    remove: (id: number) => httpBugReports.delete(`/${id}`).then(() => undefined),
};

// Boutique premium — route sœur de /api/admin/content.
const httpPremium = axios.create({ baseURL: `${API_URL}/api/admin/premium` });
httpPremium.interceptors.request.use((config) => {
    config.headers.set("X-Admin-Key", adminKey.get());
    return config;
});

export const adminPremiumApi = {
    getConfig: () => httpPremium.get<PremiumConfig>("/config").then((r) => r.data),
    updateConfig: (b: Partial<Pick<PremiumConfig, "premium_shop_enabled" | "premium_testers">>) =>
        httpPremium.patch<PremiumConfig>("/config", b).then((r) => r.data),

    listCosmetics: () => httpPremium.get<Cosmetic[]>("/cosmetics").then((r) => r.data),
    createCosmetic: (b: Omit<Cosmetic, "active"> & { active?: boolean }) =>
        httpPremium.post<Cosmetic>("/cosmetics", b).then((r) => r.data),
    updateCosmetic: (id: string, b: Partial<Omit<Cosmetic, "id" | "kind">>) =>
        httpPremium.patch<Cosmetic>(`/cosmetics/${id}`, b).then((r) => r.data),
    deleteCosmetic: (id: string) => httpPremium.delete(`/cosmetics/${id}`).then(() => undefined),

    listProducts: () => httpPremium.get<PremiumProduct[]>("/products").then((r) => r.data),
    createProduct: (b: PremiumProductInput) => httpPremium.post<PremiumProduct>("/products", b).then((r) => r.data),
    updateProduct: (id: string, b: Partial<Omit<PremiumProductInput, "id">>) =>
        httpPremium.patch<PremiumProduct>(`/products/${id}`, b).then((r) => r.data),
    deleteProduct: (id: string) => httpPremium.delete(`/products/${id}`).then(() => undefined),

    listOrders: () => httpPremium.get<PremiumOrder[]>("/orders").then((r) => r.data),
};

export interface PremiumProductInput {
    id: string;
    name: string;
    description: string;
    price_cents: number;
    grants: Grant[];
    once_per_account: boolean;
    limit_period: "none" | "day" | "week" | "month" | "account";
    limit_count: number;
    active: boolean;
    sort_order: number;
}

// Jeu fermé / remise à zéro des comptes (routes /api/admin/*).
const httpRoot = axios.create({ baseURL: `${API_URL}/api/admin` });
httpRoot.interceptors.request.use((config) => {
    config.headers.set("X-Admin-Key", adminKey.get());
    return config;
});

export interface GameStatusAdmin {
    closed: boolean;
    message: string;
    default_message: string;
}

export const adminMaintenanceApi = {
    getStatus: () => httpRoot.get<GameStatusAdmin>("/game-status").then((r) => r.data),
    setStatus: (b: { closed: boolean; message: string }) => httpRoot.put<GameStatusAdmin>("/game-status", b).then((r) => r.data),
    resetAccounts: (confirm: string) =>
        httpRoot.post<{ users: number; cards_removed: number }>("/reset-accounts", { confirm }).then((r) => r.data),
};

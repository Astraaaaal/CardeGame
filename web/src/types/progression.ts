export interface PendingLevelReward {
    level: number;
    reward_resource_id: string | null;
    reward_amount: number | null;
    reward_booster_id: string | null;
    reward_booster_name: string | null;
    /** Niveau de prestige (0 = route normale) et son bonus. */
    prestige: number;
    bonus_resource_id: string | null;
    bonus_amount: number | null;
}

export interface LevelStatus {
    current_level: number;
    prestige: number;
    total_power: number;
    claimed_level: number;
    /** Seuil du niveau atteint : la barre se remplit ENTRE les deux seuils,
     * sinon elle mesure le chemin depuis zéro et reste presque pleine. */
    current_level_power_required: number;
    next_level_power_required: number | null;
    pending_rewards: PendingLevelReward[];
    has_unclaimed: boolean;
}

export interface LevelTierOverview {
    level: number;
    power_required: number;
    reward_resource_id: string | null;
    reward_resource_name: string | null;
    reward_amount: number | null;
    reward_booster_id: string | null;
    reward_booster_name: string | null;
    prestige: number;
    bonus_resource_id: string | null;
    bonus_resource_name: string | null;
    bonus_amount: number | null;
    reached: boolean;
    claimed: boolean;
}

export type AchievementCategory = "collection" | "social" | "economy" | "progression" | "meta";

export interface Achievement {
    id: string;
    name: string;
    description: string;
    category: AchievementCategory;
    threshold: number;
    progress: number;
    reward_resource_id: string | null;
    reward_amount: number | null;
    reward_booster_id: string | null;
    unlocked_at: string | null;
    claimed_at: string | null;
}

export type QuestPeriod = "daily" | "weekly";

export interface Quest {
    id: number;
    quest_def_id: string;
    name: string;
    description: string;
    period: QuestPeriod;
    threshold: number;
    progress: number;
    reward_resource_id: string | null;
    reward_amount: number | null;
    reward_booster_id: string | null;
    completed: boolean;
    claimed_at: string | null;
}

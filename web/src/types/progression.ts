export interface PendingLevelReward {
    level: number;
    reward_resource_id: string | null;
    reward_amount: number | null;
}

export interface LevelStatus {
    current_level: number;
    total_power: number;
    claimed_level: number;
    next_level_power_required: number | null;
    pending_rewards: PendingLevelReward[];
    has_unclaimed: boolean;
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
    completed: boolean;
    claimed_at: string | null;
}

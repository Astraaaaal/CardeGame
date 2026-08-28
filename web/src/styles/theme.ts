/**
 * Theme constants — miroir de backend constants.
 */

export const COLORS = {
    bg: "#19192B",
    surface: "#252540",
    accent: "#50A0FF",
    gold: "#FFC832",
    text: "#FFFFFF",
    textMuted: "rgba(255,255,255,0.5)",
} as const;

export const RARITY_COLORS: Record<string, string> = {
    common: "rgb(200,200,200)",
    rare: "rgb(80,160,255)",
    epic: "rgb(180,80,255)",
    legendary: "rgb(255,200,50)",
};

export const DAILY_BASE_REWARD = 500;
export const DAILY_STREAK_BONUS = 100;

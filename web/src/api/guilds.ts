import api from "./client";

export type GuildRole = "leader" | "officer" | "member";
export type JoinPolicy = "open" | "request" | "invite";

export interface GuildSummary {
    id: number;
    name: string;
    tag: string;
    icon: string;
    color: string;
    join_policy: JoinPolicy;
    level: number;
    members: number;
    max_members: number;
    power: number;
    chest_total: number;
    challenge_best_tier: number;
}

export interface GuildObjective {
    metric: string;
    label: string;
    target: number;
    progress: number;
    completed_at: string | null;
    my_contribution: number;
    claimable: boolean;
    claimed: boolean;
    reward_coins: number;
    reward_dust: number;
}

export interface GuildMemberRow {
    user_id: number;
    username: string;
    display_name: string;
    role: GuildRole;
    joined_at: string;
    donated_points: number;
}

export interface GuildDetail extends GuildSummary {
    my_role: GuildRole;
    welcome_message: string;
    xp: number;
    xp_current_level: number;
    xp_next_level: number;
    chest_points: number;
    challenge_tier: number;
    week_key: string;
    objectives: GuildObjective[];
    members_list: GuildMemberRow[];
    requests: { id: number; user_id: number; display_name: string; username: string }[];
    buffs: { kind: string; label: string; expires_at: string }[];
    shop: { kind: string; label: string; cost: number; hours: number }[];
    perks: { daily_bonus_pct: number; extra_expedition_slots: number; expedition_slot_level: number };
    points_per_coins: number;
    points_per_dust: number;
}

export interface MyGuildState {
    guild: GuildDetail | null;
    invites: { id: number; guild: GuildSummary }[];
    left_at: string | null;
    cooldown_hours: number;
    creation_cost: number;
}

export interface WallMessage {
    id: number;
    user_id: number | null;
    author: string | null;
    body: string;
    created_at: string;
    system: boolean;
}

export type RankingKind = "overall" | "level" | "power" | "chest" | "challenge";
export interface GuildRankingRow extends GuildSummary {
    rank: number;
    xp: number;
    average_rank: number;
}

export const guildsApi = {
    me: () => api.get<MyGuildState>("/guilds/me").then((r) => r.data),
    search: (q: string) => api.get<GuildSummary[]>("/guilds/search", { params: { q } }).then((r) => r.data),
    rankings: (kind: RankingKind) => api.get<GuildRankingRow[]>("/guilds/rankings", { params: { kind } }).then((r) => r.data),
    create: (b: { name: string; tag: string; icon: string; color: string; join_policy: JoinPolicy }) =>
        api.post<GuildSummary>("/guilds", b).then((r) => r.data),
    join: (id: number) => api.post<{ result: "joined" | "requested" }>(`/guilds/${id}/join`).then((r) => r.data),
    leave: () => api.post("/guilds/leave").then((r) => r.data),
    settings: (b: Partial<{ welcome_message: string; join_policy: JoinPolicy; icon: string; color: string }>) =>
        api.patch<GuildDetail>("/guilds/settings", b).then((r) => r.data),
    invite: (username: string) => api.post("/guilds/invites", { username }).then((r) => r.data),
    answerInvite: (id: number, accept: boolean) => api.post(`/guilds/invites/${id}/answer`, { accept }).then((r) => r.data),
    answerRequest: (id: number, accept: boolean) =>
        api.post<GuildDetail>(`/guilds/requests/${id}/answer`, { accept }).then((r) => r.data),
    setRole: (userId: number, role: GuildRole) =>
        api.post<GuildDetail>(`/guilds/members/${userId}/role`, { role }).then((r) => r.data),
    kick: (userId: number) => api.post<GuildDetail>(`/guilds/members/${userId}/kick`).then((r) => r.data),
    claimObjective: (metric: string) =>
        api.post<{ coins: number; dust: number }>(`/guilds/objectives/${metric}/claim`).then((r) => r.data),
    donate: (resourceId: string, amount: number) =>
        api.post<{ points: number; spent: number }>("/guilds/donate", { resource_id: resourceId, amount }).then((r) => r.data),
    buyBuff: (kind: string) => api.post<GuildDetail>(`/guilds/buffs/${kind}`).then((r) => r.data),
    wall: () => api.get<WallMessage[]>("/guilds/wall").then((r) => r.data),
    post: (body: string) => api.post<WallMessage[]>("/guilds/wall", { body }).then((r) => r.data),
};

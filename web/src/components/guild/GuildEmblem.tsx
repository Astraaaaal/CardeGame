/** Emblème de guilde : icône sur un disque de sa couleur. */
export default function GuildEmblem({ icon, color, size = 40 }: { icon: string; color: string; size?: number }) {
    return (
        <span
            className="inline-flex items-center justify-center rounded-full shrink-0 border-2 border-white/20"
            style={{ width: size, height: size, background: color, fontSize: size * 0.5 }}
        >
            {icon}
        </span>
    );
}

export const GUILD_ICONS = ["🛡️", "🐉", "🦅", "🐺", "🦁", "🔥", "⚡", "🌙", "⭐", "💎", "🗡️", "👑"];
export const GUILD_COLORS = ["#6366f1", "#0ea5e9", "#10b981", "#eab308", "#f97316", "#ef4444", "#ec4899", "#8b5cf6"];

export const POLICY_LABEL = {
    open: "Ouverte à tous",
    request: "Sur demande",
    invite: "Sur invitation",
} as const;

export const ROLE_LABEL = { leader: "Chef", officer: "Officier", member: "Membre" } as const;

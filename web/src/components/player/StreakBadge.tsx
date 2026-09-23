import StreakFlame, { tierOf } from "./StreakFlame";

interface StreakBadgeProps {
    streak: number;
    /** Taille compacte pour les en-têtes ; par défaut, taille du menu. */
    size?: "sm" | "md";
}

/** Série de connexion : flamme + nombre de jours, la flamme chauffant avec la série. */
export default function StreakBadge({ streak, size = "md" }: StreakBadgeProps) {
    if (streak <= 0) return null;
    const tier = tierOf(streak);
    const small = size === "sm";

    return (
        <div
            className={`inline-flex items-center gap-1 rounded-full border ${small ? "px-2 py-0.5" : "px-2.5 py-1"}`}
            style={{ borderColor: `${tier.bottom}55`, background: `${tier.bottom}1f` }}
            title={`${streak} jour${streak > 1 ? "s" : ""} de connexion d'affilée`}
        >
            <StreakFlame streak={streak} size={small ? 14 : 18} />
            <span className={`font-bold tabular-nums ${small ? "text-xs" : "text-sm"}`} style={{ color: tier.top }}>
                {streak}
                <span className="opacity-60"> j</span>
            </span>
        </div>
    );
}

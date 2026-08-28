interface StreakBadgeProps {
    streak: number;
}

export default function StreakBadge({ streak }: StreakBadgeProps) {
    if (streak <= 0) return null;

    return (
        <div className="flex items-center gap-1 bg-orange-600/20 rounded-full px-3 py-1">
            <span className="text-base">🔥</span>
            <span className="text-orange-400 font-bold text-sm">{streak}j</span>
        </div>
    );
}

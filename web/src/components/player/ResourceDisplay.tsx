interface ResourceDisplayProps {
    amount: number;
    label?: string;
    className?: string;
}

/** Affiche une ressource secondaire (ex: poussière), même style que CoinDisplay. */
export default function ResourceDisplay({ amount, label = "Poussière", className = "" }: ResourceDisplayProps) {
    return (
        <div
            className={`flex items-center gap-1.5 bg-black/30 rounded-full px-3 py-1.5 ${className}`}
            title={label}
        >
            <span className="text-purple-300 text-lg">✨</span>
            <span className="text-purple-300 font-bold tabular-nums">
                {amount.toLocaleString("fr-FR")}
            </span>
        </div>
    );
}

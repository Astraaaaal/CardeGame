interface CoinDisplayProps {
    coins: number;
    className?: string;
}

export default function CoinDisplay({ coins, className = "" }: CoinDisplayProps) {
    return (
        <div
            className={`flex items-center gap-1.5 bg-black/30 rounded-full px-3 py-1.5 ${className}`}
        >
            <span className="text-gold text-lg">🪙</span>
            <span className="text-gold font-bold tabular-nums">
                {coins.toLocaleString("fr-FR")}
            </span>
        </div>
    );
}

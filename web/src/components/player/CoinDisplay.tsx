import CoinIcon from "@/components/ui/CoinIcon";

interface CoinDisplayProps {
    coins: number;
    className?: string;
}

export default function CoinDisplay({ coins, className = "" }: CoinDisplayProps) {
    return (
        <div
            className={`flex items-center gap-1.5 bg-black/30 rounded-full px-3 py-1.5 ${className}`}
        >
            <CoinIcon className="w-[1.1em] h-[1.1em] text-gold" />
            <span className="text-gold font-bold tabular-nums">
                {coins.toLocaleString("fr-FR")}
            </span>
        </div>
    );
}

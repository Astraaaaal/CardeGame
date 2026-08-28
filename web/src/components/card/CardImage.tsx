import type { Card } from "@/types/card";

interface CardImageProps {
    card: Card;
    size?: "sm" | "md" | "lg";
    onClick?: () => void;
    className?: string;
}

const sizeMap = {
    sm: "w-24 h-[calc(24*16/9*0.25rem)]",
    md: "w-40 h-[calc(40*16/9*0.25rem)]",
    lg: "w-56 h-[calc(56*16/9*0.25rem)]",
};

function rarityColorToCSS(color: number[]): string {
    return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
}

export default function CardImage({
    card,
    size = "md",
    onClick,
    className = "",
}: CardImageProps) {
    const borderColor = rarityColorToCSS(card.rarity_color);

    return (
        <div
            className={`
        relative rounded-xl overflow-hidden cursor-pointer
        transition-transform duration-200 hover:scale-105
        ${sizeMap[size]} ${className}
      `}
            style={{ boxShadow: `0 0 12px ${borderColor}40`, border: `2px solid ${borderColor}` }}
            onClick={onClick}
        >
            {card.rendered_url ? (
                <img
                    src={card.rendered_url}
                    alt={card.character_name}
                    className="w-full h-full object-cover"
                    loading="lazy"
                />
            ) : (
                <div className="w-full h-full bg-game-surface flex items-center justify-center">
                    <span className="text-white/40 text-xs text-center px-2">
                        {card.character_name}
                    </span>
                </div>
            )}

            {/* Rarity glow indicator */}
            <div
                className="absolute bottom-0 left-0 right-0 h-1"
                style={{ backgroundColor: borderColor }}
            />
        </div>
    );
}

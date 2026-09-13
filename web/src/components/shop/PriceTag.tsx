import { resourceIcon } from "@/utils/resources";

interface PriceTagProps {
    basePrice: number;
    quantity: number;
    resourceId?: string;
}

function getDiscount(quantity: number): number {
    if (quantity >= 10) return 0.15;
    if (quantity >= 5) return 0.10;
    return 0;
}

export default function PriceTag({ basePrice, quantity, resourceId = "coins" }: PriceTagProps) {
    const discount = getDiscount(quantity);
    const total = Math.floor(basePrice * quantity * (1 - discount));

    return (
        <div className="flex items-center gap-2">
            <span className="text-gold font-bold text-xl">
                {total.toLocaleString("fr-FR")} {resourceIcon(resourceId)}
            </span>
            {discount > 0 && (
                <span className="text-green-400 text-xs font-semibold bg-green-400/10 rounded-full px-2 py-0.5">
                    -{Math.round(discount * 100)}%
                </span>
            )}
        </div>
    );
}

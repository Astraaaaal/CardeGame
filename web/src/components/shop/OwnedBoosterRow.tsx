import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { OwnedBooster } from "@/types/booster";
import { useOpenOwnedBoosters } from "@/hooks/usePackOpening";
import { useHasPendingTradeProposal } from "@/hooks/useTradePulse";
import Button from "@/components/ui/Button";
import { errMsg } from "@/utils/errors";

const COUNTS = [1, 5, 10] as const;

/**
 * Pile de boosters possédés : « ×N possédé(s) » + Utiliser, qui propose d'en
 * ouvrir 1, 5, 10 ou tous d'un coup. Partagé entre la boutique (sous le
 * booster à l'affiche) et l'inventaire.
 */
export default function OwnedBoosterRow({ owned, showName = false }: { owned: OwnedBooster; showName?: boolean }) {
    const navigate = useNavigate();
    const openOwned = useOpenOwnedBoosters();
    const tradePending = useHasPendingTradeProposal();
    const [choosing, setChoosing] = useState(false);
    const [error, setError] = useState("");

    const open = (quantity: number) => {
        setError("");
        openOwned.mutate(
            { booster_id: owned.booster_id, quantity, bonus_id: owned.bonus_id },
            { onSuccess: () => navigate("/opening"), onError: (e) => setError(errMsg(e)) },
        );
    };

    return (
        <div className="bg-gold/10 border border-gold/30 rounded-xl px-3 py-2">
            <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                    {showName && <p className="text-white text-sm font-semibold truncate">{owned.booster_name}</p>}
                    {owned.bonus_label && <p className="text-gold text-xs truncate">{owned.bonus_label}</p>}
                    <p className="text-white/70 text-xs">🎴 ×{owned.quantity} possédé{owned.quantity > 1 ? "s" : ""}</p>
                </div>
                <Button
                    variant="gold" size="sm"
                    disabled={tradePending}
                    loading={openOwned.isPending && !choosing}
                    onClick={() => (owned.quantity === 1 ? open(1) : setChoosing((v) => !v))}
                >
                    Utiliser
                </Button>
            </div>
            {choosing && (
                <div className="flex gap-1.5 mt-2">
                    {COUNTS.filter((n) => n < owned.quantity).map((n) => (
                        <button key={n} disabled={openOwned.isPending}
                            className="flex-1 py-1.5 rounded-lg text-xs font-bold bg-white/10 text-white hover:bg-white/20 disabled:opacity-40"
                            onClick={() => open(n)}>
                            ×{n}
                        </button>
                    ))}
                    <button disabled={openOwned.isPending}
                        className="flex-1 py-1.5 rounded-lg text-xs font-bold bg-gold text-game-bg hover:bg-gold/80 disabled:opacity-40"
                        onClick={() => open(owned.quantity)}>
                        Tous ({owned.quantity})
                    </button>
                </div>
            )}
            {tradePending && (
                <p className="text-amber-300/80 text-[11px] mt-1">
                    Ouverture indisponible tant qu'une proposition d'échange attend une réponse.
                </p>
            )}
            {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
        </div>
    );
}

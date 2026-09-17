import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { shopApi } from "@/api/shop";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import { showRewards } from "@/stores/rewardPopupStore";
import { errMsg } from "@/utils/errors";

export const REROLL_TOKEN_PURPOSE = "reroll-token";

export function useRerollTokens() {
    return useQuery({ queryKey: ["reroll-tokens"], queryFn: shopApi.rerollTokens });
}

/**
 * Utilisation d'un reroll de l'inventaire : choix de la carte dans la
 * Collection, puis récapitulatif avant → après avec « Relancer encore » tant
 * qu'il en reste. À monter sur chaque page d'où l'on peut lancer un reroll
 * (`returnTo`) : c'est elle qui applique le reroll au retour de la Collection.
 */
export function useRerollTokenUse(returnTo: string, onError: (message: string) => void) {
    const navigate = useNavigate();
    const qc = useQueryClient();
    const requestSelection = useCardSelectionStore((s) => s.requestSelection);
    const consumeResultIfPurpose = useCardSelectionStore((s) => s.consumeResultIfPurpose);
    const [pendingTokenId, setPendingTokenId] = useState<number | null>(null);
    const handled = useRef(false);

    const apply = async (tokenId: number, cardId: string) => {
        setPendingTokenId(tokenId);
        try {
            const res = await shopApi.applyRerollToken(tokenId, cardId);
            qc.invalidateQueries({ queryKey: ["reroll-tokens"] });
            qc.invalidateQueries({ queryKey: ["collection"] });
            qc.invalidateQueries({ queryKey: ["card-copies"] });
            qc.invalidateQueries({ queryKey: ["player"] });
            const left = res.token.quantity;
            showRewards({
                title: res.token.label,
                items: [{ kind: "reroll", before: res.previous_card, after: res.card, axes: res.token.axes }],
                action: left > 0
                    ? { label: `Relancer encore (${left} restant${left > 1 ? "s" : ""})`, onClick: () => apply(tokenId, cardId) }
                    : undefined,
            });
        } catch (e) {
            onError(errMsg(e));
        } finally {
            setPendingTokenId(null);
        }
    };

    // Retour de la Collection (mode sélection) avec la carte à relancer.
    useEffect(() => {
        if (handled.current) return;
        const result = consumeResultIfPurpose([REROLL_TOKEN_PURPOSE]);
        if (!result) return;
        handled.current = true;
        const tokenId = Number(result.context?.tokenId);
        const cardId = result.selectedCards[0]?.id;
        if (tokenId && cardId) apply(tokenId, cardId);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const start = (tokenId: number) => {
        requestSelection({
            max: 1,
            title: "Choisis la carte à relancer",
            excludeIds: [],
            returnTo,
            context: { purpose: REROLL_TOKEN_PURPOSE, tokenId: String(tokenId) },
        });
        navigate("/collection");
    };

    return { start, pendingTokenId };
}

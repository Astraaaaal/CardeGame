import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { useIsAnimationLocked } from "@/stores/animationLockStore";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import { useTradePulse } from "@/hooks/useTradePulse";
import TradeRequestPopup from "@/components/social/TradeRequestPopup";

/** Surveille l'état des échanges sur toutes les pages : un échange en cours ne
 * se quitte pas (il se conclut ou s'annule) — le joueur y est ramené depuis
 * n'importe quelle page, sauf la Collection le temps de choisir des cartes à
 * proposer. Affiche aussi les demandes reçues et rafraîchit les listes. */
export default function TradeWatcher() {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
    const navigate = useNavigate();
    const { pathname } = useLocation();
    const qc = useQueryClient();
    const locked = useIsAnimationLocked();
    const { data: pulse } = useTradePulse();
    const lastSignature = useRef<string | null>(null);

    const activeId = isAuthenticated ? pulse?.active_session_id ?? null : null;

    const pickingCardsForTrade = useCardSelectionStore((s) =>
        s.request?.context?.purpose === "trade-add" && s.request.context.tradeSessionId === String(activeId)
    );

    useEffect(() => {
        if (!activeId || pathname === `/trade/${activeId}`) return;
        if (locked || (pathname === "/collection" && pickingCardsForTrade)) return;
        navigate(`/trade/${activeId}`, { replace: true });
    }, [activeId, pathname, locked, pickingCardsForTrade, navigate]);

    useEffect(() => {
        if (!pulse) return;
        const signature = `${pulse.active_session_id}|${pulse.incoming_ids.join(",")}|${pulse.outgoing_ids.join(",")}`;
        if (lastSignature.current !== null && lastSignature.current !== signature) {
            qc.invalidateQueries({ queryKey: ["trade-requests"] });
        }
        lastSignature.current = signature;
    }, [pulse, qc]);

    if (!isAuthenticated || !pulse) return null;

    return (
        <TradeRequestPopup
            requests={pulse.incoming_unseen}
            blocked={locked || !!activeId || pathname.startsWith("/trade/")}
        />
    );
}

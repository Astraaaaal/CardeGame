import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { useIsAnimationLocked } from "@/stores/animationLockStore";
import { useTradePulse } from "@/hooks/useTradePulse";
import TradeRequestPopup from "@/components/social/TradeRequestPopup";

const JOINED_KEY = "trade-joined-sessions";

// Sessions dans lesquelles le joueur est déjà entré (auto ou lui-même) : on
// ne l'y ramène de force qu'une fois, sinon quitter la page (pour aller
// choisir une carte, ou juste revenir au menu) le renverrait aussitôt dedans.
// Mémoire + sessionStorage (survit à un rechargement de l'onglet).
const joined = new Set<number>(readStoredJoined());

function readStoredJoined(): number[] {
    try {
        const raw = JSON.parse(sessionStorage.getItem(JOINED_KEY) ?? "[]");
        return Array.isArray(raw) ? raw.filter((v) => typeof v === "number") : [];
    } catch {
        return [];
    }
}

export function markTradeJoined(sessionId: number) {
    if (joined.has(sessionId)) return;
    joined.add(sessionId);
    try {
        sessionStorage.setItem(JOINED_KEY, JSON.stringify([...joined].slice(-20)));
    } catch {
        // stockage indisponible : la mémoire suffit pour cet onglet
    }
}

/** Surveille l'état des échanges sur toutes les pages : entre automatiquement
 * dans un échange accepté par l'autre joueur, affiche les demandes reçues,
 * et rafraîchit les listes quand quelque chose change. */
export default function TradeWatcher() {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
    const navigate = useNavigate();
    const { pathname } = useLocation();
    const qc = useQueryClient();
    const locked = useIsAnimationLocked();
    const { data: pulse } = useTradePulse();
    const lastSignature = useRef<string | null>(null);

    const activeId = isAuthenticated ? pulse?.active_session_id ?? null : null;

    useEffect(() => {
        if (!activeId) return;
        if (pathname === `/trade/${activeId}`) {
            markTradeJoined(activeId);
            return;
        }
        if (locked || joined.has(activeId)) return;
        markTradeJoined(activeId);
        navigate(`/trade/${activeId}`);
    }, [activeId, pathname, locked, navigate]);

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

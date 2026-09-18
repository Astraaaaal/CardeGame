import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { activitiesApi } from "@/api/activities";
import { useAuthStore } from "@/stores/authStore";

export const PRESENCE_KEY = ["presence"];
const PING_MS = 30_000;

/** État du bonus de présence et du coffre d'absence. */
export function usePresenceStatus() {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
    return useQuery({ queryKey: PRESENCE_KEY, queryFn: activitiesApi.presence, enabled: isAuthenticated });
}

/**
 * Signal de présence toutes les 30 s tant que l'appli est affichée (onglet au
 * premier plan) ; relancé dès que l'appli redevient visible. Monté une seule
 * fois pour toute l'appli.
 */
export function usePresencePing() {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
    const qc = useQueryClient();

    useEffect(() => {
        if (!isAuthenticated) return;
        const ping = () => {
            if (document.visibilityState !== "visible") return;
            activitiesApi.ping().then((data) => qc.setQueryData(PRESENCE_KEY, data)).catch(() => {});
        };
        ping();
        const timer = window.setInterval(ping, PING_MS);
        const onVisible = () => { if (document.visibilityState === "visible") ping(); };
        document.addEventListener("visibilitychange", onVisible);
        return () => {
            window.clearInterval(timer);
            document.removeEventListener("visibilitychange", onVisible);
        };
    }, [isAuthenticated, qc]);
}

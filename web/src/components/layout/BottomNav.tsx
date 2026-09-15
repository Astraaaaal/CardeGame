import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { friendsApi } from "@/api/friends";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import FriendsPanel from "@/components/social/FriendsPanel";

/**
 * Navigation basse (Réglages + Social) répétée sur la plupart des pages —
 * pas sur celles où un flux focalisé serait perturbé par une navigation
 * annexe (ouverture de booster, sélection de carte...), cf. les pages qui
 * ne l'incluent pas.
 */
export default function BottomNav() {
    const navigate = useNavigate();
    // Rouvre automatiquement le panneau Social au retour d'une sélection de
    // carte pour un cadeau — ne s'applique en pratique que sur la page dont
    // c'est le `returnTo` (l'accueil), les autres instances démarrent fermées.
    const [socialOpen, setSocialOpen] = useState(
        () => useCardSelectionStore.getState().result?.context?.purpose === "gift"
    );

    const { data: friendRequests } = useQuery({
        queryKey: ["friend-requests"], queryFn: friendsApi.listRequests, staleTime: 30_000,
    });
    const pendingCount = friendRequests?.incoming.length ?? 0;

    return (
        <>
            <footer className="flex items-center justify-between px-4 py-4">
                <button
                    className="text-white/70 hover:text-white text-xl"
                    onClick={() => navigate("/settings")}
                    title="Réglages"
                >
                    ⚙️
                </button>
                <button
                    className="relative text-white/70 hover:text-white text-xl"
                    onClick={() => setSocialOpen(true)}
                    title="Social"
                >
                    👥
                    {pendingCount > 0 && (
                        <span className="absolute -top-1 -right-1.5 inline-flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4">
                            {pendingCount}
                        </span>
                    )}
                </button>
            </footer>

            <FriendsPanel open={socialOpen} onClose={() => setSocialOpen(false)} />
        </>
    );
}

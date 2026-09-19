import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { friendsApi } from "@/api/friends";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import FriendsPanel from "@/components/social/FriendsPanel";

/**
 * Navigation (Réglages + Social) en pastilles flottantes, répétée sur la plupart des pages —
 * pas sur celles où un flux focalisé serait perturbé par une navigation
 * annexe (ouverture de booster, sélection de carte...), cf. les pages qui
 * ne l'incluent pas.
 */
const BUBBLE =
    "pointer-events-auto w-12 h-12 rounded-full bg-game-surface border border-white/15 shadow-lg shadow-black/40 " +
    "flex items-center justify-center text-xl hover:border-accent transition-colors";

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
            {/* Espace réservé : la fin de la page ne passe pas sous les pastilles. */}
            <div className="h-20 shrink-0" aria-hidden />
            {/* Pastilles flottantes, toujours accessibles sans défiler jusqu'en bas.
                Elles remontent au-dessus d'une barre de validation flottante
                (--fab-h, cf. FloatingActionBar). */}
            <div
                className="fixed inset-x-0 z-30 pointer-events-none transition-[bottom] duration-200"
                style={{ bottom: "calc(var(--fab-h, 0px) + 1rem)" }}
            >
                <div className="max-w-mobile mx-auto px-4 flex items-center justify-between">
                    <button
                        className={BUBBLE}
                        onClick={() => navigate("/settings")}
                        title="Réglages"
                    >
                        ⚙️
                    </button>
                    <button
                        className={`relative ${BUBBLE}`}
                        onClick={() => setSocialOpen(true)}
                        title="Social"
                    >
                        👥
                        {pendingCount > 0 && (
                            <span className="absolute -top-1 -right-1 inline-flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4">
                                {pendingCount}
                            </span>
                        )}
                    </button>
                </div>
            </div>

            <FriendsPanel open={socialOpen} onClose={() => setSocialOpen(false)} />
        </>
    );
}

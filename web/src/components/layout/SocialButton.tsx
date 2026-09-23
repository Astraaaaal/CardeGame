import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { friendsApi } from "@/api/friends";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import FriendsPanel from "@/components/social/FriendsPanel";

/**
 * Accès au panneau Social, en pastille fixe dans le coin haut droit — répété
 * sur la plupart des pages, sauf celles où un flux focalisé serait perturbé
 * (ouverture de booster, sélection de carte...).
 *
 * En bas de l'écran, il se battait avec la barre d'onglets et les flèches de
 * défilement de la collection ; en haut, il ne croise plus rien et reste sous
 * le pouce sur les deux formats.
 */
export default function SocialButton() {
    // Rouvre automatiquement le panneau au retour d'une sélection de carte pour
    // un cadeau — ne s'applique en pratique que sur la page dont c'est le
    // `returnTo` (l'accueil), les autres instances démarrent fermées.
    const [open, setOpen] = useState(
        () => useCardSelectionStore.getState().result?.context?.purpose === "gift"
    );

    const { data: friendRequests } = useQuery({
        queryKey: ["friend-requests"], queryFn: friendsApi.listRequests, staleTime: 30_000,
    });
    const pendingCount = friendRequests?.incoming.length ?? 0;

    return (
        <>
            <div className="fixed inset-x-0 top-2 z-40 pointer-events-none">
                <div className="max-w-mobile mx-auto px-3 flex justify-end">
                    <button
                        className="pointer-events-auto relative w-10 h-10 rounded-full bg-game-surface/90 backdrop-blur
                                   border border-white/15 shadow-lg shadow-black/40 flex items-center justify-center
                                   text-lg hover:border-accent transition-colors"
                        onClick={() => setOpen(true)}
                        title="Social"
                        aria-label="Social"
                    >
                        👥
                        {pendingCount > 0 && (
                            <span className="absolute -top-1 -right-1 inline-flex items-center justify-center
                                             bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4">
                                {pendingCount}
                            </span>
                        )}
                    </button>
                </div>
            </div>

            <FriendsPanel open={open} onClose={() => setOpen(false)} />
        </>
    );
}

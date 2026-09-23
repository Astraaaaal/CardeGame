import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { friendsApi } from "@/api/friends";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import FriendsPanel from "@/components/social/FriendsPanel";
import { useIsDesktop } from "@/hooks/useViewport";
import { tabIndexOf } from "./mobileTabs";

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

    // Sur téléphone, la barre d'onglets occupe le bas de l'écran : les pastilles
    // doivent se poser au-dessus, sinon elles passent dessous et deviennent
    // inatteignables.
    const isDesktop = useIsDesktop();
    const { pathname } = useLocation();
    const aboveTabBar = !isDesktop && tabIndexOf(pathname) >= 0;

    const { data: friendRequests } = useQuery({
        queryKey: ["friend-requests"], queryFn: friendsApi.listRequests, staleTime: 30_000,
    });
    const pendingCount = friendRequests?.incoming.length ?? 0;

    // Hauteur occupée par les pastilles (48 px + 16 px de marge).
    useEffect(() => {
        const root = document.documentElement;
        root.style.setProperty("--nav-h", "4rem");
        return () => { root.style.removeProperty("--nav-h"); };
    }, []);

    return (
        <>
            {/* Espace réservé : la fin de la page ne passe pas sous les pastilles. */}
            <div className="h-20 shrink-0" aria-hidden />
            {/* Pastilles flottantes, toujours accessibles sans défiler jusqu'en bas.
                Une barre de validation flottante se place au-dessus d'elles
                (--nav-h, cf. FloatingActionBar). */}
            <div className={`fixed inset-x-0 z-30 pointer-events-none ${aboveTabBar ? "bottom-[4.5rem]" : "bottom-4"}`}>
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

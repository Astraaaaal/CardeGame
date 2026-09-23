import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "@/stores/toastStore";
import { useUnlocks } from "@/hooks/useUnlocks";
import { useIsDesktop } from "@/hooks/useViewport";
import { MOBILE_TABS, tabIndexOf } from "./mobileTabs";

/**
 * Barre d'onglets du bas (téléphone) : les cinq écrans principaux, dans
 * l'ordre du glissement. Un écran encore verrouillé reste visible mais grisé,
 * et dit à quel niveau il s'ouvre — savoir ce qui arrive fait partie du jeu.
 */
export default function MobileTabBar() {
    const navigate = useNavigate();
    const { pathname } = useLocation();
    const { isUnlocked, levelFor } = useUnlocks();
    const isDesktop = useIsDesktop();

    const visible = !isDesktop && tabIndexOf(pathname) >= 0;

    // Hauteur réservée en bas de l'écran : une barre d'action flottante se pose
    // au-dessus d'elle plutôt que dessous (cf. FloatingActionBar).
    useEffect(() => {
        const root = document.documentElement;
        if (!visible) return;
        root.style.setProperty("--nav-h", "3.5rem");
        return () => { root.style.removeProperty("--nav-h"); };
    }, [visible]);

    // Seulement sur téléphone, et seulement sur les écrans qu'elle dessert :
    // ailleurs (ouverture de booster, échange…) le flux reste focalisé.
    if (!visible) return null;

    return (
        <nav className="fixed bottom-0 inset-x-0 z-40 bg-game-surface/95 backdrop-blur border-t border-white/10
                        pb-[env(safe-area-inset-bottom)]">
            <div className="max-w-mobile mx-auto flex">
                {MOBILE_TABS.map((tab) => {
                    const active = pathname === tab.path;
                    const locked = !!tab.feature && !isUnlocked(tab.feature);
                    return (
                        <button
                            key={tab.path}
                            className={`flex-1 min-w-0 py-2 flex flex-col items-center gap-0.5 transition-colors ${
                                active ? "text-accent" : locked ? "text-white/25" : "text-white/55 hover:text-white/80"}`}
                            aria-current={active ? "page" : undefined}
                            onClick={() => locked
                                ? toast.info(`${tab.label} se débloque au niveau ${levelFor(tab.feature!)}.`)
                                : navigate(tab.path)}
                        >
                            <span className="text-lg leading-none">{locked ? "🔒" : tab.icon}</span>
                            <span className="text-[10px] font-semibold truncate max-w-full">{tab.label}</span>
                        </button>
                    );
                })}
            </div>
        </nav>
    );
}

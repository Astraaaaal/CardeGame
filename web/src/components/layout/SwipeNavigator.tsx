import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "@/stores/toastStore";
import { useIsDesktop } from "@/hooks/useViewport";
import { useUnlocks } from "@/hooks/useUnlocks";
import { MOBILE_TABS, tabIndexOf } from "./mobileTabs";

/** Distance horizontale minimale, et rapport au mouvement vertical, pour qu'un
 *  geste compte comme un changement d'écran plutôt qu'un défilement. */
const MIN_DISTANCE = 70;
const HORIZONTAL_RATIO = 1.7;

/** Un geste parti d'une zone qui défile horizontalement (barres de filtres,
 *  rangées d'onglets) ou d'une fenêtre lui appartient : on ne le lui vole pas. */
function belongsToContent(target: EventTarget | null): boolean {
    let node = target as HTMLElement | null;
    while (node && node !== document.body) {
        if (node.dataset?.noSwipe !== undefined) return true;
        if (node.scrollWidth > node.clientWidth + 8) {
            const overflow = getComputedStyle(node).overflowX;
            if (overflow === "auto" || overflow === "scroll") return true;
        }
        node = node.parentElement;
    }
    return false;
}

/**
 * Navigation au glissement entre les cinq écrans du téléphone (cf.
 * mobileTabs.ts) : glisser vers la gauche avance dans la liste, vers la droite
 * recule. N'affiche rien ; inactif sur ordinateur et hors de ces écrans.
 */
export default function SwipeNavigator() {
    const navigate = useNavigate();
    const { pathname } = useLocation();
    const isDesktop = useIsDesktop();
    const { isUnlocked, levelFor } = useUnlocks();
    const start = useRef<{ x: number; y: number; valid: boolean } | null>(null);

    const index = tabIndexOf(pathname);
    const enabled = !isDesktop && index >= 0;

    useEffect(() => {
        if (!enabled) return;

        const down = (e: PointerEvent) => {
            if (e.pointerType === "mouse") return;  // à la souris, la barre d'onglets suffit
            start.current = { x: e.clientX, y: e.clientY, valid: !belongsToContent(e.target) };
        };

        const up = (e: PointerEvent) => {
            const from = start.current;
            start.current = null;
            if (!from?.valid) return;

            const dx = e.clientX - from.x;
            const dy = e.clientY - from.y;
            if (Math.abs(dx) < MIN_DISTANCE || Math.abs(dx) < Math.abs(dy) * HORIZONTAL_RATIO) return;

            const target = MOBILE_TABS[index + (dx < 0 ? 1 : -1)];
            if (!target) return;
            if (target.feature && !isUnlocked(target.feature)) {
                toast.info(`${target.label} se débloque au niveau ${levelFor(target.feature)}.`);
                return;
            }
            navigate(target.path);
        };

        const cancel = () => { start.current = null; };

        window.addEventListener("pointerdown", down, { passive: true });
        window.addEventListener("pointerup", up, { passive: true });
        window.addEventListener("pointercancel", cancel, { passive: true });
        return () => {
            window.removeEventListener("pointerdown", down);
            window.removeEventListener("pointerup", up);
            window.removeEventListener("pointercancel", cancel);
        };
    }, [enabled, index, navigate, isUnlocked, levelFor]);

    return null;
}

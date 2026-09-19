import { useEffect, useRef } from "react";

interface FloatingActionBarProps {
    children: React.ReactNode;
    /** Hauteur réservée en bas de page pour que le contenu final ne passe pas sous la barre. */
    spacerClassName?: string;
}

/**
 * Boutons de validation toujours visibles en bas de l'écran (plutôt qu'en bas
 * de la page), sans bandeau derrière eux. À placer en dernier dans la page :
 * l'espace réservé permet de faire défiler le contenu au-dessus des boutons.
 */
export default function FloatingActionBar({ children, spacerClassName = "h-24" }: FloatingActionBarProps) {
    const bar = useRef<HTMLDivElement>(null);
    // Publie la hauteur de la barre (--fab-h) : les pastilles Réglages/Social
    // (BottomNav) se placent juste au-dessus au lieu d'être masquées.
    useEffect(() => {
        const el = bar.current;
        if (!el) return;
        const root = document.documentElement;
        const update = () => root.style.setProperty("--fab-h", `${el.offsetHeight}px`);
        update();
        const observer = new ResizeObserver(update);
        observer.observe(el);
        return () => {
            observer.disconnect();
            root.style.removeProperty("--fab-h");
        };
    }, []);

    return (
        <>
            <div className={`shrink-0 ${spacerClassName}`} aria-hidden />
            {/* Pas de bandeau : seuls les boutons flottent au-dessus du contenu. */}
            <div ref={bar} className="fixed bottom-0 inset-x-0 z-30 px-4 py-3 pointer-events-none">
                <div className="max-w-sm mx-auto w-full pointer-events-auto">{children}</div>
            </div>
        </>
    );
}

interface FloatingActionBarProps {
    children: React.ReactNode;
    /** Hauteur réservée en bas de page pour que le contenu final ne passe pas sous la barre. */
    spacerClassName?: string;
    /** Boutons compacts placés sur la même ligne que les pastilles Réglages /
     * Social (cf. BottomNav), entre les deux, au lieu d'une barre au-dessus. */
    betweenNav?: boolean;
}

/**
 * Boutons de validation toujours visibles en bas de l'écran (plutôt qu'en bas
 * de la page), sans bandeau derrière eux. À placer en dernier dans la page :
 * l'espace réservé permet de faire défiler le contenu au-dessus des boutons.
 */
export default function FloatingActionBar({ children, spacerClassName = "h-24", betweenNav = false }: FloatingActionBarProps) {
    if (betweenNav) {
        return (
            <div className="fixed inset-x-0 bottom-4 z-30 pointer-events-none">
                {/* Même gabarit que la ligne des pastilles (48 px chacune), contenu centré entre elles. */}
                <div className="max-w-mobile mx-auto px-4">
                    <div className="h-12 mx-14 flex items-center justify-center [&>*]:pointer-events-auto">{children}</div>
                </div>
            </div>
        );
    }
    return (
        <>
            <div className={`shrink-0 ${spacerClassName}`} aria-hidden />
            {/* Pas de bandeau : seuls les boutons flottent au-dessus du contenu,
                et au-dessus des pastilles Réglages/Social si la page en a (--nav-h, cf. BottomNav). */}
            <div className="fixed inset-x-0 z-30 px-4 py-3 pointer-events-none" style={{ bottom: "var(--nav-h, 0px)" }}>
                <div className="max-w-sm mx-auto w-full pointer-events-auto">{children}</div>
            </div>
        </>
    );
}

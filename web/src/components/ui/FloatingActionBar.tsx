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
    return (
        <>
            <div className={`shrink-0 ${spacerClassName}`} aria-hidden />
            {/* Pas de bandeau : seuls les boutons flottent au-dessus du contenu. */}
            <div className="fixed bottom-0 inset-x-0 z-30 px-4 py-3 pointer-events-none">
                <div className="max-w-sm mx-auto w-full pointer-events-auto">{children}</div>
            </div>
        </>
    );
}

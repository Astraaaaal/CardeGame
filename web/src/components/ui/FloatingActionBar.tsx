interface FloatingActionBarProps {
    children: React.ReactNode;
    /** Hauteur réservée en bas de page pour que le contenu final ne passe pas sous la barre. */
    spacerClassName?: string;
}

/**
 * Boutons de validation toujours visibles en bas de l'écran (plutôt qu'en bas
 * de la page). À placer en dernier dans la page : l'espace réservé permet de
 * faire défiler le reste du contenu au-dessus de la barre.
 */
export default function FloatingActionBar({ children, spacerClassName = "h-24" }: FloatingActionBarProps) {
    return (
        <>
            <div className={`shrink-0 ${spacerClassName}`} aria-hidden />
            <div className="fixed bottom-0 inset-x-0 z-30 bg-game-surface border-t border-white/10 px-4 py-3">
                <div className="max-w-sm mx-auto w-full">{children}</div>
            </div>
        </>
    );
}

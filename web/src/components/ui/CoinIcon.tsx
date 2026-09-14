/**
 * Icône de pièce en SVG inline — remplace l'emoji 🪙, dont le glyphe est
 * absent de la police système sur certains environnements (ex: Windows
 * figé sur une ancienne révision de Segoe UI Emoji, antérieure à
 * l'ajout de cet emoji en 2020), où il s'affiche comme un carré vide.
 * `fill="currentColor"` : hérite la couleur du texte parent (text-gold, etc.).
 */
export default function CoinIcon({ className = "" }: { className?: string }) {
    return (
        <svg
            viewBox="0 0 24 24"
            className={`inline-block shrink-0 ${className}`}
            aria-hidden="true"
        >
            <circle cx="12" cy="12" r="10" fill="currentColor" />
            <circle cx="12" cy="12" r="9.25" fill="none" stroke="#000" strokeOpacity="0.18" strokeWidth="1" />
            <circle cx="12" cy="12" r="6.5" fill="none" stroke="#000" strokeOpacity="0.18" strokeWidth="1" />
            <text
                x="12" y="16.2" textAnchor="middle"
                fontSize="10" fontWeight="700" fill="#000" fillOpacity="0.32"
                fontFamily="Inter, system-ui, sans-serif"
            >
                $
            </text>
        </svg>
    );
}

/** Icônes dessinées (monochromes) des objets : booster et reroll — remplacent les emojis 🎴 / 🎲. */
export function BoosterIcon({ className = "w-[1.1em] h-[1.1em]" }: { className?: string }) {
    return (
        <svg className={`inline-block align-[-0.15em] ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="2" strokeLinejoin="round" aria-hidden>
            <rect x="5" y="3" width="14" height="18" rx="2" />
            <path d="M5 7h14M5 17h14" />
            <path d="M12 10.2l1 2 2.1.3-1.5 1.5.4 2.1-2-1-2 1 .4-2.1-1.5-1.5 2.1-.3z" fill="currentColor" stroke="none" />
        </svg>
    );
}

export function RerollIcon({ className = "w-[1.1em] h-[1.1em]" }: { className?: string }) {
    return (
        <svg className={`inline-block align-[-0.15em] ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <path d="M20 11a8 8 0 0 0-14.9-4M4 13a8 8 0 0 0 14.9 4" />
            <path d="M5 3v4h4M19 21v-4h-4" />
        </svg>
    );
}

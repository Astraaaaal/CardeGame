interface TutorialSphereProps {
    size?: number;
}

/**
 * La sphère qui porte la parole du tutoriel — en attendant la mascotte.
 *
 * Coque fixe, cœur qui bat : c'est le battement intérieur qui fait lire
 * « ça parle » plutôt que « ça charge ». Une sphère qui grossit tout entière
 * flotterait au lieu de rester ancrée à côté de sa bulle.
 */
export default function TutorialSphere({ size = 44 }: TutorialSphereProps) {
    const ring = Math.round(size * 0.14);
    const core = Math.round(size * 0.32);

    return (
        <div className="relative shrink-0" style={{ width: size, height: size }} aria-hidden>
            <div className="absolute inset-0 rounded-full bg-accent animate-tuto-halo" />
            <div
                className="absolute rounded-full bg-game-surface border border-accent/50"
                style={{ inset: ring }}
            />
            <div
                className="absolute rounded-full bg-accent-light animate-tuto-core"
                style={{ inset: core }}
            />
        </div>
    );
}

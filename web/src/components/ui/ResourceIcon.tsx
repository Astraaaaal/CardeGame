import type { ReactNode } from "react";
import CoinIcon from "./CoinIcon";

/** Fragment de rareté : éclat taillé, couleur du palier. */
const shard = (color: string) => (
    <>
        <path d="M8 1l5 5-3 9-6-2-1-8z" fill={color} />
        <path d="M8 1l-1 7 3 7M3 5l4 3 6-2" fill="none" stroke="#fff" strokeOpacity=".45" strokeWidth=".8" />
    </>
);

/** Poussière de qualité : nuage de grains, plus brillant au fil des paliers. */
const dust = (color: string, glow = false) => (
    <>
        {glow && <circle cx="8" cy="9" r="6" fill={color} opacity=".25" />}
        {[[4, 11, 1.6], [8, 12, 1.9], [12, 10, 1.5], [6, 7, 1.3], [10, 6, 1.4], [8, 3.5, 1]].map(([cx, cy, r]) => (
            <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r={r} fill={color} />
        ))}
    </>
);

const ICONS: Record<string, ReactNode> = {
    frag_rare: shard("#50A0FF"),
    frag_epic: shard("#B450FF"),
    frag_legendary: shard("#FFC832"),
    silver_ore: (
        <>
            <path d="M2 11l2-6 5-3 5 4 1 6-5 3z" fill="#6b7280" />
            <path d="M5 7l3 2 3-3M7 12l2-3 3 2" fill="none" stroke="#e5e7eb" strokeWidth="1.2" />
        </>
    ),
    gold_nugget: (
        <>
            <path d="M3 10c0-4 3-7 6-6 4 0 5 4 4 7-1 3-4 4-7 3-2 0-3-2-3-4z" fill="#f5b50a" />
            <path d="M6 7c1-1 3-1 4 0" fill="none" stroke="#fff4c2" strokeWidth="1.2" strokeLinecap="round" />
        </>
    ),
    rough_diamond: (
        <>
            <path d="M4 3h8l3 4-7 8-7-8z" fill="#67e8f9" />
            <path d="M1 7h14M4 3l4 12 4-12M6 7l2-4 2 4" fill="none" stroke="#fff" strokeOpacity=".55" strokeWidth=".8" />
        </>
    ),
    prism_crystal: (
        <>
            <defs>
                <linearGradient id="res-prism" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0" stopColor="#f472b6" />
                    <stop offset=".35" stopColor="#facc15" />
                    <stop offset=".65" stopColor="#4ade80" />
                    <stop offset="1" stopColor="#60a5fa" />
                </linearGradient>
            </defs>
            <path d="M8 1l5 3v8l-5 3-5-3V4z" fill="url(#res-prism)" />
            <path d="M8 1v14M3 4l5 3 5-3" fill="none" stroke="#fff" strokeOpacity=".6" strokeWidth=".8" />
        </>
    ),
    art_ink: (
        <>
            <path d="M8 1c3 4 5 7 5 9a5 5 0 01-10 0c0-2 2-5 5-9z" fill="#ec4899" />
            <path d="M6 10a2 2 0 002 2" fill="none" stroke="#fff" strokeOpacity=".6" strokeWidth="1.2" strokeLinecap="round" />
        </>
    ),
    ex_seal: (
        <>
            <circle cx="8" cy="8" r="7" fill="#dc2626" />
            <circle cx="8" cy="8" r="5.3" fill="none" stroke="#fecaca" strokeWidth=".7" />
            <text x="8" y="10.4" textAnchor="middle" fontSize="6.5" fontWeight="900" fill="#fff" fontFamily="sans-serif">EX</text>
        </>
    ),
    glitter: (
        <>
            <path d="M6 2l1 4 4 1-4 1-1 4-1-4-4-1 4-1z" fill="#f9a8d4" />
            <path d="M12 8l.7 2.3L15 11l-2.3.7L12 14l-.7-2.3L9 11l2.3-.7z" fill="#fde047" />
            <circle cx="12.5" cy="3.5" r="1" fill="#fff" />
        </>
    ),
    dust_fine: dust("#cbd5e1"),
    dust_lustrous: dust("#5eead4", true),
    dust_pearly: dust("#fbcfe8", true),
    dust_star: (
        <>
            {dust("#fde047", true)}
            <path d="M8 1l.9 2.1L11 4l-2.1.9L8 7l-.9-2.1L5 4l2.1-.9z" fill="#fff" />
        </>
    ),
};

/** Icône d'une ressource : pièces (CoinIcon), éclats premium, ressources de
 *  recyclage (dessins par palier), poussière et ressources créées dans l'admin (✨). */
export default function ResourceIcon({
    resourceId,
    className = "w-[1em] h-[1em] align-[-0.15em]",
}: {
    resourceId: string;
    className?: string;
}) {
    if (resourceId === "coins") return <CoinIcon className={className} />;
    if (resourceId === "shards") return <span className="text-cyan-300">✦</span>;
    const icon = ICONS[resourceId];
    if (icon) return <svg viewBox="0 0 16 16" className={`inline-block ${className}`} aria-hidden="true">{icon}</svg>;
    return <span>✨</span>;
}

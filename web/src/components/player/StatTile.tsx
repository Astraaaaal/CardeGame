import type { ReactNode } from "react";

interface StatTileProps {
    label: string;
    value: ReactNode;
    /** Précision secondaire (meilleur rang, etc.), sur une ligne réservée. */
    detail?: string | null;
    icon?: ReactNode;
    /** Met la valeur en avant (la statistique principale de l'écran). */
    accent?: boolean;
}

/**
 * Case de statistique du profil. Toutes les cases ont la même hauteur et le
 * même rythme — libellé discret en haut, valeur alignée à gauche en bas, ligne
 * de précision toujours réservée même vide : sans ça, une case à deux lignes
 * décalait ses voisines et l'ensemble paraissait bricolé.
 */
export default function StatTile({ label, value, detail, icon, accent }: StatTileProps) {
    return (
        <div className="bg-game-surface border border-white/10 rounded-xl px-3 py-2.5 flex flex-col gap-1">
            <p className="text-white/35 text-[10px] uppercase tracking-wider truncate">{label}</p>
            <p className={`font-extrabold leading-none tabular-nums flex items-center gap-1.5 ${
                accent ? "text-accent text-xl" : "text-white text-lg"}`}>
                {icon}
                <span className="truncate">{value}</span>
            </p>
            <p className="text-gold text-[10px] leading-none h-3 truncate">{detail ?? ""}</p>
        </div>
    );
}

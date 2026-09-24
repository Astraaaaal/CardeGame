import { useState } from "react";
import type { Card } from "@/types/card";
import { useTypes, typeColor as lookupTypeColor, typeColorAlpha } from "@/hooks/useTypes";

/**
 * CardImage — rendu complet d'une carte à partir des métadonnées (CSS/DOM).
 * Pas de rendu serveur : l'art du personnage vient de web/public/characters/,
 * le reste (cadre rareté, badges, effet d'usure qualité, sheen shiny…) est en CSS.
 * Toutes les tailles internes sont en `cqi` (1cqi = 1% de la largeur de la carte),
 * donc la carte se met à l'échelle proprement quelle que soit sa largeur.
 * Les couleurs de type viennent de l'API (/api/types) — gérables depuis /admin,
 * pas d'une liste figée dans le code.
 */

// Effet visuel de la qualité (usure)
const QUALITY_FX: Record<string, { filter: string; streak?: boolean }> = {
    authentic: { filter: "none" }, mint: { filter: "none" },
    graded: { filter: "none" }, excellent: { filter: "none" },
    preserved: { filter: "saturate(.92)" },
    fair: { filter: "saturate(.85) brightness(.97)" },
    worn: { filter: "saturate(.72) brightness(.92) contrast(1.05)" },
    faded: { filter: "saturate(.45) brightness(1.06) contrast(.9)" },
    scratched: { filter: "saturate(.78) contrast(1.08)", streak: true },
    torn: { filter: "saturate(.6) brightness(.9)", streak: true },
    damaged: { filter: "grayscale(.4) brightness(.82) contrast(1.1)" },
    unplayable: { filter: "grayscale(.7) brightness(.7)" },
    unreadable: { filter: "grayscale(.85) brightness(.6) blur(1px)" },
    destroyed: { filter: "grayscale(.92) brightness(.5) blur(1.4px)" },
};

const HIDE_DESC = new Set(["unplayable", "unreadable", "destroyed"]);
const MAX_W: Record<string, number> = { sm: 150, md: 220, lg: 300 };

const rgb = (c: number[]) => `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
// Même couleur avec une transparence. Coller « 55 » derrière un rgb() donnait
// une couleur invalide, et une seule valeur invalide fait jeter TOUTE la
// déclaration box-shadow par le navigateur : la lueur de rareté et la
// bordure ne s'affichaient pas du tout.
const rgba = (c: number[], alpha: number) => `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${alpha})`;

interface CardImageProps {
    card: Card;
    size?: "sm" | "md" | "lg";
    onClick?: () => void;
    className?: string;
}

export default function CardImage({
    card,
    size = "md",
    onClick,
    className = "",
}: CardImageProps) {
    const [imgOk, setImgOk] = useState(true);
    const { data: types } = useTypes();

    const rarity = rgb(card.rarity_color);
    const typeCol = lookupTypeColor(types, card.character_type);
    const hasJewelry = card.jewelry_id !== "none";
    const frame = hasJewelry ? rgb(card.jewelry_color) : typeCol;
    const fx = QUALITY_FX[card.quality_id] ?? { filter: "none" };
    // Full art : illustration pleine carte. Sinon : fenêtre 4:3 et panneau de texte.
    const isFullArt = card.specialty_id === "full_art";
    const shiny = card.specialty_id === "shiny";
    const ex = card.specialty_id === "ex";
    const showDesc =
        size !== "sm" && !HIDE_DESC.has(card.quality_id) && !!card.character_description;

    return (
        <div
            className={`relative select-none ${onClick ? "cursor-pointer" : ""} ${className}`}
            style={{
                width: "100%",
                maxWidth: MAX_W[size],
                aspectRatio: "5 / 7",
                containerType: "inline-size",
                // Isole le repaint de la carte (filtres, blend, animations) :
                // sans ça, une sélection de texte à la souris repeint toute la
                // grille à chaque mouvement, ce qui fige les machines modestes.
                contain: "paint",
                // En % de la carte elle-même : un "cqi" ici se rapporterait au conteneur
                // parent (ou à la fenêtre), d'où des coins quasi ovales sur écran large.
                borderRadius: "5% / 3.57%",
                overflow: "hidden",
                // Une full art n'a aucune bordure : l'illustration va jusqu'au bord,
                // c'est tout son intérêt. Sur les autres, la bordure porte la
                // couleur du bijou — elle dit « argent », « or », « prismatique »
                // sans qu'on ait besoin de l'écrire.
                boxShadow: [
                    isFullArt ? null : `inset 0 0 0 3px ${frame}`,
                    isFullArt ? null : "inset 0 0 0 4.5px rgba(0,0,0,.55)",
                    `0 0 ${ex ? 26 : 14}px ${rgba(card.rarity_color, ex ? 0.53 : 0.33)}`,
                    "0 4px 14px rgba(0,0,0,.45)",
                ].filter(Boolean).join(", "),
                transition: "transform .18s ease",
            }}
            onClick={onClick}
            onMouseEnter={
                onClick
                    ? (e) => (e.currentTarget.style.transform = "scale(1.04)")
                    : undefined
            }
            onMouseLeave={
                onClick
                    ? (e) => (e.currentTarget.style.transform = "scale(1)")
                    : undefined
            }
        >
            {/* Fond des cartes encadrées : la fenêtre d'illustration s'y détache. */}
            {!isFullArt && <div style={{ position: "absolute", inset: 0, background: "#1B1B2E" }} />}

            {/* Art du personnage — pleine carte en full art, en fenêtre 4:3 sinon. */}
            <div
                style={isFullArt
                    ? { position: "absolute", inset: 0 }
                    : {
                        position: "absolute", left: "5.5cqi", right: "5.5cqi", top: "17cqi",
                        aspectRatio: "4 / 3", borderRadius: "3cqi", overflow: "hidden",
                        boxShadow: "inset 0 0 0 1.5px rgba(255,255,255,.18)",
                    }}
            >
                {imgOk ? (
                    <img
                        src={`/characters/${card.image_url}`}
                        alt=""
                        loading="lazy"
                        onError={() => setImgOk(false)}
                        style={{
                            position: "absolute", inset: 0, width: "100%", height: "100%",
                            objectFit: "cover", filter: fx.filter,
                        }}
                    />
                ) : (
                    <div
                        style={{
                            position: "absolute", inset: 0,
                            background: `linear-gradient(150deg, ${frame}, #14141F)`,
                        }}
                    />
                )}
            </div>

            {/* Stries d'usure (scratched / torn) */}
            {fx.streak && (
                <div
                    style={{
                        position: "absolute",
                        inset: 0,
                        background:
                            "repeating-linear-gradient(118deg, transparent 0 9px, rgba(255,255,255,.05) 9px 10px, transparent 10px 16px)",
                        mixBlendMode: "overlay",
                    }}
                />
            )}

            {/* Reflet shiny */}
            {shiny && (
                <div
                    style={{
                        position: "absolute",
                        inset: "-40%",
                        background:
                            "linear-gradient(60deg, transparent 42%, rgba(255,255,255,.4) 50%, transparent 58%)",
                        animation: "cardSheen 3.5s linear infinite",
                        pointerEvents: "none",
                    }}
                />
            )}

            {/* Dégradés haut/bas : seulement quand le texte se pose sur l'illustration. */}
            {isFullArt && (
                <div
                    style={{
                        position: "absolute",
                        inset: 0,
                        background:
                            "linear-gradient(to bottom, rgba(0,0,0,.62) 0%, transparent 24%, transparent 52%, rgba(0,0,0,.85) 100%)",
                    }}
                />
            )}

            {/* Contenu texte */}
            <div
                style={{
                    position: "absolute",
                    inset: 0,
                    padding: "6cqi 5.5cqi",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    color: "#fff",
                    fontFamily: "Inter, system-ui, sans-serif",
                }}
            >
                {/* Haut : nom + type */}
                <div
                    style={{
                        display: "flex",
                        gap: "3cqi",
                        alignItems: "flex-start",
                        justifyContent: "space-between",
                    }}
                >
                    <span
                        style={{
                            fontWeight: 800,
                            fontSize: "6.6cqi",
                            lineHeight: 1.1,
                            textShadow: "0 1px 3px rgba(0,0,0,.9)",
                        }}
                    >
                        {/* Pas de mention de spécialité : un shiny, un EX ou une full
                            art se reconnaissent à leurs effets, pas à une étiquette. */}
                        {card.character_name}
                    </span>
                    <span
                        style={{
                            flexShrink: 0,
                            fontSize: "4.6cqi",
                            fontWeight: 700,
                            padding: "1.2cqi 2.6cqi",
                            borderRadius: "3cqi",
                            background: typeColorAlpha(types, card.character_type, 0.9),
                            textShadow: "0 1px 2px rgba(0,0,0,.6)",
                            whiteSpace: "nowrap",
                        }}
                    >
                        {card.character_type}
                    </span>
                </div>

                {/* Panneau de texte des cartes encadrées : description aujourd'hui,
                    effets de combat demain. Absent quand il n'a rien à dire — un
                    cadre vide vaut moins qu'un peu d'air. */}
                {!isFullArt && showDesc && (
                    <div
                        style={{
                            position: "absolute",
                            left: "5.5cqi", right: "5.5cqi",
                            top: "calc(17cqi + 66.75cqi + 5cqi)",
                            bottom: "20cqi",
                            borderRadius: "3cqi",
                            background: "rgba(255,255,255,.04)",
                            boxShadow: "inset 0 0 0 1.5px rgba(255,255,255,.08)",
                            padding: "3.5cqi 4cqi",
                            overflow: "hidden",
                        }}
                    >
                        <p
                            style={{
                                fontSize: "4.2cqi",
                                lineHeight: 1.3,
                                color: "rgba(255,255,255,.82)",
                                display: "-webkit-box",
                                WebkitLineClamp: 5,
                                WebkitBoxOrient: "vertical",
                                overflow: "hidden",
                                margin: 0,
                            }}
                        >
                            {card.character_description}
                        </p>
                    </div>
                )}

                {/* Bas : description (full art) + type + gen/set */}
                <div style={{ display: "flex", flexDirection: "column", gap: "2cqi" }}>
                    {showDesc && isFullArt && (
                        <p
                            style={{
                                fontSize: "4.4cqi",
                                lineHeight: 1.25,
                                color: "rgba(255,255,255,.82)",
                                display: "-webkit-box",
                                WebkitLineClamp: 3,
                                WebkitBoxOrient: "vertical",
                                overflow: "hidden",
                                textShadow: "0 1px 2px rgba(0,0,0,.9)",
                                margin: 0,
                            }}
                        >
                            {card.character_description}
                        </p>
                    )}
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            gap: "2cqi",
                        }}
                    >
                        <div style={{ display: "flex", alignItems: "center", gap: "1.5cqi", minWidth: 0 }}>
                            <span
                                style={{
                                    fontSize: "4.8cqi",
                                    fontWeight: 800,
                                    padding: "1cqi 3cqi",
                                    borderRadius: "3cqi",
                                    background: rarity,
                                    color: "#0D0D14",
                                    whiteSpace: "nowrap",
                                }}
                            >
                                {card.rarity_name}
                            </span>
                            {card.power != null && (
                                <span
                                    style={{
                                        fontSize: "4cqi",
                                        fontWeight: 700,
                                        color: "#FFD84D",
                                        textShadow: "0 1px 2px rgba(0,0,0,.9)",
                                        whiteSpace: "nowrap",
                                    }}
                                    title="Puissance"
                                >
                                    ⚡{card.power}
                                </span>
                            )}
                        </div>
                        <span
                            style={{
                                fontSize: "3.9cqi",
                                color: "rgba(255,255,255,.78)",
                                fontWeight: 600,
                                textShadow: "0 1px 2px rgba(0,0,0,.9)",
                                whiteSpace: "nowrap",
                            }}
                        >
                            Gen {card.gen} · {card.set_id}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}

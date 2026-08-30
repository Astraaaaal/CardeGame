import { useState } from "react";
import type { Card } from "@/types/card";

/**
 * CardImage — rendu complet d'une carte à partir des métadonnées (CSS/DOM).
 * Pas de rendu serveur : l'art du personnage vient de web/public/characters/,
 * le reste (cadre rareté, badges, effet d'usure qualité, sheen shiny…) est en CSS.
 * Toutes les tailles internes sont en `cqi` (1cqi = 1% de la largeur de la carte),
 * donc la carte se met à l'échelle proprement quelle que soit sa largeur.
 */

// Couleurs de type — portées depuis prototype/src/engine/card_renderer.py
const TYPE_COLORS: Record<string, string> = {
    Plantes: "#3CB44B", Feu: "#DC3C28", Eau: "#3278DC", "Électrique": "#E0B000",
    "Ténèbres": "#6A4CA0", "Lumière": "#D9C878", Glace: "#7FC8F0", Roche: "#A0825A",
    Vent: "#8FC9B4", Poison: "#AA50C8", "Métal": "#8C99A8", Psychique: "#E664B4",
    Dragon: "#643CC8", "Fée": "#FF96C8", Combat: "#B4321E", Normal: "#8A8A8A",
};

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

    const rarity = rgb(card.rarity_color);
    const typeColor = TYPE_COLORS[card.character_type] ?? "#6A6A80";
    const hasJewelry = card.jewelry_id !== "none";
    const frame = hasJewelry ? rgb(card.jewelry_color) : typeColor;
    const fx = QUALITY_FX[card.quality_id] ?? { filter: "none" };
    const isSpecial = !["normal", "full_art"].includes(card.specialty_id);
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
                borderRadius: "5cqi",
                overflow: "hidden",
                boxShadow: `inset 0 0 0 3px ${frame}, inset 0 0 0 4.5px rgba(0,0,0,.55), 0 0 ${ex ? 26 : 14}px ${rarity}${ex ? "88" : "55"}, 0 4px 14px rgba(0,0,0,.45)`,
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
            {/* Art du personnage */}
            {imgOk ? (
                <img
                    src={`/characters/${card.image_url}`}
                    alt=""
                    loading="lazy"
                    onError={() => setImgOk(false)}
                    style={{
                        position: "absolute",
                        inset: 0,
                        width: "100%",
                        height: "100%",
                        objectFit: "cover",
                        filter: fx.filter,
                    }}
                />
            ) : (
                <div
                    style={{
                        position: "absolute",
                        inset: 0,
                        background: `linear-gradient(150deg, ${frame}, #14141F)`,
                    }}
                />
            )}

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

            {/* Dégradés haut/bas pour la lisibilité du texte */}
            <div
                style={{
                    position: "absolute",
                    inset: 0,
                    background:
                        "linear-gradient(to bottom, rgba(0,0,0,.62) 0%, transparent 24%, transparent 52%, rgba(0,0,0,.85) 100%)",
                }}
            />

            {/* Bandeau jewelry */}
            {hasJewelry && (
                <span
                    style={{
                        position: "absolute",
                        top: "6cqi",
                        left: "50%",
                        transform: "translateX(-50%)",
                        fontSize: "3.8cqi",
                        fontWeight: 700,
                        padding: "0.8cqi 2.8cqi",
                        borderRadius: "3cqi",
                        background: `${rgb(card.jewelry_color)}e6`,
                        color: "#0D0D14",
                        whiteSpace: "nowrap",
                    }}
                >
                    {card.jewelry_name}
                </span>
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
                        {card.character_name}
                        {isSpecial && (
                            <span style={{ fontWeight: 700, fontSize: "5cqi", color: rarity }}>
                                {" "}
                                {card.specialty_name}
                            </span>
                        )}
                    </span>
                    <span
                        style={{
                            flexShrink: 0,
                            fontSize: "4.6cqi",
                            fontWeight: 700,
                            padding: "1.2cqi 2.6cqi",
                            borderRadius: "3cqi",
                            background: `${typeColor}e6`,
                            textShadow: "0 1px 2px rgba(0,0,0,.6)",
                            whiteSpace: "nowrap",
                        }}
                    >
                        {card.character_type}
                    </span>
                </div>

                {/* Bas : description + rareté + gen/set */}
                <div style={{ display: "flex", flexDirection: "column", gap: "2cqi" }}>
                    {showDesc && (
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
                        <span
                            style={{
                                fontSize: "4.8cqi",
                                fontWeight: 800,
                                padding: "1cqi 3cqi",
                                borderRadius: "3cqi",
                                background: rarity,
                                color: "#0D0D14",
                            }}
                        >
                            {card.rarity_name}
                        </span>
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

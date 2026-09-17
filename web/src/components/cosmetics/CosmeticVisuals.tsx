import type { CSSProperties, ReactNode } from "react";
import type { Cosmetic } from "@/types/premium";

const imageSrc = (c: Cosmetic) => `/cosmetics/${c.image_url}`;

/** Style d'un fond de vitrine : image si renseignée, sinon dégradé animé ou non. */
export function showcaseBackgroundStyle(c: Cosmetic | null | undefined): CSSProperties | undefined {
    if (!c) return undefined;
    if (c.image_url) {
        return { backgroundImage: `url(${imageSrc(c)})`, backgroundSize: "cover", backgroundPosition: "center" };
    }
    const style: CSSProperties = {
        backgroundImage: `linear-gradient(135deg, ${c.color_from}55, #0d0d14 55%, ${c.color_to}55)`,
    };
    if (c.animation === "shine" || c.animation === "pulse") {
        style.backgroundSize = "220% 220%";
        style.animation = `cosmetic-pan ${c.animation === "shine" ? 6 : 10}s ease-in-out infinite alternate`;
    }
    if (c.animation === "rainbow") style.animation = "cosmetic-hue 12s linear infinite";
    return style;
}

/**
 * Avatar entouré de son cadre équipé. Sans cadre : simple bordure neutre.
 * `size` en pixels (diamètre de l'avatar, cadre compris).
 */
export function FramedAvatar({ frame, size, children }: {
    frame: Cosmetic | null | undefined;
    size: number;
    children: ReactNode;
}) {
    const ring = Math.max(3, Math.round(size / 18));
    const inner = (
        <div className="w-full h-full rounded-full overflow-hidden bg-black/40 flex items-center justify-center">
            {children}
        </div>
    );

    if (!frame) {
        return (
            <div className="rounded-full border-2 border-white/10 shrink-0" style={{ width: size, height: size }}>
                {inner}
            </div>
        );
    }

    if (frame.image_url) {
        return (
            <div className="relative shrink-0" style={{ width: size, height: size }}>
                <div className="absolute" style={{ inset: ring }}>{inner}</div>
                <img src={imageSrc(frame)} alt="" className="absolute -inset-[12%] w-[124%] h-[124%] max-w-none pointer-events-none" />
            </div>
        );
    }

    const gradient = `conic-gradient(from 0deg, ${frame.color_from}, ${frame.color_to}, ${frame.color_from})`;
    return (
        <div
            className="relative rounded-full shrink-0"
            style={{
                width: size, height: size, padding: ring,
                ["--cosmetic-glow" as string]: frame.color_from,
                animation: frame.animation === "pulse" ? "cosmetic-pulse 4s ease-in-out infinite" : undefined,
            }}
        >
            <div
                className="absolute inset-0 rounded-full overflow-hidden"
                style={{ animation: frame.animation === "rainbow" ? "cosmetic-hue 6s linear infinite" : undefined }}
            >
                <div
                    className="absolute -inset-1/4"
                    style={{
                        background: gradient,
                        animation: frame.animation === "shine" || frame.animation === "rainbow"
                            ? "cosmetic-spin 4s linear infinite"
                            : undefined,
                    }}
                />
            </div>
            <div className="relative w-full h-full">{inner}</div>
        </div>
    );
}

/** Aperçu compact d'un cosmétique (catalogue, inventaire, admin). */
export function CosmeticPreview({ cosmetic, size = 56 }: { cosmetic: Cosmetic; size?: number }) {
    if (cosmetic.kind === "avatar_frame") {
        return (
            <FramedAvatar frame={cosmetic} size={size}>
                {/* Silhouette d'avatar : le cadre s'aperçoit mieux qu'avec un « ? ». */}
                <svg viewBox="0 0 24 24" className="w-2/3 h-2/3 text-white/25" fill="currentColor" aria-hidden>
                    <circle cx="12" cy="9" r="4" />
                    <path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8z" />
                </svg>
            </FramedAvatar>
        );
    }
    return (
        <div
            className="rounded-lg border border-white/10 shrink-0"
            style={{ width: size * 1.4, height: size, ...showcaseBackgroundStyle(cosmetic) }}
        />
    );
}

export const COSMETIC_KIND_LABEL: Record<Cosmetic["kind"], string> = {
    avatar_frame: "Cadre d'avatar",
    showcase_background: "Fond de vitrine",
};

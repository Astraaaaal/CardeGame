/** Formats d'affichage partagés (nombres, pourcentages, dates, couleurs). */

/** Nombre à la française : espaces entre les milliers. */
export const formatNumber = (n: number) => n.toLocaleString("fr-FR");

/** Part entre 0 et 1, en pourcentage arrondi. */
export const formatPercent = (x: number) => `${Math.round(x * 100)} %`;

/** Date UTC renvoyée par l'API (sans « Z » final) : sans lui, elle serait lue comme heure locale. */
export const parseUtc = (s: string) => new Date(s.endsWith("Z") ? s : s + "Z");

/** Date et heure courtes, à l'heure locale : jj/mm/aaaa hh:mm. */
export function formatDateTime(iso: string): string {
    return parseUtc(iso).toLocaleDateString("fr-FR", {
        day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
}

/** Couleur [r, g, b] en CSS. */
export const rgbCss = (c: number[]) => `rgb(${c[0]}, ${c[1]}, ${c[2]})`;

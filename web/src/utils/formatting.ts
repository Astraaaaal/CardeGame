/**
 * Formatting helpers.
 */

export function formatCoins(coins: number): string {
    return coins.toLocaleString("fr-FR");
}

export function formatProbability(p: number): string {
    return `${(p * 100).toFixed(4)}%`;
}

export function rgbToCSS(color: number[]): string {
    return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
}

import type { Player } from "@/types/player";

/** Solde du joueur pour une ressource donnée. "coins" vit sur user.coins,
 *  toute autre ressource dans user.resources[]. */
export function getResourceBalance(user: Player | null | undefined, resourceId: string): number {
    if (!user) return 0;
    if (resourceId === "coins") return user.coins;
    return user.resources.find((r) => r.id === resourceId)?.amount ?? 0;
}

/** Icône générique pour une ressource, utilisée quand ce n'est pas des pièces. */
export function resourceIcon(resourceId: string): string {
    return resourceId === "coins" ? "🪙" : "✨";
}

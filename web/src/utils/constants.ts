/**
 * Utility constants for the frontend.
 */

export const PACK_QUANTITIES = [1, 5, 10] as const;
export type PackQuantity = (typeof PACK_QUANTITIES)[number];

export const DISCOUNT_MAP: Record<number, number> = {
    1: 0,
    5: 0.10,
    10: 0.15,
};

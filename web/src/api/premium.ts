import api from "./client";
import type { Cosmetic, MyCosmetics, PremiumProduct, PremiumStatus } from "@/types/premium";

export const premiumApi = {
    status: () => api.get<PremiumStatus>("/premium/status").then((r) => r.data),
    products: () => api.get<PremiumProduct[]>("/premium/products").then((r) => r.data),
    /** Retourne l'URL de la page de paiement Stripe. */
    checkout: (productId: string) =>
        api.post<{ url: string }>("/premium/checkout", { product_id: productId }).then((r) => r.data.url),
    cosmetics: () => api.get<Cosmetic[]>("/premium/cosmetics").then((r) => r.data),
    myCosmetics: () => api.get<MyCosmetics>("/premium/cosmetics/mine").then((r) => r.data),
    equip: (avatarFrameId: string | null, showcaseBackgroundId: string | null) =>
        api.put<MyCosmetics>("/premium/cosmetics/equip", {
            avatar_frame_id: avatarFrameId,
            showcase_background_id: showcaseBackgroundId,
        }).then((r) => r.data),
};

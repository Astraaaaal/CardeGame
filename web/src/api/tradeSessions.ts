import api from "./client";
import type { TradeSession } from "@/types/trade";

export const tradeSessionsApi = {
    get: (sessionId: number) => api.get<TradeSession>(`/trade-sessions/${sessionId}`).then((r) => r.data),
    addCard: (sessionId: number, userCardId: string) =>
        api.post<TradeSession>(`/trade-sessions/${sessionId}/items/cards`, { user_card_id: userCardId }).then((r) => r.data),
    addResource: (sessionId: number, resourceId: string, amount: number) =>
        api.post<TradeSession>(`/trade-sessions/${sessionId}/items/resources`, { resource_id: resourceId, amount }).then((r) => r.data),
    addBooster: (sessionId: number, boosterId: string, bonusId: number | null, amount: number) =>
        api.post<TradeSession>(`/trade-sessions/${sessionId}/items/boosters`, { booster_id: boosterId, bonus_id: bonusId, amount }).then((r) => r.data),
    addReroll: (sessionId: number, rerollTokenId: number, amount: number) =>
        api.post<TradeSession>(`/trade-sessions/${sessionId}/items/rerolls`, { reroll_token_id: rerollTokenId, amount }).then((r) => r.data),
    removeItem: (sessionId: number, itemId: number) =>
        api.delete<TradeSession>(`/trade-sessions/${sessionId}/items/${itemId}`).then((r) => r.data),
    setReady: (sessionId: number, ready: boolean) =>
        api.post<TradeSession>(`/trade-sessions/${sessionId}/ready`, { ready }).then((r) => r.data),
    confirm: (sessionId: number) =>
        api.post<TradeSession>(`/trade-sessions/${sessionId}/confirm`).then((r) => r.data),
    cancel: (sessionId: number) =>
        api.post(`/trade-sessions/${sessionId}/cancel`).then(() => undefined),
};

import api from "./client";
import type {
    Friend, FriendRequestItem, FriendRequestsResponse,
    TradeRequestItem, TradeRequestsResponse,
} from "@/types/social";

export const friendsApi = {
    list: () => api.get<Friend[]>("/friends/").then((r) => r.data),
    remove: (userId: number) => api.delete(`/friends/${userId}`).then(() => undefined),

    addCloseFriend: (userId: number) => api.post(`/friends/${userId}/close-friend`).then(() => undefined),
    removeCloseFriend: (userId: number) => api.delete(`/friends/${userId}/close-friend`).then(() => undefined),

    listRequests: () => api.get<FriendRequestsResponse>("/friends/requests").then((r) => r.data),
    send: (username: string) =>
        api.post<FriendRequestItem>("/friends/requests", { username }).then((r) => r.data),
    accept: (requestId: number) =>
        api.post<Friend>(`/friends/requests/${requestId}/accept`).then((r) => r.data),
    decline: (requestId: number) =>
        api.delete(`/friends/requests/${requestId}`).then(() => undefined),

    listTradeRequests: () => api.get<TradeRequestsResponse>("/friends/trade-requests").then((r) => r.data),
    listUnseenTradeRequests: () =>
        api.get<TradeRequestItem[]>("/friends/trade-requests/unseen").then((r) => r.data),
    markTradeRequestsSeen: () =>
        api.post("/friends/trade-requests/mark-seen").then(() => undefined),
    proposeTrade: (friendUserId: number) =>
        api.post<TradeRequestItem>(`/friends/${friendUserId}/trade-request`).then((r) => r.data),
    sendTrade: (username: string) =>
        api.post<TradeRequestItem>("/friends/trade-requests", { username }).then((r) => r.data),
    cancelTradeRequest: (requestId: number) =>
        api.delete(`/friends/trade-requests/${requestId}`).then(() => undefined),
};

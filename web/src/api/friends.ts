import api from "./client";
import type {
    Friend, FriendGroup, FriendRequestItem, FriendRequestsResponse,
    TradePulse, TradeRequestItem, TradeRequestsResponse,
} from "@/types/social";
import type { TradeSession } from "@/types/trade";

export const friendsApi = {
    list: () => api.get<Friend[]>("/friends/").then((r) => r.data),
    remove: (userId: number) => api.delete(`/friends/${userId}`).then(() => undefined),

    addCloseFriend: (userId: number) => api.post(`/friends/${userId}/close-friend`).then(() => undefined),
    removeCloseFriend: (userId: number) => api.delete(`/friends/${userId}/close-friend`).then(() => undefined),

    listGroups: () => api.get<FriendGroup[]>("/friends/groups").then((r) => r.data),
    createGroup: (name: string) => api.post<FriendGroup>("/friends/groups", { name }).then((r) => r.data),
    renameGroup: (id: number, name: string) => api.patch<FriendGroup>(`/friends/groups/${id}`, { name }).then((r) => r.data),
    deleteGroup: (id: number) => api.delete(`/friends/groups/${id}`).then(() => undefined),
    addToGroup: (userId: number, groupId: number) => api.post(`/friends/${userId}/groups/${groupId}`).then(() => undefined),
    removeFromGroup: (userId: number, groupId: number) => api.delete(`/friends/${userId}/groups/${groupId}`).then(() => undefined),

    listRequests: () => api.get<FriendRequestsResponse>("/friends/requests").then((r) => r.data),
    send: (username: string) =>
        api.post<FriendRequestItem>("/friends/requests", { username }).then((r) => r.data),
    accept: (requestId: number) =>
        api.post<Friend>(`/friends/requests/${requestId}/accept`).then((r) => r.data),
    decline: (requestId: number) =>
        api.delete(`/friends/requests/${requestId}`).then(() => undefined),

    listTradeRequests: () => api.get<TradeRequestsResponse>("/friends/trade-requests").then((r) => r.data),
    tradePulse: () => api.get<TradePulse>("/friends/trade-requests/pulse").then((r) => r.data),
    markTradeRequestsSeen: () =>
        api.post("/friends/trade-requests/mark-seen").then(() => undefined),
    markTradeRequestSeen: (requestId: number) =>
        api.post(`/friends/trade-requests/${requestId}/seen`).then(() => undefined),
    proposeTrade: (friendUserId: number) =>
        api.post<TradeRequestItem>(`/friends/${friendUserId}/trade-request`).then((r) => r.data),
    sendTrade: (username: string) =>
        api.post<TradeRequestItem>("/friends/trade-requests", { username }).then((r) => r.data),
    cancelTradeRequest: (requestId: number) =>
        api.delete(`/friends/trade-requests/${requestId}`).then(() => undefined),
    acceptTradeRequest: (requestId: number) =>
        api.post<TradeSession>(`/friends/trade-requests/${requestId}/accept`).then((r) => r.data),
};

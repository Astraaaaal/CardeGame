import api from "./client";
import type { AppMessage } from "@/types/message";

export interface SendGiftBody {
    username: string;
    subject?: string;
    body?: string;
    item_type: "card" | "resource";
    user_card_id?: string;
    resource_id?: string;
    amount?: number;
}

export const messagesApi = {
    list: () => api.get<AppMessage[]>("/messages/").then((r) => r.data),
    unreadCount: () => api.get<{ count: number }>("/messages/unread-count").then((r) => r.data.count),
    markRead: (id: number) => api.post<AppMessage>(`/messages/${id}/read`).then((r) => r.data),
    claim: (id: number) => api.post<AppMessage>(`/messages/${id}/claim`).then((r) => r.data),
    remove: (id: number) => api.delete(`/messages/${id}`).then(() => undefined),
    sendGift: (body: SendGiftBody) => api.post<AppMessage>("/messages/gift", body).then((r) => r.data),
};

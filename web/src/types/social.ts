export interface Friend {
    user_id: number;
    username: string;
    display_name: string;
    online: boolean;
    last_seen: string | null;
    close_friend: boolean;
}

export interface FriendRequestItem {
    id: number;
    user_id: number;
    username: string;
    display_name: string;
    created_at: string;
}

export interface FriendRequestsResponse {
    incoming: FriendRequestItem[];
    outgoing: FriendRequestItem[];
}

export interface TradeRequestItem {
    id: number;
    user_id: number;
    username: string;
    display_name: string;
    created_at: string;
}

export interface TradeRequestsResponse {
    incoming: TradeRequestItem[];
    outgoing: TradeRequestItem[];
}

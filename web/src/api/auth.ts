import api from "./client";
import type { LoginRequest, RegisterRequest, TokenResponse, MessageResponse } from "@/types/auth";

export const authApi = {
    register: async (data: RegisterRequest): Promise<MessageResponse> => {
        const res = await api.post("/auth/register", data);
        return res.data;
    },

    login: async (data: LoginRequest): Promise<TokenResponse> => {
        const res = await api.post("/auth/login", data);
        return res.data;
    },

    refresh: async (refreshToken: string): Promise<TokenResponse> => {
        const res = await api.post("/auth/refresh", { refresh_token: refreshToken });
        return res.data;
    },

    logout: async (refreshToken: string): Promise<void> => {
        await api.post("/auth/logout", { refresh_token: refreshToken });
    },
};

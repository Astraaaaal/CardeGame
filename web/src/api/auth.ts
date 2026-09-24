import api from "./client";
import type { LoginRequest, RegisterRequest, TokenResponse, MessageResponse } from "@/types/auth";

export const authApi = {
    status: async (): Promise<{ closed: boolean; message: string; invite_required: boolean }> => {
        const res = await api.get("/auth/status");
        return res.data;
    },

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

    verifyEmail: async (token: string): Promise<MessageResponse> => {
        const res = await api.post("/auth/verify-email", { token });
        return res.data;
    },

    requestPasswordReset: async (identifier: string): Promise<MessageResponse> => {
        const res = await api.post("/auth/password-reset/request", { identifier });
        return res.data;
    },

    confirmPasswordReset: async (identifier: string, code: string, new_password: string): Promise<MessageResponse> => {
        const res = await api.post("/auth/password-reset/confirm", { identifier, code, new_password });
        return res.data;
    },

    logout: async (refreshToken: string): Promise<void> => {
        await api.post("/auth/logout", { refresh_token: refreshToken });
    },
};

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/api/auth";
import { playerApi } from "@/api/player";
import { useAuthStore } from "@/stores/authStore";
import type { LoginRequest, RegisterRequest } from "@/types/auth";

export function useLogin() {
    const { setTokens, setUser } = useAuthStore();
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (data: LoginRequest) => {
            const tokens = await authApi.login(data);
            setTokens(tokens.access_token, tokens.refresh_token);
            const player = await playerApi.getMe();
            setUser(player);
            return player;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["player"] });
        },
    });
}

export function useRegister() {
    return useMutation({
        mutationFn: (data: RegisterRequest) => authApi.register(data),
    });
}

export function useLogout() {
    const { logout, refreshToken } = useAuthStore();
    const queryClient = useQueryClient();

    return () => {
        // Révoque le refresh token côté serveur (best-effort), puis purge en local.
        if (refreshToken) authApi.logout(refreshToken).catch(() => {});
        logout();
        queryClient.clear();
    };
}

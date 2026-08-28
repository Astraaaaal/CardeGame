import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Player } from "@/types/player";

interface AuthState {
    accessToken: string | null;
    refreshToken: string | null;
    user: Player | null;
    isAuthenticated: boolean;

    setTokens: (access: string, refresh: string) => void;
    setUser: (user: Player) => void;
    updateCoins: (coins: number) => void;
    logout: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            accessToken: null,
            refreshToken: null,
            user: null,
            isAuthenticated: false,

            setTokens: (access, refresh) => {
                localStorage.setItem("access_token", access);
                localStorage.setItem("refresh_token", refresh);
                set({ accessToken: access, refreshToken: refresh, isAuthenticated: true });
            },

            setUser: (user) => set({ user }),

            updateCoins: (coins) =>
                set((state) => ({
                    user: state.user ? { ...state.user, coins } : null,
                })),

            logout: () => {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");
                set({
                    accessToken: null,
                    refreshToken: null,
                    user: null,
                    isAuthenticated: false,
                });
            },
        }),
        {
            name: "auth-storage",
            partialize: (state) => ({
                accessToken: state.accessToken,
                refreshToken: state.refreshToken,
                isAuthenticated: state.isAuthenticated,
            }),
        }
    )
);

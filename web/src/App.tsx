import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { playerApi } from "@/api/player";
import LoginPage from "@/pages/LoginPage";
import MainMenu from "@/pages/MainMenu";
import Shop from "@/pages/Shop";
import PackOpening from "@/pages/PackOpening";
import Collection from "@/pages/Collection";
import Profile from "@/pages/Profile";
import PlayerShowcase from "@/pages/PlayerShowcase";
import Leaderboard from "@/pages/Leaderboard";
import Progression from "@/pages/Progression";
import TradeSessionPage from "@/pages/TradeSessionPage";
import AdminPanel from "@/pages/AdminPanel";
import LegalNotice from "@/pages/LegalNotice";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const { isAuthenticated, setUser } = useAuthStore();

    // Hydrate le profil pour TOUTES les pages protégées (coins, streak…),
    // pas seulement quand on arrive par le menu. Dédupliqué par react-query.
    const { data: player } = useQuery({
        queryKey: ["player"],
        queryFn: playerApi.getMe,
        enabled: isAuthenticated,
        staleTime: 30_000,
    });

    useEffect(() => {
        if (player) setUser(player);
    }, [player, setUser]);

    if (!isAuthenticated) return <Navigate to="/login" replace />;
    return <>{children}</>;
}

export default function App() {
    return (
        <div className="max-w-mobile mx-auto min-h-screen">
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/admin" element={<AdminPanel />} />
                <Route path="/legal" element={<LegalNotice />} />
                <Route
                    path="/"
                    element={
                        <ProtectedRoute>
                            <MainMenu />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/shop"
                    element={
                        <ProtectedRoute>
                            <Shop />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/opening"
                    element={
                        <ProtectedRoute>
                            <PackOpening />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/collection"
                    element={
                        <ProtectedRoute>
                            <Collection />
                        </ProtectedRoute>
                    }
                />
                <Route path="/resource-shop" element={<Navigate to="/shop" replace />} />
                <Route
                    path="/profile"
                    element={
                        <ProtectedRoute>
                            <Profile />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/players/:userId"
                    element={
                        <ProtectedRoute>
                            <PlayerShowcase />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/leaderboard"
                    element={
                        <ProtectedRoute>
                            <Leaderboard />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/progression"
                    element={
                        <ProtectedRoute>
                            <Progression />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/trade/:sessionId"
                    element={
                        <ProtectedRoute>
                            <TradeSessionPage />
                        </ProtectedRoute>
                    }
                />
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </div>
    );
}

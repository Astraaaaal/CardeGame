import TutorialBubble from "@/components/tutorial/TutorialBubble";
import { useUnlockAnnouncements } from "@/components/tutorial/useTutorial";
import { useEffect } from "react";
import LevelWatcher from "@/components/player/LevelWatcher";
import { Routes, Route, Navigate } from "react-router-dom";
import MobileTabBar from "@/components/layout/MobileTabBar";
import SwipeNavigator from "@/components/layout/SwipeNavigator";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { playerApi } from "@/api/player";
import LoginPage from "@/pages/LoginPage";
import MainMenu from "@/pages/MainMenu";
import Shop from "@/pages/Shop";
import PackOpening from "@/pages/PackOpening";
import Collection from "@/pages/Collection";
import Profile from "@/pages/Profile";
import Settings from "@/pages/Settings";
import PlayerShowcase from "@/pages/PlayerShowcase";
import Leaderboard from "@/pages/Leaderboard";
import Progression from "@/pages/Progression";
import Inventory from "@/pages/Inventory";
import VerifyEmail from "@/pages/VerifyEmail";
import TradeSessionPage from "@/pages/TradeSessionPage";
import AdminPanel from "@/pages/AdminPanel";
import LegalNotice from "@/pages/LegalNotice";
import Activities from "@/pages/Activities";
import Guild from "@/pages/Guild";
import TradeWatcher from "@/components/trade/TradeWatcher";
import RewardPopup from "@/components/player/RewardPopup";
import Toaster from "@/components/ui/Toaster";
import { usePresencePing } from "@/hooks/usePresence";

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

/** Annonce les fonctionnalités qui viennent de s'ouvrir. Monté une seule fois,
 *  il n'affiche rien par lui-même : il alimente la file de TutorialBubble. */
function UnlockAnnouncer() {
    useUnlockAnnouncements();
    return null;
}

export default function App() {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
    // Signal de présence (bonus de chance, coffre d'absence) tant que l'appli est affichée.
    usePresencePing();
    // Une seule colonne, quelle que soit la taille de l'écran : étalée sur un
    // grand écran, l'interface paraissait évasée et molle.
    return (
        <div className="max-w-mobile mx-auto min-h-screen">
            <TradeWatcher />
            <RewardPopup />
            <Toaster />
            {isAuthenticated && <LevelWatcher />}
            {isAuthenticated && <TutorialBubble />}
            {isAuthenticated && <UnlockAnnouncer />}
            {isAuthenticated && <MobileTabBar />}
            {isAuthenticated && <SwipeNavigator />}
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/admin" element={<AdminPanel />} />
                <Route path="/legal" element={<LegalNotice />} />
                <Route path="/verify-email" element={<VerifyEmail />} />
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
                    path="/settings"
                    element={
                        <ProtectedRoute>
                            <Settings />
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
                    path="/activities"
                    element={
                        <ProtectedRoute>
                            <Activities />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/guild"
                    element={
                        <ProtectedRoute>
                            <Guild />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/inventory"
                    element={
                        <ProtectedRoute>
                            <Inventory />
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

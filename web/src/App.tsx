import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import LoginPage from "@/pages/LoginPage";
import MainMenu from "@/pages/MainMenu";
import BoosterShop from "@/pages/BoosterShop";
import PackOpening from "@/pages/PackOpening";
import Collection from "@/pages/Collection";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const { isAuthenticated } = useAuthStore();
    if (!isAuthenticated) return <Navigate to="/login" replace />;
    return <>{children}</>;
}

export default function App() {
    return (
        <div className="max-w-mobile mx-auto min-h-screen">
            <Routes>
                <Route path="/login" element={<LoginPage />} />
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
                            <BoosterShop />
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
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </div>
    );
}

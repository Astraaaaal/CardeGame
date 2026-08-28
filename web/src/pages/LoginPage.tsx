import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import Button from "@/components/ui/Button";
import { useLogin, useRegister } from "@/hooks/useAuth";

export default function LoginPage() {
    const [isRegister, setIsRegister] = useState(false);
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const navigate = useNavigate();

    const loginMutation = useLogin();
    const registerMutation = useRegister();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (username.length < 3 || password.length < 4) {
            setError("Nom (3+ car.) et mot de passe (4+ car.) requis");
            return;
        }

        try {
            if (isRegister) {
                await registerMutation.mutateAsync({ username, password });
                // Auto-login après inscription
                await loginMutation.mutateAsync({ username, password });
            } else {
                await loginMutation.mutateAsync({ username, password });
            }
            navigate("/");
        } catch (err: unknown) {
            if (err && typeof err === "object" && "response" in err) {
                const axiosErr = err as { response?: { data?: { detail?: string } } };
                setError(axiosErr.response?.data?.detail || "Erreur de connexion");
            } else {
                setError("Erreur de connexion");
            }
        }
    };

    const isLoading = loginMutation.isPending || registerMutation.isPending;

    return (
        <div className="min-h-screen bg-game-bg flex flex-col items-center justify-center px-4">
            <motion.div
                className="w-full max-w-sm"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
            >
                {/* Logo / Titre */}
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-extrabold text-white mb-2">
                        Carde<span className="text-accent">Game</span>
                    </h1>
                    <p className="text-white/50 text-sm">
                        {isRegister ? "Créer un compte" : "Connexion"}
                    </p>
                </div>

                {/* Form */}
                <form
                    onSubmit={handleSubmit}
                    className="bg-game-surface rounded-2xl p-6 border border-white/10 space-y-4"
                >
                    <div>
                        <label className="block text-white/70 text-sm mb-1">
                            Nom d'utilisateur
                        </label>
                        <input
                            type="text"
                            className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-2.5
                         text-white placeholder-white/30 focus:border-accent focus:outline-none
                         transition-colors"
                            placeholder="Entrez votre nom..."
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            autoComplete="username"
                        />
                    </div>

                    <div>
                        <label className="block text-white/70 text-sm mb-1">
                            Mot de passe
                        </label>
                        <input
                            type="password"
                            className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-2.5
                         text-white placeholder-white/30 focus:border-accent focus:outline-none
                         transition-colors"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            autoComplete={isRegister ? "new-password" : "current-password"}
                        />
                    </div>

                    {error && (
                        <motion.p
                            className="text-red-400 text-sm text-center"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                        >
                            {error}
                        </motion.p>
                    )}

                    <Button
                        type="submit"
                        variant="primary"
                        size="lg"
                        loading={isLoading}
                        className="w-full"
                    >
                        {isRegister ? "Créer le compte" : "Se connecter"}
                    </Button>
                </form>

                {/* Toggle */}
                <p className="text-center text-white/40 text-sm mt-4">
                    {isRegister ? "Déjà un compte ?" : "Pas encore de compte ?"}{" "}
                    <button
                        className="text-accent hover:underline"
                        onClick={() => {
                            setIsRegister(!isRegister);
                            setError("");
                        }}
                    >
                        {isRegister ? "Se connecter" : "S'inscrire"}
                    </button>
                </p>
            </motion.div>
        </div>
    );
}

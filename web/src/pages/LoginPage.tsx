import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import Button from "@/components/ui/Button";
import PasswordInput from "@/components/ui/PasswordInput";
import { useLogin, useRegister } from "@/hooks/useAuth";
import { authApi } from "@/api/auth";
import { errMsg } from "@/utils/errors";

type Mode = "login" | "register" | "forgot" | "reset";

const INPUT = `w-full bg-black/30 border border-white/10 rounded-xl px-4 py-2.5
    text-white placeholder-white/30 focus:border-accent focus:outline-none transition-colors`;

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div>
            <label className="block text-white/70 text-sm mb-1">{label}</label>
            {children}
        </div>
    );
}

export default function LoginPage() {
    const [mode, setMode] = useState<Mode>("login");
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [email, setEmail] = useState("");
    const [newsletter, setNewsletter] = useState(false);
    const [inviteCode, setInviteCode] = useState("");
    const [code, setCode] = useState("");
    const [error, setError] = useState("");
    const [info, setInfo] = useState("");
    const [busy, setBusy] = useState(false);
    const navigate = useNavigate();

    const loginMutation = useLogin();
    const registerMutation = useRegister();

    const switchMode = (next: Mode) => {
        setMode(next);
        setError("");
        setInfo("");
        if (next === "forgot") setPassword("");
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setInfo("");

        try {
            if (mode === "login") {
                if (!username.trim() || !password) {
                    setError("Pseudo (ou e-mail) et mot de passe requis");
                    return;
                }
                await loginMutation.mutateAsync({ username, password });
                navigate("/");
            } else if (mode === "register") {
                if (username.length < 3 || password.length < 4) {
                    setError("Nom (3+ car.) et mot de passe (4+ car.) requis");
                    return;
                }
                if (!email.includes("@")) {
                    setError("Adresse e-mail requise");
                    return;
                }
                await registerMutation.mutateAsync({ username, password, email, newsletter, invite_code: inviteCode });
                // Auto-login après inscription
                await loginMutation.mutateAsync({ username, password });
                navigate("/");
            } else if (mode === "forgot") {
                if (!username.trim()) {
                    setError("Indique ton pseudo ou ton e-mail");
                    return;
                }
                setBusy(true);
                const res = await authApi.requestPasswordReset(username);
                setInfo(res.message);
                setMode("reset");
            } else {
                if (!/^\d{6}$/.test(code) || password.length < 4) {
                    setError("Code à 6 chiffres et nouveau mot de passe (4+ car.) requis");
                    return;
                }
                setBusy(true);
                const res = await authApi.confirmPasswordReset(username, code, password);
                setCode("");
                setPassword("");
                setMode("login");
                setInfo(res.message);
            }
        } catch (err: unknown) {
            setError(errMsg(err));
        } finally {
            setBusy(false);
        }
    };

    const isLoading = loginMutation.isPending || registerMutation.isPending || busy;
    const subtitle = { login: "Connexion", register: "Créer un compte", forgot: "Mot de passe oublié", reset: "Nouveau mot de passe" }[mode];
    const submitLabel = { login: "Se connecter", register: "Créer le compte", forgot: "Recevoir un code", reset: "Changer le mot de passe" }[mode];

    return (
        <div className="min-h-screen bg-game-bg flex flex-col items-center justify-center px-4">
            <motion.div
                className="w-full max-w-sm"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
            >
                {/* Logo / Titre */}
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-extrabold text-white mb-2 inline-flex items-baseline gap-2">
                        Carde<span className="text-accent">Game</span>
                        <span className="text-xs font-bold tracking-wide text-white/40">BÊTA</span>
                    </h1>
                    <p className="text-white/50 text-sm">{subtitle}</p>
                </div>

                <form
                    onSubmit={handleSubmit}
                    className="bg-game-surface rounded-2xl p-6 border border-white/10 space-y-4"
                >
                    <Field label={mode === "register" ? "Nom d'utilisateur" : "Pseudo ou e-mail"}>
                        <input
                            type="text"
                            className={INPUT}
                            placeholder={mode === "register" ? "Entrez votre nom..." : "Pseudo ou adresse e-mail..."}
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            autoComplete="username"
                            disabled={mode === "reset"}
                        />
                    </Field>

                    {mode === "register" && (
                        <Field label="Adresse e-mail">
                            <input
                                type="email"
                                className={INPUT}
                                placeholder="toi@exemple.fr"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                autoComplete="email"
                            />
                        </Field>
                    )}

                    {mode === "reset" && (
                        <Field label="Code reçu par e-mail">
                            <input
                                type="text"
                                inputMode="numeric"
                                maxLength={6}
                                className={`${INPUT} tracking-[0.4em] text-center text-lg`}
                                placeholder="000000"
                                value={code}
                                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                                autoComplete="one-time-code"
                            />
                        </Field>
                    )}

                    {mode !== "forgot" && (
                        <Field label={mode === "reset" ? "Nouveau mot de passe" : "Mot de passe"}>
                            <PasswordInput
                                className={INPUT}
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                autoComplete={mode === "login" ? "current-password" : "new-password"}
                            />
                        </Field>
                    )}

                    {mode === "register" && (
                        <>
                            <Field label="Code d'invitation">
                                <input
                                    type="text"
                                    className={INPUT}
                                    placeholder="Reçu de la personne qui t'invite"
                                    value={inviteCode}
                                    onChange={(e) => setInviteCode(e.target.value)}
                                    autoComplete="off"
                                />
                            </Field>
                            <label className="flex items-start gap-2 text-white/60 text-xs cursor-pointer">
                                <input
                                    type="checkbox"
                                    className="mt-0.5"
                                    checked={newsletter}
                                    onChange={(e) => setNewsletter(e.target.checked)}
                                />
                                Recevoir la newsletter de CardeGame (nouveautés, événements). Désinscription possible à tout moment.
                            </label>
                        </>
                    )}

                    {mode === "login" && (
                        <button
                            type="button"
                            className="text-accent text-xs hover:underline"
                            onClick={() => switchMode("forgot")}
                        >
                            Mot de passe oublié ?
                        </button>
                    )}

                    {info && <p className="text-green-400 text-sm text-center">{info}</p>}
                    {error && (
                        <motion.p
                            className="text-red-400 text-sm text-center"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                        >
                            {error}
                        </motion.p>
                    )}

                    <Button type="submit" variant="primary" size="lg" loading={isLoading} className="w-full">
                        {submitLabel}
                    </Button>

                    {mode === "reset" && (
                        <button
                            type="button"
                            className="text-white/40 text-xs hover:text-white w-full"
                            onClick={() => switchMode("forgot")}
                        >
                            Renvoyer un code
                        </button>
                    )}
                </form>

                <p className="text-center text-white/40 text-sm mt-4">
                    {mode === "login" ? "Pas encore de compte ?" : mode === "register" ? "Déjà un compte ?" : ""}{" "}
                    <button
                        className="text-accent hover:underline"
                        onClick={() => switchMode(mode === "login" ? "register" : "login")}
                    >
                        {mode === "login" ? "S'inscrire" : "Se connecter"}
                    </button>
                </p>
                <p className="text-center mt-2">
                    <Link to="/legal" className="text-white/30 text-xs hover:text-white/60">Mentions légales</Link>
                </p>
            </motion.div>
        </div>
    );
}

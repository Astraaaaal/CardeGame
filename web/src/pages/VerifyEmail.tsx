import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/authStore";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { errMsg } from "@/utils/errors";

/** Page ouverte depuis le lien de confirmation reçu par e-mail. */
export default function VerifyEmail() {
    const [params] = useSearchParams();
    const token = params.get("token") ?? "";
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
    const qc = useQueryClient();
    const [state, setState] = useState<{ ok: boolean; text: string } | null>(null);
    // Le lien est à usage unique : sous StrictMode l'effet est joué deux fois.
    const sent = useRef(false);

    useEffect(() => {
        if (sent.current) return;
        sent.current = true;
        if (!token) {
            setState({ ok: false, text: "Lien incomplet." });
            return;
        }
        authApi.verifyEmail(token)
            .then((res) => {
                setState({ ok: true, text: res.message });
                qc.invalidateQueries({ queryKey: ["player"] });
            })
            .catch((e) => setState({ ok: false, text: errMsg(e) }));
    }, [token, qc]);

    return (
        <div className="min-h-screen bg-game-bg flex flex-col items-center justify-center px-4 text-center">
            {!state ? (
                <LoadingSpinner text="Confirmation en cours..." />
            ) : (
                <div className="bg-game-surface rounded-2xl p-6 border border-white/10 max-w-sm w-full space-y-4">
                    <p className="text-4xl">{state.ok ? "✅" : "⚠️"}</p>
                    <p className={state.ok ? "text-green-400" : "text-red-400"}>{state.text}</p>
                    <Link to={isAuthenticated ? "/" : "/login"} className="inline-block text-accent font-semibold">
                        {isAuthenticated ? "Retour au jeu" : "Se connecter"}
                    </Link>
                </div>
            )}
        </div>
    );
}

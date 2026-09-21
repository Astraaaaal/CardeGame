import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { playerApi } from "@/api/player";
import { useAuthStore } from "@/stores/authStore";
import Button from "@/components/ui/Button";
import Toggle from "@/components/ui/Toggle";
import { errMsg } from "@/utils/errors";

/** Adresse e-mail (ajout / changement / confirmation) et abonnement newsletter. */
export default function EmailSettings() {
    const { user, setUser } = useAuthStore();
    const qc = useQueryClient();
    const [editing, setEditing] = useState(!user?.email);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const refresh = (player: Parameters<typeof setUser>[0]) => {
        setUser(player);
        qc.setQueryData(["player"], player);
    };

    const change = useMutation({
        mutationFn: () => playerApi.changeEmail(email, password),
        onSuccess: (player) => {
            refresh(player);
            setEditing(false);
            setEmail("");
            setPassword("");
            setMsg({ text: `Lien de confirmation envoyé à ${player.email}.`, ok: true });
        },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });
    const resend = useMutation({
        mutationFn: playerApi.resendVerification,
        onSuccess: (res) => setMsg({ text: res.message, ok: true }),
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });
    const newsletter = useMutation({
        mutationFn: playerApi.setNewsletter,
        onSuccess: refresh,
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    if (!user) return null;

    return (
        <div className="bg-game-surface rounded-2xl border border-white/10 p-4 space-y-3">
            <h3 className="text-white font-bold text-sm">Adresse e-mail</h3>

            {user.email && (
                <div className="flex items-center justify-between gap-2">
                    <span className="text-white text-sm truncate">{user.email}</span>
                    {user.email_verified ? (
                        <span className="text-green-400 text-xs shrink-0">✓ Confirmée</span>
                    ) : (
                        <span className="text-amber-300 text-xs shrink-0">Non confirmée</span>
                    )}
                </div>
            )}

            {user.email && !user.email_verified && (
                <p className="text-white/40 text-xs">
                    Clique sur le lien reçu par e-mail. Sans confirmation, la récupération de mot de passe
                    et la newsletter ne fonctionnent pas.{" "}
                    <button className="text-accent hover:underline" disabled={resend.isPending} onClick={() => resend.mutate()}>
                        Renvoyer le lien
                    </button>
                </p>
            )}

            {editing ? (
                <div className="space-y-2">
                    <input
                        type="email"
                        className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                        placeholder={user.email ? "Nouvelle adresse e-mail" : "Ton adresse e-mail"}
                        value={email}
                        onChange={(e) => { setEmail(e.target.value); setMsg(null); }}
                        autoComplete="email"
                    />
                    <input
                        type="password"
                        className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                        placeholder="Mot de passe actuel"
                        value={password}
                        onChange={(e) => { setPassword(e.target.value); setMsg(null); }}
                        autoComplete="current-password"
                    />
                    <div className="flex gap-2">
                        <Button
                            variant="primary" size="sm" className="flex-1"
                            disabled={!email.includes("@") || !password}
                            loading={change.isPending} success={change.isSuccess}
                            onClick={() => change.mutate()}
                        >
                            {user.email ? "Changer l'adresse" : "Ajouter l'adresse"}
                        </Button>
                        {user.email && (
                            <Button variant="secondary" size="sm" onClick={() => setEditing(false)}>Annuler</Button>
                        )}
                    </div>
                </div>
            ) : (
                <button className="text-accent text-xs hover:underline" onClick={() => setEditing(true)}>
                    Changer d'adresse e-mail
                </button>
            )}

            <div className="flex items-center justify-between gap-3 pt-2 border-t border-white/5">
                <div>
                    <p className="text-white text-sm">Newsletter</p>
                    <p className="text-white/40 text-xs">Nouveautés et événements, envoyés à ton adresse confirmée.</p>
                </div>
                <Toggle
                    checked={user.newsletter_opt_in}
                    disabled={!user.email || newsletter.isPending}
                    onChange={(v) => newsletter.mutate(v)}
                />
            </div>

            {msg && <p className={`text-xs ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>}
        </div>
    );
}

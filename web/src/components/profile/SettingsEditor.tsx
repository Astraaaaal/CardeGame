import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { playerApi } from "@/api/player";
import { useLogout } from "@/hooks/useAuth";
import type { PlayerSettings, TradeRequestPolicy, GiftPolicy } from "@/types/player";
import Button from "@/components/ui/Button";
import DeleteAccountModal from "@/components/profile/DeleteAccountModal";

function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof r?.data?.detail === "string") return r.data.detail;
    }
    return "Erreur.";
}

const POLICY_OPTIONS: { value: TradeRequestPolicy; label: string }[] = [
    { value: "everyone", label: "Tout le monde" },
    { value: "friends", label: "Amis uniquement" },
    { value: "close_friends", label: "Amis proches uniquement" },
    { value: "none", label: "Personne" },
];

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
    return (
        <button
            className={`w-11 h-6 rounded-full transition-colors relative shrink-0 ${checked ? "bg-accent" : "bg-white/15"}`}
            onClick={() => onChange(!checked)}
        >
            <span
                className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                    checked ? "translate-x-5" : "translate-x-0.5"
                }`}
            />
        </button>
    );
}

export default function SettingsEditor() {
    const qc = useQueryClient();
    const navigate = useNavigate();
    const logout = useLogout();
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
    const [deleteOpen, setDeleteOpen] = useState(false);

    const { data, isLoading } = useQuery({ queryKey: ["player-settings"], queryFn: playerApi.getSettings });

    const save = useMutation({
        mutationFn: (patch: Partial<PlayerSettings>) => playerApi.updateSettings(patch),
        onSuccess: (updated) => {
            qc.setQueryData(["player-settings"], updated);
            setMsg({ text: "Paramètre enregistré.", ok: true });
        },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    if (isLoading || !data) return <p className="text-white/40 text-sm">Chargement...</p>;

    return (
        <div className="space-y-4">
            <div className="bg-game-surface rounded-2xl border border-white/10 p-4">
                <div className="flex items-center justify-between gap-3">
                    <div>
                        <h3 className="text-white font-bold text-sm">Demandes d'ami</h3>
                        <p className="text-white/40 text-xs mt-0.5">
                            Autoriser les autres joueurs à t'envoyer une demande d'ami.
                        </p>
                    </div>
                    <Toggle
                        checked={data.allow_friend_requests}
                        onChange={(v) => save.mutate({ allow_friend_requests: v })}
                    />
                </div>
            </div>

            <div className="bg-game-surface rounded-2xl border border-white/10 p-4">
                <h3 className="text-white font-bold text-sm mb-1">Demandes d'échange</h3>
                <p className="text-white/40 text-xs mb-3">
                    Qui peut te proposer un échange (bouton "Proposer un échange" ou carte à
                    échanger listée en mode "Proposition").
                </p>
                <select
                    className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                    value={data.trade_request_policy}
                    onChange={(e) => save.mutate({ trade_request_policy: e.target.value as TradeRequestPolicy })}
                >
                    {POLICY_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                </select>
            </div>

            <div className="bg-game-surface rounded-2xl border border-white/10 p-4">
                <h3 className="text-white font-bold text-sm mb-1">Cadeaux</h3>
                <p className="text-white/40 text-xs mb-3">
                    Qui peut t'envoyer un cadeau (carte ou ressource) depuis la messagerie.
                </p>
                <select
                    className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                    value={data.gift_policy}
                    onChange={(e) => save.mutate({ gift_policy: e.target.value as GiftPolicy })}
                >
                    {POLICY_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                </select>
            </div>

            <div className="bg-game-surface rounded-2xl border border-white/10 p-4">
                <div className="flex items-center justify-between gap-3">
                    <div>
                        <h3 className="text-white font-bold text-sm">Popup de notification</h3>
                        <p className="text-white/40 text-xs mt-0.5">
                            Afficher une popup quand tu reçois une nouvelle demande d'échange.
                            Si désactivé, elle reste visible dans le panneau Amis.
                        </p>
                    </div>
                    <Toggle
                        checked={data.trade_request_popup_enabled}
                        onChange={(v) => save.mutate({ trade_request_popup_enabled: v })}
                    />
                </div>
            </div>

            {msg && (
                <p className={`text-xs ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>
            )}

            <div className="bg-game-surface rounded-2xl border border-white/10 p-4">
                <Button variant="secondary" size="sm" className="w-full" onClick={() => { logout(); navigate("/login"); }}>
                    Déconnexion
                </Button>
            </div>

            <div className="bg-game-surface rounded-2xl border border-red-500/30 p-4">
                <h3 className="text-white font-bold text-sm mb-1">Zone dangereuse</h3>
                <p className="text-white/40 text-xs mb-3">
                    Supprime définitivement ton compte et toutes tes données. Cette action est irréversible.
                </p>
                <Button variant="danger" size="sm" onClick={() => setDeleteOpen(true)}>
                    Supprimer mon compte
                </Button>
            </div>

            {deleteOpen && (
                <DeleteAccountModal
                    onClose={() => setDeleteOpen(false)}
                    onDeleted={() => {
                        logout();
                        navigate("/login");
                    }}
                />
            )}
        </div>
    );
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { playerApi } from "@/api/player";
import { messagesApi } from "@/api/messages";
import { useAuthStore } from "@/stores/authStore";
import { useLogout } from "@/hooks/useAuth";
import Button from "@/components/ui/Button";
import CoinDisplay from "@/components/player/CoinDisplay";
import ResourceDisplay from "@/components/player/ResourceDisplay";
import ShowcaseEditor from "@/components/profile/ShowcaseEditor";
import TradeListingsEditor from "@/components/profile/TradeListingsEditor";
import SettingsEditor from "@/components/profile/SettingsEditor";
import MessagesInbox from "@/components/profile/MessagesInbox";

function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof r?.data?.detail === "string") return r.data.detail;
    }
    return "Erreur.";
}

function fmtDate(iso: string | null | undefined): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
}

type Tab = "stats" | "profile" | "showcase" | "messages" | "settings";

export default function Profile() {
    const navigate = useNavigate();
    const { user, setUser } = useAuthStore();
    const logout = useLogout();
    const qc = useQueryClient();
    const [tab, setTab] = useState<Tab>("stats");

    const { data: unreadCount } = useQuery({
        queryKey: ["messages-unread-count"],
        queryFn: messagesApi.unreadCount,
        staleTime: 20_000,
        refetchInterval: 30_000,
    });

    const [displayName, setDisplayName] = useState(user?.display_name ?? "");
    const [nameMsg, setNameMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const [currentPwd, setCurrentPwd] = useState("");
    const [newPwd, setNewPwd] = useState("");
    const [confirmPwd, setConfirmPwd] = useState("");
    const [pwdMsg, setPwdMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const updateName = useMutation({
        mutationFn: () => playerApi.updateProfile(displayName.trim()),
        onSuccess: (player) => {
            setUser(player);
            qc.invalidateQueries({ queryKey: ["player"] });
            setNameMsg({ text: "Nom mis à jour.", ok: true });
        },
        onError: (e) => setNameMsg({ text: errMsg(e), ok: false }),
    });

    const changePwd = useMutation({
        mutationFn: () => playerApi.changePassword(currentPwd, newPwd),
        onSuccess: () => {
            setPwdMsg({ text: "Mot de passe changé. Reconnexion...", ok: true });
            setTimeout(() => {
                logout();
                navigate("/login");
            }, 1200);
        },
        onError: (e) => setPwdMsg({ text: errMsg(e), ok: false }),
    });

    const handlePwdSubmit = () => {
        setPwdMsg(null);
        if (newPwd.length < 4) {
            setPwdMsg({ text: "Le nouveau mot de passe doit faire au moins 4 caractères.", ok: false });
            return;
        }
        if (newPwd !== confirmPwd) {
            setPwdMsg({ text: "Les deux mots de passe ne correspondent pas.", ok: false });
            return;
        }
        changePwd.mutate();
    };

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate("/")}>
                    ← Retour
                </button>
                <h1 className="text-white font-bold">👤 Profil</h1>
                <span className="w-14" />
            </header>

            <div className="flex border-b border-white/5 overflow-x-auto no-scrollbar">
                {([
                    { key: "stats", label: "Statistiques" },
                    { key: "profile", label: "Profil" },
                    { key: "showcase", label: "Vitrine" },
                    { key: "messages", label: "Messages" },
                    { key: "settings", label: "Paramètres" },
                ] as const).map((t) => (
                    <button
                        key={t.key}
                        className={`relative flex-1 py-2.5 text-sm font-semibold transition-colors whitespace-nowrap px-2 ${
                            tab === t.key ? "text-accent border-b-2 border-accent" : "text-white/40 hover:text-white/70"
                        }`}
                        onClick={() => setTab(t.key)}
                    >
                        {t.label}
                        {t.key === "messages" && !!unreadCount && (
                            <span className="ml-1.5 inline-flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4 align-middle">
                                {unreadCount}
                            </span>
                        )}
                    </button>
                ))}
            </div>

            <main className="flex-1 px-4 py-6 max-w-sm mx-auto w-full">
                {tab === "stats" && (
                    <div className="space-y-4">
                        <div className="flex items-center gap-2">
                            <CoinDisplay coins={user?.coins ?? 0} />
                            {(user?.resources ?? []).map((r) => (
                                <ResourceDisplay key={r.id} amount={r.amount} label={r.name} />
                            ))}
                        </div>

                        <div className="bg-game-surface rounded-2xl border border-white/10 divide-y divide-white/5">
                            {[
                                ["Pseudo", user?.username ?? "—"],
                                ["Nom affiché", user?.display_name ?? "—"],
                                ["Packs ouverts", String(user?.packs_opened ?? 0)],
                                ["Cartes possédées (total)", String(user?.total_cards ?? 0)],
                                ["Série de connexion", `${user?.login_streak ?? 0} jour(s)`],
                                ["Membre depuis", fmtDate(user?.created_at)],
                                ["Dernière connexion", fmtDate(user?.last_login)],
                            ].map(([label, value]) => (
                                <div key={label} className="flex items-center justify-between px-4 py-3">
                                    <span className="text-white/50 text-sm">{label}</span>
                                    <span className="text-white text-sm font-semibold">{value}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {tab === "profile" && (
                    <div className="space-y-6">
                        <div className="bg-game-surface rounded-2xl border border-white/10 p-4">
                            <h3 className="text-white font-bold text-sm mb-3">Nom affiché</h3>
                            <div className="flex gap-2">
                                <input
                                    className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                                    value={displayName}
                                    maxLength={20}
                                    onChange={(e) => { setDisplayName(e.target.value); setNameMsg(null); }}
                                />
                                <Button
                                    variant="primary" size="sm"
                                    disabled={!displayName.trim() || displayName.trim() === user?.display_name}
                                    loading={updateName.isPending}
                                    onClick={() => updateName.mutate()}
                                >
                                    Enregistrer
                                </Button>
                            </div>
                            {nameMsg && (
                                <p className={`text-xs mt-2 ${nameMsg.ok ? "text-green-400" : "text-red-400"}`}>
                                    {nameMsg.text}
                                </p>
                            )}
                        </div>

                        <div className="bg-game-surface rounded-2xl border border-white/10 p-4">
                            <h3 className="text-white font-bold text-sm mb-3">Changer le mot de passe</h3>
                            <div className="space-y-2">
                                <input
                                    type="password"
                                    className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                                    placeholder="Mot de passe actuel"
                                    value={currentPwd}
                                    onChange={(e) => { setCurrentPwd(e.target.value); setPwdMsg(null); }}
                                />
                                <input
                                    type="password"
                                    className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                                    placeholder="Nouveau mot de passe"
                                    value={newPwd}
                                    onChange={(e) => { setNewPwd(e.target.value); setPwdMsg(null); }}
                                />
                                <input
                                    type="password"
                                    className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                                    placeholder="Confirmer le nouveau mot de passe"
                                    value={confirmPwd}
                                    onChange={(e) => { setConfirmPwd(e.target.value); setPwdMsg(null); }}
                                />
                                <Button
                                    variant="primary" size="sm" className="w-full"
                                    disabled={!currentPwd || !newPwd || !confirmPwd}
                                    loading={changePwd.isPending}
                                    onClick={handlePwdSubmit}
                                >
                                    Changer le mot de passe
                                </Button>
                            </div>
                            {pwdMsg && (
                                <p className={`text-xs mt-2 ${pwdMsg.ok ? "text-green-400" : "text-red-400"}`}>
                                    {pwdMsg.text}
                                </p>
                            )}
                            <p className="text-white/30 text-xs mt-3">
                                Changer le mot de passe te déconnecte de toutes tes sessions — tu devras te reconnecter.
                            </p>
                        </div>
                    </div>
                )}

                {tab === "showcase" && (
                    <div className="space-y-6">
                        <ShowcaseEditor />
                        <TradeListingsEditor />
                    </div>
                )}

                {tab === "messages" && <MessagesInbox />}

                {tab === "settings" && <SettingsEditor />}
            </main>
        </div>
    );
}

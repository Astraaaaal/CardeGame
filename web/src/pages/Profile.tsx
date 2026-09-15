import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import CoinDisplay from "@/components/player/CoinDisplay";
import ResourceDisplay from "@/components/player/ResourceDisplay";
import ShowcaseEditor from "@/components/profile/ShowcaseEditor";
import TradeListingsEditor from "@/components/profile/TradeListingsEditor";

function fmtDate(iso: string | null | undefined): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
}

type Tab = "stats" | "showcase";

export default function Profile() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    // Si on revient d'une sélection de carte pour un slot de vitrine (cf.
    // ShowcaseEditor) ou un slot "à échanger" (cf. TradeListingsEditor),
    // rouvre directement cet onglet plutôt que de perdre le contexte.
    const [tab, setTab] = useState<Tab>(() => {
        const purpose = useCardSelectionStore.getState().result?.context?.purpose;
        return purpose === "showcase-slot" || purpose === "trade-listing-slot" ? "showcase" : "stats";
    });

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate("/")}>
                    Retour
                </button>
                <h1 className="text-white font-bold">Profil</h1>
                <span className="w-14" />
            </header>

            <div className="flex border-b border-white/5">
                {([
                    { key: "stats", label: "Statistiques" },
                    { key: "showcase", label: "Vitrine" },
                ] as const).map((t) => (
                    <button
                        key={t.key}
                        className={`flex-1 py-2.5 text-sm font-semibold transition-colors ${
                            tab === t.key ? "text-accent border-b-2 border-accent" : "text-white/40 hover:text-white/70"
                        }`}
                        onClick={() => setTab(t.key)}
                    >
                        {t.label}
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

                {tab === "showcase" && (
                    <div className="space-y-6">
                        <ShowcaseEditor />
                        <TradeListingsEditor />
                    </div>
                )}
            </main>
        </div>
    );
}

import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import { playerApi } from "@/api/player";
import type { PlayerStats } from "@/types/player";
import type { Card } from "@/types/card";
import ShowcaseEditor, { type EditorSaveHandle } from "@/components/profile/ShowcaseEditor";
import TradeListingsEditor from "@/components/profile/TradeListingsEditor";
import CardImage from "@/components/card/CardImage";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import BottomNav from "@/components/layout/BottomNav";
import { errMsg } from "@/utils/errors";

function fmtDate(iso: string | null | undefined): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
}

function StatSection({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div>
            <h3 className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-2">{title}</h3>
            <div className="bg-game-surface rounded-2xl border border-white/10 divide-y divide-white/5">
                {children}
            </div>
        </div>
    );
}

function StatRow({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex items-center justify-between px-4 py-3">
            <span className="text-white/50 text-sm">{label}</span>
            <span className="text-white text-sm font-semibold">{value}</span>
        </div>
    );
}

function CardHighlight({ label, card, caption }: { label: string; card: Card; caption: string }) {
    return (
        <div className="flex items-center gap-3 px-4 py-3">
            <div className="w-12 shrink-0">
                <CardImage card={card} size="sm" />
            </div>
            <div className="min-w-0">
                <p className="text-white/50 text-xs">{label}</p>
                <p className="text-white text-sm font-semibold truncate">{card.character_name}</p>
                <p className="text-white/40 text-xs">{caption}</p>
            </div>
        </div>
    );
}

function StatsTab({ stats, isLoading }: { stats: PlayerStats | undefined; isLoading: boolean }) {
    const { user } = useAuthStore();

    if (isLoading || !stats) return <LoadingSpinner text="Chargement..." />;

    return (
        <div className="space-y-5">
            <StatSection title="Identité">
                <StatRow label="Pseudo" value={user?.username ?? "—"} />
                <StatRow label="Nom affiché" value={user?.display_name ?? "—"} />
                <StatRow label="Membre depuis" value={fmtDate(user?.created_at)} />
                <StatRow label="Dernière connexion" value={fmtDate(user?.last_login)} />
            </StatSection>

            <StatSection title="Collection">
                <StatRow label="Cartes possédées (total)" value={stats.total_cards.toLocaleString("fr-FR")} />
                <StatRow label="Cartes uniques" value={stats.unique_cards.toLocaleString("fr-FR")} />
                <StatRow label="Packs ouverts" value={stats.packs_opened.toLocaleString("fr-FR")} />
                <StatRow label="Cartes recyclées" value={stats.cards_recycled.toLocaleString("fr-FR")} />
            </StatSection>

            <StatSection title="Puissance">
                <StatRow label="Puissance totale" value={stats.total_power.toLocaleString("fr-FR")} />
                <StatRow label="Puissance moyenne" value={stats.average_power.toLocaleString("fr-FR")} />
                {stats.highest_power_card && (
                    <CardHighlight
                        label="Ta carte la plus puissante"
                        card={stats.highest_power_card}
                        caption={`${stats.highest_power_card.power?.toLocaleString("fr-FR")} de puissance`}
                    />
                )}
            </StatSection>

            {stats.luckiest_card && (
                <StatSection title="Chance">
                    <CardHighlight
                        label="Ta pépite (le tirage le plus improbable)"
                        card={stats.luckiest_card}
                        caption={
                            stats.luckiest_card.combined_rarity
                                ? `1 chance sur ${stats.luckiest_card.combined_rarity.toLocaleString("fr-FR")}`
                                : "—"
                        }
                    />
                </StatSection>
            )}

            <StatSection title="Progression">
                <StatRow label="Niveau actuel" value={String(stats.current_level)} />
                <StatRow label="Achievements débloqués" value={`${stats.achievements_unlocked} / ${stats.achievements_total}`} />
                <StatRow label="Série de connexion" value={`${stats.login_streak} jour(s)`} />
            </StatSection>

            <StatSection title="Social">
                <StatRow label="Amis" value={String(stats.friends_count)} />
                <StatRow label="Échanges conclus" value={String(stats.trades_completed)} />
                <StatRow label="Cadeaux envoyés" value={String(stats.gifts_sent)} />
                <StatRow label="Cadeaux reçus" value={String(stats.gifts_received)} />
            </StatSection>

            <StatSection title="Le petit coin fun">
                {stats.favorite_type_name && (
                    <StatRow
                        label="Type favori"
                        value={`${stats.favorite_type_name} (${stats.favorite_type_count} carte${stats.favorite_type_count > 1 ? "s" : ""})`}
                    />
                )}
                {stats.most_duplicated_card && (
                    <CardHighlight
                        label="Ton plus gros doublon"
                        card={stats.most_duplicated_card}
                        caption={`possédée ${stats.most_duplicated_count} fois`}
                    />
                )}
                {stats.oldest_card && (
                    <CardHighlight
                        label="Ta doyenne"
                        card={stats.oldest_card}
                        caption={`avec toi depuis le ${fmtDate(stats.oldest_card.obtained_at)}`}
                    />
                )}
            </StatSection>
        </div>
    );
}

type Tab = "stats" | "showcase";

export default function Profile() {
    const navigate = useNavigate();
    // Si on revient d'une sélection de carte pour un slot de vitrine (cf.
    // ShowcaseEditor) ou un slot "à échanger" (cf. TradeListingsEditor),
    // rouvre directement cet onglet plutôt que de perdre le contexte.
    const [tab, setTab] = useState<Tab>(() => {
        const purpose = useCardSelectionStore.getState().result?.context?.purpose;
        return purpose === "showcase-slot" || purpose === "trade-listing-slot" ? "showcase" : "stats";
    });

    const { user } = useAuthStore();
    const { data: stats, isLoading } = useQuery({
        queryKey: ["player-stats"], queryFn: playerApi.getStats, enabled: tab === "stats",
    });

    const showcaseRef = useRef<EditorSaveHandle>(null);
    const listingsRef = useRef<EditorSaveHandle>(null);
    const [saving, setSaving] = useState(false);
    const [saveMsg, setSaveMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const saveShowcase = async () => {
        setSaving(true);
        setSaveMsg(null);
        try {
            await Promise.all([showcaseRef.current?.save(), listingsRef.current?.save()]);
            setSaveMsg({ text: "Vitrine enregistrée.", ok: true });
        } catch (e) {
            setSaveMsg({ text: errMsg(e), ok: false });
        } finally {
            setSaving(false);
        }
    };

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
                {tab === "stats" && <StatsTab stats={stats} isLoading={isLoading} />}

                {tab === "showcase" && (
                    <div className="space-y-6">
                        <ShowcaseEditor ref={showcaseRef} />
                        <TradeListingsEditor ref={listingsRef} />

                        <div className="space-y-2">
                            {saveMsg && (
                                <p className={`text-xs ${saveMsg.ok ? "text-green-400" : "text-red-400"}`}>{saveMsg.text}</p>
                            )}
                            <div className="flex items-center gap-2">
                                <Button variant="primary" className="flex-1" loading={saving} onClick={saveShowcase}>
                                    Enregistrer
                                </Button>
                                <button
                                    className="w-11 h-11 shrink-0 rounded-full border border-white/15 bg-game-surface
                                               text-white/60 hover:text-white hover:border-accent transition-colors
                                               flex items-center justify-center"
                                    title="Voir comme un autre joueur"
                                    aria-label="Voir comme un autre joueur"
                                    onClick={() => user && navigate(`/players/${user.id}`)}
                                >
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" />
                                        <circle cx="12" cy="12" r="3" />
                                    </svg>
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </main>

            <BottomNav />
        </div>
    );
}

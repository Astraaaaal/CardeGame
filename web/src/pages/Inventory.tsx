import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { boostersApi } from "@/api/boosters";
import { useAuthStore } from "@/stores/authStore";
import { useOpenOwnedBoosters } from "@/hooks/usePackOpening";
import { useHasPendingTradeProposal } from "@/hooks/useTradePulse";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ResourceIcon from "@/components/ui/ResourceIcon";
import BottomNav from "@/components/layout/BottomNav";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <section>
            <h2 className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-2">{title}</h2>
            <div className="space-y-2">{children}</div>
        </section>
    );
}

/** Tout ce que le joueur possède en dehors des cartes (ressources, boosters à ouvrir...). */
export default function Inventory() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const tradePending = useHasPendingTradeProposal();
    const openOwned = useOpenOwnedBoosters();
    const { data: boosters, isLoading } = useQuery({ queryKey: ["booster-inventory"], queryFn: boostersApi.getInventory });

    const resources = [
        { id: "coins", name: "Pièces", amount: user?.coins ?? 0 },
        ...(user?.resources ?? []).filter((r) => r.id !== "coins" && r.amount > 0),
    ];

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate("/")}>
                    Retour
                </button>
                <h1 className="text-white font-bold">Inventaire</h1>
                <span className="w-14" />
            </header>

            <main className="flex-1 px-4 py-6 max-w-sm mx-auto w-full space-y-6">
                <Section title="Ressources">
                    {resources.map((r) => (
                        <div key={r.id} className="flex items-center gap-3 bg-game-surface border border-white/10 rounded-xl px-4 py-3">
                            <ResourceIcon resourceId={r.id} className="w-6 h-6" />
                            <span className="flex-1 text-white text-sm">{r.name}</span>
                            <span className="text-white font-bold tabular-nums">{r.amount.toLocaleString("fr-FR")}</span>
                        </div>
                    ))}
                </Section>

                <Section title="Boosters à ouvrir">
                    {isLoading ? (
                        <LoadingSpinner text="Chargement..." />
                    ) : !boosters?.length ? (
                        <p className="text-white/30 text-sm">Aucun booster en attente.</p>
                    ) : (
                        <>
                            {tradePending && (
                                <p className="text-amber-300/80 text-xs">
                                    Ouverture indisponible tant qu'une proposition d'échange attend une réponse.
                                </p>
                            )}
                            {boosters.map((b) => (
                                <div key={b.booster_id} className="flex items-center gap-3 bg-gold/10 border border-gold/30 rounded-xl px-4 py-3">
                                    <span className="text-xl">🎴</span>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-white text-sm font-semibold truncate">{b.booster_name}</p>
                                        <p className="text-white/40 text-xs">×{b.quantity}</p>
                                    </div>
                                    <Button
                                        variant="gold" size="sm"
                                        disabled={tradePending}
                                        loading={openOwned.isPending && openOwned.variables?.booster_id === b.booster_id}
                                        onClick={() => openOwned.mutate(
                                            { booster_id: b.booster_id, quantity: b.quantity },
                                            { onSuccess: () => navigate("/opening") },
                                        )}
                                    >
                                        Ouvrir
                                    </Button>
                                </div>
                            ))}
                        </>
                    )}
                </Section>
            </main>

            <BottomNav />
        </div>
    );
}

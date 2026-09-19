import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { boostersApi } from "@/api/boosters";
import { useAuthStore } from "@/stores/authStore";
import OwnedBoosterRow from "@/components/shop/OwnedBoosterRow";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ResourceIcon from "@/components/ui/ResourceIcon";
import BottomNav from "@/components/layout/BottomNav";
import { premiumApi } from "@/api/premium";
import { CosmeticPreview, COSMETIC_KIND_LABEL } from "@/components/cosmetics/CosmeticVisuals";
import { useRerollTokens, useRerollTokenUse } from "@/hooks/useRerollTokens";

const AXIS_LABEL: Record<string, string> = { rarity: "rareté", quality: "qualité", specialty: "spécialité", jewelry: "bijou" };

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
    const { data: boosters, isLoading } = useQuery({ queryKey: ["booster-inventory"], queryFn: boostersApi.getInventory });
    const { data: cosmetics } = useQuery({ queryKey: ["my-cosmetics"], queryFn: premiumApi.myCosmetics });
    const { data: rerollTokens } = useRerollTokens();
    const [rerollError, setRerollError] = useState("");
    const rerollToken = useRerollTokenUse("/inventory", setRerollError);
    const equippedIds = [cosmetics?.equipped_avatar_frame_id, cosmetics?.equipped_showcase_background_id];

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
                            {/* Les ressources se dépensent dans la boutique : pièces → boosters, le reste → offres à ressources. */}
                            <Button variant="gold" size="sm" onClick={() => navigate(r.id === "coins" ? "/shop" : "/shop?tab=resources")}>
                                Utiliser
                            </Button>
                        </div>
                    ))}
                </Section>

                <Section title="Boosters à ouvrir">
                    {isLoading ? (
                        <LoadingSpinner text="Chargement..." />
                    ) : !boosters?.length ? (
                        <p className="text-white/30 text-sm">Aucun booster en attente.</p>
                    ) : (
                        boosters.map((b) => (
                            <OwnedBoosterRow key={`${b.booster_id}-${b.bonus_id ?? "base"}`} owned={b} showName />
                        ))
                    )}
                </Section>

                {!!rerollTokens?.length && (
                    <Section title="Rerolls">
                        {rerollError && <p className="text-red-400 text-xs">{rerollError}</p>}
                        {rerollTokens.map((t) => (
                            <div key={t.id} className="flex items-center gap-3 bg-accent/10 border border-accent/30 rounded-xl px-4 py-3">
                                <span className="text-xl">🎲</span>
                                <div className="flex-1 min-w-0">
                                    <p className="text-white text-sm font-semibold truncate">{t.label}</p>
                                    <p className="text-white/50 text-xs truncate">
                                        {[...t.axes.map((a) => AXIS_LABEL[a]), ...(t.reroll_power ? ["puissance"] : [])].join(" + ")}
                                        {" — "}{t.reroll_mode === "guaranteed_min" ? "garanti égal ou mieux" : "aléatoire"}
                                    </p>
                                    <p className="text-white/40 text-xs">×{t.quantity}</p>
                                </div>
                                <Button
                                    variant="gold" size="sm"
                                    loading={rerollToken.pendingTokenId === t.id}
                                    onClick={() => { setRerollError(""); rerollToken.start(t.id); }}
                                >
                                    Utiliser
                                </Button>
                            </div>
                        ))}
                    </Section>
                )}

                {!!cosmetics?.owned.length && (
                    <Section title="Cosmétiques">
                        {cosmetics.owned.map((c) => (
                            <div key={c.id} className="flex items-center gap-3 bg-game-surface border border-white/10 rounded-xl px-4 py-3">
                                <CosmeticPreview cosmetic={c} size={40} />
                                <div className="flex-1 min-w-0">
                                    <p className="text-white text-sm font-semibold truncate">{c.name}</p>
                                    <p className="text-white/40 text-xs">{COSMETIC_KIND_LABEL[c.kind]}</p>
                                </div>
                                {equippedIds.includes(c.id) ? (
                                    <span className="text-green-400 text-xs shrink-0">Équipé</span>
                                ) : (
                                    <button className="text-accent text-xs shrink-0" onClick={() => navigate("/profile")}>Équiper</button>
                                )}
                            </div>
                        ))}
                    </Section>
                )}
            </main>

            <BottomNav />
        </div>
    );
}

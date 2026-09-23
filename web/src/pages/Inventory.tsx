import { useState } from "react";
import { RerollIcon } from "@/components/ui/ItemIcon";
import { toast } from "@/stores/toastStore";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { boostersApi } from "@/api/boosters";
import { useAuthStore } from "@/stores/authStore";
import OwnedBoosterRow from "@/components/shop/OwnedBoosterRow";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ResourceIcon from "@/components/ui/ResourceIcon";
import SocialButton from "@/components/layout/SocialButton";
import { premiumApi } from "@/api/premium";
import { CosmeticPreview, COSMETIC_KIND_LABEL } from "@/components/cosmetics/CosmeticVisuals";
import { useRerollTokens, useRerollTokenUse } from "@/hooks/useRerollTokens";

const AXIS_LABEL: Record<string, string> = { rarity: "rareté", quality: "qualité", specialty: "spécialité", jewelry: "bijou" };

type Tab = "resources" | "boosters" | "rerolls" | "cosmetics";
type Sort = "quantity" | "name" | "recent";
const SORT_LABEL: Record<Sort, string> = { quantity: "Quantité", name: "Nom", recent: "Récent" };
const TAB_SORTS: Record<Tab, Sort[]> = {
    resources: ["quantity", "name"],
    boosters: ["quantity", "name", "recent"],
    rerolls: ["quantity", "name", "recent"],
    cosmetics: ["name", "recent"],
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <section>
            <h2 className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-2">{title}</h2>
            <div className="space-y-2">{children}</div>
        </section>
    );
}

/** Tri générique : quantité décroissante, nom alphabétique, ou plus récent (ordre d'arrivée inversé). */
function sortItems<T>(items: T[], sort: Sort, get: { qty?: (x: T) => number; name: (x: T) => string }): T[] {
    const list = [...items];
    if (sort === "recent") return list.reverse();
    if (sort === "quantity" && get.qty) return list.sort((a, b) => get.qty!(b) - get.qty!(a) || get.name(a).localeCompare(get.name(b)));
    return list.sort((a, b) => get.name(a).localeCompare(get.name(b)));
}

function readStored<T extends string>(key: string, fallback: T): T {
    try { return (sessionStorage.getItem(key) as T | null) ?? fallback; } catch { return fallback; }
}

/** Tout ce que le joueur possède en dehors des cartes (ressources, boosters à ouvrir...). */
export default function Inventory() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const { data: boosters, isLoading } = useQuery({ queryKey: ["booster-inventory"], queryFn: boostersApi.getInventory });
    const { data: cosmetics } = useQuery({ queryKey: ["my-cosmetics"], queryFn: premiumApi.myCosmetics });
    const { data: rerollTokens } = useRerollTokens();
    const setRerollError = (m: string | null) => { if (m) toast.error(m); };
    const rerollToken = useRerollTokenUse("/inventory", setRerollError);
    const equippedIds = [cosmetics?.equipped_avatar_frame_id, cosmetics?.equipped_showcase_background_id];

    const [tab, setTabState] = useState<Tab>(() => readStored("inventory-tab", "resources"));
    const [sorts, setSorts] = useState<Record<Tab, Sort>>(() => {
        try { return { ...{ resources: "quantity", boosters: "quantity", rerolls: "quantity", cosmetics: "name" }, ...JSON.parse(sessionStorage.getItem("inventory-sorts") ?? "{}") }; }
        catch { return { resources: "quantity", boosters: "quantity", rerolls: "quantity", cosmetics: "name" }; }
    });
    const setTab = (t: Tab) => { setTabState(t); try { sessionStorage.setItem("inventory-tab", t); } catch { /* indisponible */ } };
    const setSort = (s: Sort) => {
        const next = { ...sorts, [tab]: s };
        setSorts(next);
        try { sessionStorage.setItem("inventory-sorts", JSON.stringify(next)); } catch { /* indisponible */ }
    };
    const sort = sorts[tab];

    const resources = [
        { id: "coins", name: "Pièces", amount: user?.coins ?? 0 },
        ...(user?.resources ?? []).filter((r) => r.id !== "coins" && r.amount > 0),
    ];

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="relative flex items-center justify-between pl-4 pr-14 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate("/")}>
                    Retour
                </button>
                <h1 className="absolute left-1/2 -translate-x-1/2 max-w-[55%] truncate text-white font-bold pointer-events-none">Inventaire</h1>
                <span className="w-14" />
            </header>

            <div className="flex border-b border-white/5">
                {([
                    ["resources", "Ressources", resources.length],
                    ["boosters", "Boosters", boosters?.reduce((n, b) => n + b.quantity, 0) ?? 0],
                    ["rerolls", "Rerolls", rerollTokens?.reduce((n, t) => n + t.quantity, 0) ?? 0],
                    ["cosmetics", "Cosmétiques", cosmetics?.owned.length ?? 0],
                ] as [Tab, string, number][]).map(([key, label, count]) => (
                    <button key={key}
                        className={`flex-1 min-w-0 px-1 py-2.5 text-xs font-semibold truncate transition-colors ${tab === key ? "text-accent border-b-2 border-accent" : "text-white/40 hover:text-white/70"}`}
                        onClick={() => setTab(key)}>
                        {label}{count ? <span className="ml-1 text-white/30">{count}</span> : null}
                    </button>
                ))}
            </div>

            <main className="flex-1 px-4 py-4 max-w-sm mx-auto w-full space-y-4">
                <div className="flex items-center gap-1.5 text-[11px] text-white/40">
                    Trier par
                    {TAB_SORTS[tab].map((s) => (
                        <button key={s}
                            className={`px-2.5 py-0.5 rounded-full font-bold ${sort === s ? "bg-accent text-white" : "bg-white/10 text-white/60"}`}
                            onClick={() => setSort(s)}>{SORT_LABEL[s]}</button>
                    ))}
                </div>

                {tab === "resources" && <Section title="Ressources">
                    {sortItems(resources, sort, { qty: (r) => r.amount, name: (r) => r.name }).map((r) => (
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
                </Section>}

                {tab === "boosters" && <Section title="Boosters à ouvrir">
                    {isLoading ? (
                        <LoadingSpinner text="Chargement..." />
                    ) : !boosters?.length ? (
                        <p className="text-white/30 text-sm">Aucun booster en attente.</p>
                    ) : (
                        sortItems(boosters, sort, { qty: (b) => b.quantity, name: (b) => `${b.booster_name} ${b.bonus_label ?? ""}` }).map((b) => (
                            <OwnedBoosterRow key={`${b.booster_id}-${b.bonus_id ?? "base"}`} owned={b} showName />
                        ))
                    )}
                </Section>}

                {tab === "rerolls" && (
                    <Section title="Rerolls">
                        {!rerollTokens?.length && <p className="text-white/30 text-sm">Aucun reroll en stock.</p>}
                        {sortItems(rerollTokens ?? [], sort, { qty: (t) => t.quantity, name: (t) => t.label }).map((t) => (
                            <div key={t.id} className="flex items-center gap-3 bg-accent/10 border border-accent/30 rounded-xl px-4 py-3">
                                <RerollIcon className="w-6 h-6 text-white/80" />
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

                {tab === "cosmetics" && (
                    <Section title="Cosmétiques">
                        {!cosmetics?.owned.length && <p className="text-white/30 text-sm">Aucun cosmétique pour l'instant.</p>}
                        {sortItems(cosmetics?.owned ?? [], sort, { name: (c) => c.name }).map((c) => (
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

            <SocialButton />
        </div>
    );
}

import { parseUtc } from "@/utils/format";
import { inputCls, labelCls } from "@/components/ui/formStyles";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi, adminPremiumApi, type PremiumProductInput } from "@/api/admin";
import type { Cosmetic, CosmeticAnimation, CosmeticKind, Grant, PremiumProduct } from "@/types/premium";
import { formatEuros } from "@/types/premium";
import Button from "@/components/ui/Button";
import LimitFields from "./LimitFields";
import { LIMIT_PERIOD_LABEL } from "@/utils/purchaseLimits";
import Modal from "@/components/ui/Modal";
import Toggle from "@/components/ui/Toggle";
import { CosmeticPreview, COSMETIC_KIND_LABEL } from "@/components/cosmetics/CosmeticVisuals";
import { errMsg } from "@/utils/errors";


const ANIMATIONS: { value: CosmeticAnimation; label: string }[] = [
    { value: "none", label: "Aucune" },
    { value: "shine", label: "Brillance (rotation)" },
    { value: "pulse", label: "Pulsation" },
    { value: "rainbow", label: "Arc-en-ciel" },
];

const STATUS_LABEL: Record<string, string> = {
    pending: "En attente", paid: "Payée", failed: "Échouée", refunded: "Remboursée",
};

function Section({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
    return (
        <section className="space-y-2">
            <div className="flex items-center justify-between">
                <h2 className="text-white/60 text-xs font-semibold uppercase tracking-wide">{title}</h2>
                {action}
            </div>
            {children}
        </section>
    );
}

/* ── Ouverture de la boutique + état des services externes ── */
function ConfigSection() {
    const qc = useQueryClient();
    const { data } = useQuery({ queryKey: ["admin", "premium-config"], queryFn: adminPremiumApi.getConfig });
    const [testers, setTesters] = useState("");
    const [msg, setMsg] = useState("");
    useEffect(() => { if (data) setTesters(data.premium_testers); }, [data]);

    const save = useMutation({
        mutationFn: adminPremiumApi.updateConfig,
        onSuccess: (c) => { qc.setQueryData(["admin", "premium-config"], c); setMsg("Enregistré."); },
        onError: (e) => setMsg(errMsg(e)),
    });

    if (!data) return null;
    return (
        <Section title="Ouverture">
            <div className="bg-game-surface/60 border border-white/5 rounded-lg p-3 space-y-3">
                <div className="flex items-center justify-between gap-3">
                    <div>
                        <p className="text-white text-sm font-semibold">Boutique premium ouverte à tous</p>
                        <p className="text-white/40 text-xs">Fermée : onglet invisible et achats refusés, sauf pour les testeurs.</p>
                    </div>
                    <Toggle checked={data.premium_shop_enabled} onChange={(v) => save.mutate({ premium_shop_enabled: v })} />
                </div>
                <div>
                    <label className={labelCls}>Testeurs (pseudos séparés par des virgules)</label>
                    <div className="flex gap-2">
                        <input className={inputCls} value={testers} placeholder="ex: alice, bob"
                            onChange={(e) => setTesters(e.target.value)} />
                        <Button variant="primary" size="sm" disabled={testers === data.premium_testers}
                            onClick={() => save.mutate({ premium_testers: testers })}>OK</Button>
                    </div>
                </div>
                <div className="flex gap-4 text-xs">
                    <span className={data.stripe_configured ? "text-green-400" : "text-amber-300"}>
                        {data.stripe_configured ? "✓ Stripe configuré" : "✗ Stripe non configuré (paiements refusés)"}
                    </span>
                    <span className={data.email_configured ? "text-green-400" : "text-amber-300"}>
                        {data.email_configured ? "✓ Brevo configuré" : "✗ Brevo non configuré (e-mails dans les logs)"}
                    </span>
                </div>
                {msg && <p className="text-white/50 text-xs">{msg}</p>}
            </div>
        </Section>
    );
}

/* ── Cosmétiques ── */
function CosmeticForm({ initial, onDone }: { initial: Cosmetic | null; onDone: () => void }) {
    const isNew = !initial;
    const [f, setF] = useState<Cosmetic>(initial ?? {
        id: "", kind: "avatar_frame", name: "", description: "",
        color_from: "#8b5cf6", color_to: "#22d3ee", animation: "none", image_url: "", active: true,
    });
    const [err, setErr] = useState("");
    const m = useMutation({
        mutationFn: () => {
            if (isNew) return adminPremiumApi.createCosmetic(f);
            const { id, kind: _kind, ...rest } = f;
            return adminPremiumApi.updateCosmetic(id, rest);
        },
        onSuccess: onDone,
        onError: (e) => setErr(errMsg(e)),
    });

    return (
        <div className="space-y-3">
            <div className="flex justify-center py-2"><CosmeticPreview cosmetic={f} size={72} /></div>
            <div className="grid grid-cols-2 gap-2">
                <div>
                    <label className={labelCls}>Identifiant</label>
                    <input className={inputCls} value={f.id} disabled={!isNew} placeholder="ex: cadre_aurore"
                        onChange={(e) => setF({ ...f, id: e.target.value })} />
                </div>
                <div>
                    <label className={labelCls}>Type</label>
                    <select className={inputCls} value={f.kind} disabled={!isNew}
                        onChange={(e) => setF({ ...f, kind: e.target.value as CosmeticKind })}>
                        {Object.entries(COSMETIC_KIND_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                    </select>
                </div>
            </div>
            <div>
                <label className={labelCls}>Nom</label>
                <input className={inputCls} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
            </div>
            <div className="grid grid-cols-3 gap-2">
                <div>
                    <label className={labelCls}>Couleur 1</label>
                    <input type="color" className="w-full h-9 bg-transparent" value={f.color_from}
                        onChange={(e) => setF({ ...f, color_from: e.target.value })} />
                </div>
                <div>
                    <label className={labelCls}>Couleur 2</label>
                    <input type="color" className="w-full h-9 bg-transparent" value={f.color_to}
                        onChange={(e) => setF({ ...f, color_to: e.target.value })} />
                </div>
                <div>
                    <label className={labelCls}>Animation</label>
                    <select className={inputCls} value={f.animation}
                        onChange={(e) => setF({ ...f, animation: e.target.value as CosmeticAnimation })}>
                        {ANIMATIONS.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
                    </select>
                </div>
            </div>
            <div>
                <label className={labelCls}>Image (optionnelle, remplace le style) — fichier dans web/public/cosmetics/</label>
                <input className={inputCls} value={f.image_url} placeholder="ex: cadre_aurore.png"
                    onChange={(e) => setF({ ...f, image_url: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>Description</label>
                <textarea className={inputCls} rows={2} value={f.description}
                    onChange={(e) => setF({ ...f, description: e.target.value })} />
            </div>
            <label className="flex items-center gap-2 text-sm text-white/80">
                <input type="checkbox" checked={f.active} onChange={(e) => setF({ ...f, active: e.target.checked })} />
                Actif
            </label>
            {err && <p className="text-red-400 text-xs">{err}</p>}
            <div className="flex gap-2">
                <Button variant="primary" className="flex-1" loading={m.isPending} onClick={() => m.mutate()}>
                    {isNew ? "Créer" : "Enregistrer"}
                </Button>
                <Button variant="secondary" onClick={onDone}>Annuler</Button>
            </div>
        </div>
    );
}

/* ── Produits en euros ── */
function ProductForm({ initial, cosmetics, onDone }: {
    initial: PremiumProduct | null;
    cosmetics: Cosmetic[];
    onDone: () => void;
}) {
    const isNew = !initial;
    const { data: resources } = useQuery({ queryKey: ["admin", "resources"], queryFn: adminApi.listResources });
    const { data: boosters } = useQuery({ queryKey: ["admin", "boosters"], queryFn: adminApi.listBoosters });
    const [f, setF] = useState<PremiumProductInput>(initial
        ? {
            id: initial.id, name: initial.name, description: initial.description, price_cents: initial.price_cents,
            grants: initial.grants.map(({ kind, id, amount }) => ({ kind, id, amount })),
            once_per_account: initial.once_per_account, active: initial.active, sort_order: initial.sort_order,
            limit_period: initial.limit_period, limit_count: initial.limit_count,
        }
        : {
            id: "", name: "", description: "", price_cents: 499,
            grants: [{ kind: "resource", id: "shards", amount: 500 }],
            once_per_account: false, limit_period: "none" as const, limit_count: 1, active: true, sort_order: 0,
        });
    const [err, setErr] = useState("");
    const m = useMutation({
        mutationFn: () => isNew ? adminPremiumApi.createProduct(f) : adminPremiumApi.updateProduct(f.id, f),
        onSuccess: onDone,
        onError: (e) => setErr(errMsg(e)),
    });

    const optionsFor = (kind: Grant["kind"]) =>
        kind === "resource" ? (resources ?? []).map((r) => ({ id: r.id, name: r.name }))
            : kind === "booster" ? (boosters ?? []).map((b) => ({ id: b.id, name: b.name }))
                : cosmetics.map((c) => ({ id: c.id, name: `${c.name} (${COSMETIC_KIND_LABEL[c.kind]})` }));

    const setGrant = (i: number, patch: Partial<Grant>) =>
        setF({ ...f, grants: f.grants.map((g, j) => (j === i ? { ...g, ...patch } : g)) });

    return (
        <div className="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
            <div className="grid grid-cols-2 gap-2">
                <div>
                    <label className={labelCls}>Identifiant</label>
                    <input className={inputCls} value={f.id} disabled={!isNew} placeholder="ex: pack_500_eclats"
                        onChange={(e) => setF({ ...f, id: e.target.value })} />
                </div>
                <div>
                    <label className={labelCls}>Prix (€)</label>
                    <input type="number" step="0.01" min="0.5" className={inputCls} value={f.price_cents / 100}
                        onChange={(e) => setF({ ...f, price_cents: Math.round(+e.target.value * 100) })} />
                </div>
            </div>
            <div>
                <label className={labelCls}>Nom</label>
                <input className={inputCls} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>Contenu du lot</label>
                <div className="space-y-2">
                    {f.grants.map((g, i) => (
                        <div key={i} className="flex gap-1.5">
                            <select className={`${inputCls} w-28`} value={g.kind}
                                onChange={(e) => {
                                    const kind = e.target.value as Grant["kind"];
                                    setGrant(i, { kind, id: optionsFor(kind)[0]?.id ?? "", amount: 1 });
                                }}>
                                <option value="resource">Ressource</option>
                                <option value="booster">Booster</option>
                                <option value="cosmetic">Cosmétique</option>
                            </select>
                            <select className={inputCls} value={g.id} onChange={(e) => setGrant(i, { id: e.target.value })}>
                                {optionsFor(g.kind).map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
                            </select>
                            {g.kind !== "cosmetic" && (
                                <input type="number" min="1" className={`${inputCls} w-20`} value={g.amount}
                                    onChange={(e) => setGrant(i, { amount: Math.max(1, +e.target.value) })} />
                            )}
                            <button className="text-red-400/70 hover:text-red-400 px-1"
                                onClick={() => setF({ ...f, grants: f.grants.filter((_, j) => j !== i) })}>×</button>
                        </div>
                    ))}
                    <button className="text-accent text-xs"
                        onClick={() => setF({ ...f, grants: [...f.grants, { kind: "resource", id: "shards", amount: 100 }] })}>
                        + Ajouter un élément
                    </button>
                </div>
            </div>
            <LimitFields
                period={f.limit_period}
                count={f.limit_count}
                onChange={(limit) => setF({ ...f, ...limit, once_per_account: limit.limit_period === "account" && limit.limit_count === 1 })}
            />
            <div>
                <label className={labelCls}>Description</label>
                <textarea className={inputCls} rows={2} value={f.description}
                    onChange={(e) => setF({ ...f, description: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-2 items-end">
                <div>
                    <label className={labelCls}>Ordre d'affichage</label>
                    <input type="number" className={inputCls} value={f.sort_order}
                        onChange={(e) => setF({ ...f, sort_order: +e.target.value })} />
                </div>
                <div className="space-y-1 pb-1">
                    <label className="flex items-center gap-2 text-sm text-white/80">
                        <input type="checkbox" checked={f.active} onChange={(e) => setF({ ...f, active: e.target.checked })} />
                        Actif
                    </label>
                </div>
            </div>
            {err && <p className="text-red-400 text-xs">{err}</p>}
            <div className="flex gap-2">
                <Button variant="primary" className="flex-1" loading={m.isPending} onClick={() => m.mutate()}>
                    {isNew ? "Créer" : "Enregistrer"}
                </Button>
                <Button variant="secondary" onClick={onDone}>Annuler</Button>
            </div>
        </div>
    );
}

/** Panneau admin de la boutique premium. */
export default function AdminPremium() {
    const qc = useQueryClient();
    const cosmeticsQ = useQuery({ queryKey: ["admin", "cosmetics"], queryFn: adminPremiumApi.listCosmetics });
    const productsQ = useQuery({ queryKey: ["admin", "premium-products"], queryFn: adminPremiumApi.listProducts });
    const ordersQ = useQuery({ queryKey: ["admin", "premium-orders"], queryFn: adminPremiumApi.listOrders });
    const [editingCosmetic, setEditingCosmetic] = useState<Cosmetic | null | undefined>(undefined);
    const [editingProduct, setEditingProduct] = useState<PremiumProduct | null | undefined>(undefined);

    const refresh = () => {
        qc.invalidateQueries({ queryKey: ["admin"] });
        setEditingCosmetic(undefined);
        setEditingProduct(undefined);
    };
    const removeCosmetic = useMutation({ mutationFn: adminPremiumApi.deleteCosmetic, onSuccess: refresh, onError: (e) => alert(errMsg(e)) });
    const removeProduct = useMutation({ mutationFn: adminPremiumApi.deleteProduct, onSuccess: refresh, onError: (e) => alert(errMsg(e)) });

    const cosmetics = cosmeticsQ.data ?? [];

    return (
        <div className="space-y-6">
            <ConfigSection />

            <Section title="Produits en euros" action={<Button size="sm" variant="primary" onClick={() => setEditingProduct(null)}>+ Produit</Button>}>
                {(productsQ.data ?? []).length === 0 && <p className="text-white/30 text-sm">Aucun produit.</p>}
                {(productsQ.data ?? []).map((p) => (
                    <div key={p.id} className="flex items-center justify-between bg-game-surface/60 border border-white/5 rounded-lg px-3 py-2">
                        <button className="text-left flex-1 min-w-0" onClick={() => setEditingProduct(p)}>
                            <p className="text-white text-sm font-semibold truncate">
                                {p.name} — {formatEuros(p.price_cents)} {!p.active && <span className="text-white/30">(inactif)</span>}
                            </p>
                            <p className="text-white/40 text-xs truncate">
                                {p.grants.map((g) => (g.kind === "cosmetic" ? g.name : `${g.amount} ${g.name}`)).join(" + ")}
                                {p.limit_period !== "none" ? ` · ${p.limit_count} ${LIMIT_PERIOD_LABEL[p.limit_period]}` : ""}
                            </p>
                        </button>
                        <button className="text-red-400/70 hover:text-red-400 text-sm px-2"
                            onClick={() => confirm(`Supprimer « ${p.name} » ?`) && removeProduct.mutate(p.id)}>Suppr.</button>
                    </div>
                ))}
            </Section>

            <Section title="Cosmétiques" action={<Button size="sm" variant="primary" onClick={() => setEditingCosmetic(null)}>+ Cosmétique</Button>}>
                <p className="text-white/30 text-xs">
                    Pour les vendre en éclats : onglet « Offres shop », type « Cosmétique », ressource « Éclats ».
                </p>
                {cosmetics.map((c) => (
                    <div key={c.id} className="flex items-center gap-3 bg-game-surface/60 border border-white/5 rounded-lg px-3 py-2">
                        <CosmeticPreview cosmetic={c} size={36} />
                        <button className="text-left flex-1 min-w-0" onClick={() => setEditingCosmetic(c)}>
                            <p className="text-white text-sm font-semibold truncate">{c.name} {!c.active && <span className="text-white/30">(inactif)</span>}</p>
                            <p className="text-white/40 text-xs">{COSMETIC_KIND_LABEL[c.kind]}</p>
                        </button>
                        <button className="text-red-400/70 hover:text-red-400 text-sm px-2"
                            onClick={() => confirm(`Supprimer « ${c.name} » ?`) && removeCosmetic.mutate(c.id)}>Suppr.</button>
                    </div>
                ))}
            </Section>

            <Section title="Dernières commandes">
                {(ordersQ.data ?? []).length === 0 && <p className="text-white/30 text-sm">Aucune commande.</p>}
                {(ordersQ.data ?? []).map((o) => (
                    <div key={o.id} className="flex items-center justify-between bg-game-surface/60 border border-white/5 rounded-lg px-3 py-2 text-xs">
                        <div className="min-w-0">
                            <p className="text-white truncate">#{o.id} · {o.product_name} · {formatEuros(o.amount_cents)}</p>
                            <p className="text-white/40">{o.username ?? "compte supprimé"} · {parseUtc(o.created_at).toLocaleString("fr-FR")}</p>
                        </div>
                        <span className={o.status === "paid" ? "text-green-400" : o.status === "pending" ? "text-white/40" : "text-red-400"}>
                            {STATUS_LABEL[o.status] ?? o.status}
                        </span>
                    </div>
                ))}
            </Section>

            {editingCosmetic !== undefined && (
                <Modal open onClose={() => setEditingCosmetic(undefined)} title={editingCosmetic ? "Modifier le cosmétique" : "Nouveau cosmétique"}>
                    <CosmeticForm initial={editingCosmetic} onDone={refresh} />
                </Modal>
            )}
            {editingProduct !== undefined && (
                <Modal open onClose={() => setEditingProduct(undefined)} title={editingProduct ? "Modifier le produit" : "Nouveau produit"}>
                    <ProductForm initial={editingProduct} cosmetics={cosmetics} onDone={refresh} />
                </Modal>
            )}
        </div>
    );
}

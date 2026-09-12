import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi, adminKey } from "@/api/admin";
import { useTypes } from "@/hooks/useTypes";
import type {
    GameSet,
    AdminBooster,
    AdminCharacter,
    AdminResource,
    AdminShopOffer,
    CharacterSetLink,
    Tuning,
} from "@/types/content";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";

const inputCls =
    "w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white " +
    "placeholder-white/30 focus:border-accent focus:outline-none transition-colors";
const labelCls = "block text-white/60 text-xs mb-1";

function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof r?.data?.detail === "string") return r.data.detail;
    }
    return "Erreur.";
}

const hexFromRgb = (r: number, g: number, b: number) =>
    "#" + [r, g, b].map((x) => Math.max(0, Math.min(255, x)).toString(16).padStart(2, "0")).join("");
const rgbFromHex = (hex: string): [number, number, number] => {
    const n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};

/* ───────────────────────── Portail (clé admin) ───────────────────────── */

function KeyGate({ onOk }: { onOk: () => void }) {
    const [k, setK] = useState("");
    const [err, setErr] = useState("");
    const [busy, setBusy] = useState(false);

    const submit = async () => {
        setBusy(true);
        setErr("");
        const ok = await adminApi.check(k.trim());
        setBusy(false);
        if (ok) {
            adminKey.set(k.trim());
            onOk();
        } else {
            setErr("Clé refusée.");
        }
    };

    return (
        <div className="min-h-screen bg-game-bg flex flex-col items-center justify-center gap-4 px-4">
            <h1 className="text-xl font-bold text-white">Panneau d'administration</h1>
            <input
                type="password"
                className={inputCls + " max-w-xs"}
                placeholder="Clé admin (X-Admin-Key)"
                value={k}
                onChange={(e) => setK(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submit()}
            />
            {err && <p className="text-red-400 text-sm">{err}</p>}
            <Button variant="primary" loading={busy} onClick={submit}>
                Entrer
            </Button>
        </div>
    );
}

/* ─────────────────────── Modale de confirmation ──────────────────────── */

function ConfirmModal({
    open, title, message, busy, onConfirm, onCancel,
}: {
    open: boolean;
    title: string;
    message: string;
    busy: boolean;
    onConfirm: () => void;
    onCancel: () => void;
}) {
    return (
        <Modal open={open} onClose={onCancel} title={title}>
            <p className="text-white/70 text-sm mb-4">{message}</p>
            <div className="flex gap-2">
                <Button variant="danger" className="flex-1" loading={busy} onClick={onConfirm}>
                    Supprimer
                </Button>
                <Button variant="secondary" onClick={onCancel}>Annuler</Button>
            </div>
        </Modal>
    );
}

/* ─────────────────────────── Formulaire Set ─────────────────────────── */

function SetForm({
    initial, onSaved, onClose,
}: { initial: GameSet | null; onSaved: () => void; onClose: () => void }) {
    const isNew = !initial;
    const [f, setF] = useState<GameSet>(initial ?? { id: "", name: "", description: "" });
    const [err, setErr] = useState("");
    const m = useMutation({
        mutationFn: () =>
            isNew
                ? adminApi.createSet(f)
                : adminApi.updateSet(f.id, { name: f.name, description: f.description }),
        onSuccess: onSaved,
        onError: (e) => setErr(errMsg(e)),
    });

    return (
        <div className="space-y-3">
            <div>
                <label className={labelCls}>Identifiant</label>
                <input className={inputCls} value={f.id} disabled={!isNew} placeholder="ex: A3"
                    onChange={(e) => setF({ ...f, id: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>Nom</label>
                <input className={inputCls} value={f.name}
                    onChange={(e) => setF({ ...f, name: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>Description</label>
                <textarea className={inputCls} rows={2} value={f.description}
                    onChange={(e) => setF({ ...f, description: e.target.value })} />
            </div>
            {err && <p className="text-red-400 text-xs">{err}</p>}
            <div className="flex gap-2 pt-1">
                <Button variant="primary" className="flex-1" loading={m.isPending} onClick={() => m.mutate()}>
                    {isNew ? "Créer" : "Enregistrer"}
                </Button>
                <Button variant="secondary" onClick={onClose}>Annuler</Button>
            </div>
        </div>
    );
}

/* ─────────────────────────── Formulaire Booster ───────────────────────── */

function BoosterForm({
    initial, sets, onSaved, onClose,
}: { initial: AdminBooster | null; sets: GameSet[]; onSaved: () => void; onClose: () => void }) {
    const isNew = !initial;
    const [f, setF] = useState<AdminBooster>(
        initial ?? {
            id: "", name: "", set_ids: sets[0] ? [sets[0].id] : [], cards_count: 5,
            price: 100, guaranteed_rare: false, description: "",
        }
    );
    const [err, setErr] = useState("");
    const m = useMutation({
        mutationFn: () =>
            isNew ? adminApi.createBooster(f) : adminApi.updateBooster(f.id, f),
        onSuccess: onSaved,
        onError: (e) => setErr(errMsg(e)),
    });

    const toggleSet = (id: string) =>
        setF((prev) => ({
            ...prev,
            set_ids: prev.set_ids.includes(id)
                ? prev.set_ids.filter((s) => s !== id)
                : [...prev.set_ids, id],
        }));

    return (
        <div className="space-y-3">
            <div>
                <label className={labelCls}>Identifiant</label>
                <input className={inputCls} value={f.id} disabled={!isNew}
                    placeholder="ex: booster_A3"
                    onChange={(e) => setF({ ...f, id: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>Nom</label>
                <input className={inputCls} value={f.name}
                    onChange={(e) => setF({ ...f, name: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>
                    Sets — le booster pioche parmi les personnages de tous les sets cochés
                </label>
                <div className="flex flex-wrap gap-2">
                    {sets.map((s) => (
                        <button
                            key={s.id}
                            type="button"
                            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${f.set_ids.includes(s.id)
                                    ? "bg-accent text-white"
                                    : "bg-white/10 text-white/50 hover:bg-white/20"
                                }`}
                            onClick={() => toggleSet(s.id)}
                        >
                            {s.id}
                        </button>
                    ))}
                </div>
                {f.set_ids.length === 0 && (
                    <p className="text-red-400 text-xs mt-1">Choisis au moins un set.</p>
                )}
            </div>
            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className={labelCls}>Cartes / pack</label>
                    <input type="number" className={inputCls} value={f.cards_count}
                        onChange={(e) => setF({ ...f, cards_count: +e.target.value })} />
                </div>
                <div>
                    <label className={labelCls}>Prix</label>
                    <input type="number" className={inputCls} value={f.price}
                        onChange={(e) => setF({ ...f, price: +e.target.value })} />
                </div>
            </div>
            <label className="flex items-center gap-2 text-sm text-white/80">
                <input type="checkbox" checked={f.guaranteed_rare}
                    onChange={(e) => setF({ ...f, guaranteed_rare: e.target.checked })} />
                Rare garantie
            </label>
            <div>
                <label className={labelCls}>Description</label>
                <textarea className={inputCls} rows={2} value={f.description}
                    onChange={(e) => setF({ ...f, description: e.target.value })} />
            </div>
            {err && <p className="text-red-400 text-xs">{err}</p>}
            <div className="flex gap-2 pt-1">
                <Button variant="primary" className="flex-1" loading={m.isPending}
                    disabled={f.set_ids.length === 0}
                    onClick={() => m.mutate()}>
                    {isNew ? "Créer" : "Enregistrer"}
                </Button>
                <Button variant="secondary" onClick={onClose}>Annuler</Button>
            </div>
        </div>
    );
}

/* ──────────────────────── Formulaire Personnage ─────────────────────── */

function CharacterForm({
    initial, sets, onSaved, onClose,
}: { initial: AdminCharacter | null; sets: GameSet[]; onSaved: () => void; onClose: () => void }) {
    const isNew = !initial;
    const { data: types } = useTypes();
    const [f, setF] = useState<AdminCharacter>(
        initial ?? { id: "", name: "", description: "", type: "Normal", gen: 1, image_url: "", sets: [] }
    );
    const [err, setErr] = useState("");
    const m = useMutation({
        mutationFn: () =>
            isNew ? adminApi.createCharacter(f) : adminApi.updateCharacter(f.id, f),
        onSuccess: onSaved,
        onError: (e) => setErr(errMsg(e)),
    });

    const setLink = (i: number, patch: Partial<CharacterSetLink>) =>
        setF({ ...f, sets: f.sets.map((l, j) => (j === i ? { ...l, ...patch } : l)) });
    const addLink = () =>
        setF({ ...f, sets: [...f.sets, { set_id: sets[0]?.id ?? "", weight: 1 }] });
    const rmLink = (i: number) => setF({ ...f, sets: f.sets.filter((_, j) => j !== i) });

    return (
        <div className="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className={labelCls}>Identifiant</label>
                    <input className={inputCls} value={f.id} disabled={!isNew}
                        placeholder="ex: char_012"
                        onChange={(e) => setF({ ...f, id: e.target.value })} />
                </div>
                <div>
                    <label className={labelCls}>Gen</label>
                    <input type="number" className={inputCls} value={f.gen}
                        onChange={(e) => setF({ ...f, gen: +e.target.value })} />
                </div>
            </div>
            <div>
                <label className={labelCls}>Nom</label>
                <input className={inputCls} value={f.name}
                    onChange={(e) => setF({ ...f, name: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>Type</label>
                <select className={inputCls} value={f.type}
                    onChange={(e) => setF({ ...f, type: e.target.value })}>
                    {(types ?? []).map((t) => <option key={t.id} value={t.name}>{t.name}</option>)}
                    {types && !types.some((t) => t.name === f.type) && (
                        <option value={f.type}>{f.type} (introuvable dans Types)</option>
                    )}
                </select>
            </div>
            <div>
                <label className={labelCls}>
                    Image (nom de fichier dans <code>web/public/characters/</code>)
                </label>
                <input className={inputCls} value={f.image_url}
                    placeholder="mon-perso.png"
                    onChange={(e) => setF({ ...f, image_url: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>Description</label>
                <textarea className={inputCls} rows={2} value={f.description}
                    onChange={(e) => setF({ ...f, description: e.target.value })} />
            </div>

            <div>
                <div className="flex items-center justify-between mb-1">
                    <label className={labelCls}>Sets & poids d'apparition</label>
                    <button className="text-accent text-xs" onClick={addLink}>+ ajouter</button>
                </div>
                {f.sets.length === 0 && (
                    <p className="text-white/30 text-xs">
                        Aucun set → le personnage n'apparaîtra dans aucun pack.
                    </p>
                )}
                <div className="space-y-2">
                    {f.sets.map((l, i) => (
                        <div key={i} className="flex gap-2 items-center">
                            <select className={inputCls} value={l.set_id}
                                onChange={(e) => setLink(i, { set_id: e.target.value })}>
                                {sets.map((s) => <option key={s.id} value={s.id}>{s.id}</option>)}
                            </select>
                            <input type="number" step="0.1" className={inputCls + " w-24"}
                                value={l.weight}
                                onChange={(e) => setLink(i, { weight: +e.target.value })} />
                            <button className="text-red-400 text-lg px-1" onClick={() => rmLink(i)}>×</button>
                        </div>
                    ))}
                </div>
            </div>

            {err && <p className="text-red-400 text-xs">{err}</p>}
            <div className="flex gap-2 pt-1">
                <Button variant="primary" className="flex-1" loading={m.isPending} onClick={() => m.mutate()}>
                    {isNew ? "Créer" : "Enregistrer"}
                </Button>
                <Button variant="secondary" onClick={onClose}>Annuler</Button>
            </div>
        </div>
    );
}

/* ─────────────────────────── Formulaire Type ─────────────────────────── */

function TypeForm({ onSaved, onClose }: { onSaved: () => void; onClose: () => void }) {
    const [f, setF] = useState({ id: "", name: "", color_r: 150, color_g: 150, color_b: 150 });
    const [err, setErr] = useState("");
    const m = useMutation({
        mutationFn: () => adminApi.createType(f),
        onSuccess: onSaved,
        onError: (e) => setErr(errMsg(e)),
    });

    return (
        <div className="space-y-3">
            <div>
                <label className={labelCls}>Identifiant (slug)</label>
                <input className={inputCls} value={f.id} placeholder="ex: cristal"
                    onChange={(e) => setF({ ...f, id: e.target.value.toLowerCase() })} />
            </div>
            <div>
                <label className={labelCls}>Nom affiché</label>
                <input className={inputCls} value={f.name} placeholder="ex: Cristal"
                    onChange={(e) => setF({ ...f, name: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>Couleur</label>
                <div className="flex items-center gap-3">
                    <input
                        type="color"
                        className="w-12 h-9 rounded bg-transparent border border-white/10"
                        value={hexFromRgb(f.color_r, f.color_g, f.color_b)}
                        onChange={(e) => {
                            const [r, g, b] = rgbFromHex(e.target.value);
                            setF({ ...f, color_r: r, color_g: g, color_b: b });
                        }}
                    />
                    <span
                        className="px-3 py-1.5 rounded-full text-xs font-semibold"
                        style={{ background: hexFromRgb(f.color_r, f.color_g, f.color_b) }}
                    >
                        {f.name || "aperçu"}
                    </span>
                </div>
            </div>
            {err && <p className="text-red-400 text-xs">{err}</p>}
            <div className="flex gap-2 pt-1">
                <Button variant="primary" className="flex-1" loading={m.isPending} onClick={() => m.mutate()}>
                    Créer
                </Button>
                <Button variant="secondary" onClick={onClose}>Annuler</Button>
            </div>
        </div>
    );
}

/* ────────────────────────── Formulaire Ressource ─────────────────────── */

function ResourceForm({ onSaved, onClose }: { onSaved: () => void; onClose: () => void }) {
    const [f, setF] = useState<AdminResource>({ id: "", name: "", description: "" });
    const [err, setErr] = useState("");
    const m = useMutation({
        mutationFn: () => adminApi.createResource(f),
        onSuccess: onSaved,
        onError: (e) => setErr(errMsg(e)),
    });

    return (
        <div className="space-y-3">
            <div>
                <label className={labelCls}>Identifiant (slug)</label>
                <input className={inputCls} value={f.id} placeholder="ex: shards"
                    onChange={(e) => setF({ ...f, id: e.target.value.toLowerCase() })} />
            </div>
            <div>
                <label className={labelCls}>Nom affiché</label>
                <input className={inputCls} value={f.name} placeholder="ex: Éclats"
                    onChange={(e) => setF({ ...f, name: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>Description</label>
                <textarea className={inputCls} rows={2} value={f.description}
                    onChange={(e) => setF({ ...f, description: e.target.value })} />
            </div>
            {err && <p className="text-red-400 text-xs">{err}</p>}
            <div className="flex gap-2 pt-1">
                <Button variant="primary" className="flex-1" loading={m.isPending} onClick={() => m.mutate()}>
                    Créer
                </Button>
                <Button variant="secondary" onClick={onClose}>Annuler</Button>
            </div>
        </div>
    );
}

/* ──────────────────────── Formulaire Offre du shop ───────────────────── */

const OFFER_KINDS: { value: AdminShopOffer["kind"]; label: string }[] = [
    { value: "booster", label: "Booster" },
    { value: "specific_card", label: "Carte précise" },
    { value: "upgrade", label: "Amélioration" },
];

function ShopOfferForm({
    resources, boosters, characters, tuning, onSaved, onClose,
}: {
    resources: AdminResource[];
    boosters: AdminBooster[];
    characters: AdminCharacter[];
    tuning: Tuning | undefined;
    onSaved: () => void;
    onClose: () => void;
}) {
    const [f, setF] = useState<Partial<AdminShopOffer>>({
        id: "", name: "", description: "", kind: "booster",
        resource_id: resources[0]?.id ?? "", price: 10,
        booster_id: boosters[0]?.id,
    });
    const [err, setErr] = useState("");
    const m = useMutation({
        mutationFn: () => adminApi.createShopOffer(f),
        onSuccess: onSaved,
        onError: (e) => setErr(errMsg(e)),
    });

    const rarities = tuning?.rarities ?? [];
    const qualities = tuning?.qualities ?? [];
    const specialties = tuning?.specialties ?? [];
    const jewelries = tuning?.jewelries ?? [];

    return (
        <div className="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
            <div>
                <label className={labelCls}>Identifiant</label>
                <input className={inputCls} value={f.id} placeholder="ex: offre_pack_a1"
                    onChange={(e) => setF({ ...f, id: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>Nom</label>
                <input className={inputCls} value={f.name}
                    onChange={(e) => setF({ ...f, name: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>Type d'offre</label>
                <select className={inputCls} value={f.kind}
                    onChange={(e) => setF({ ...f, kind: e.target.value as AdminShopOffer["kind"] })}>
                    {OFFER_KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
                </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className={labelCls}>Ressource</label>
                    <select className={inputCls} value={f.resource_id}
                        onChange={(e) => setF({ ...f, resource_id: e.target.value })}>
                        {resources.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                </div>
                <div>
                    <label className={labelCls}>Prix</label>
                    <input type="number" className={inputCls} value={f.price}
                        onChange={(e) => setF({ ...f, price: +e.target.value })} />
                </div>
            </div>

            {f.kind === "booster" && (
                <div>
                    <label className={labelCls}>Booster</label>
                    <select className={inputCls} value={f.booster_id ?? ""}
                        onChange={(e) => setF({ ...f, booster_id: e.target.value })}>
                        {boosters.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                    </select>
                </div>
            )}

            {f.kind === "specific_card" && (
                <div className="space-y-2">
                    <div>
                        <label className={labelCls}>Personnage</label>
                        <select className={inputCls} value={f.character_id ?? ""}
                            onChange={(e) => setF({ ...f, character_id: e.target.value })}>
                            <option value="">—</option>
                            {characters.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                        </select>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className={labelCls}>Rareté</label>
                            <select className={inputCls} value={f.rarity_id ?? ""}
                                onChange={(e) => setF({ ...f, rarity_id: e.target.value })}>
                                <option value="">—</option>
                                {rarities.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className={labelCls}>Qualité</label>
                            <select className={inputCls} value={f.quality_id ?? ""}
                                onChange={(e) => setF({ ...f, quality_id: e.target.value })}>
                                <option value="">—</option>
                                {qualities.map((q) => <option key={q.id} value={q.id}>{q.name}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className={labelCls}>Spécialité</label>
                            <select className={inputCls} value={f.specialty_id ?? ""}
                                onChange={(e) => setF({ ...f, specialty_id: e.target.value })}>
                                <option value="">—</option>
                                {specialties.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className={labelCls}>Jewelry</label>
                            <select className={inputCls} value={f.jewelry_id ?? ""}
                                onChange={(e) => setF({ ...f, jewelry_id: e.target.value })}>
                                <option value="">—</option>
                                {jewelries.map((j) => <option key={j.id} value={j.id}>{j.name}</option>)}
                            </select>
                        </div>
                    </div>
                </div>
            )}

            {f.kind === "upgrade" && (
                <div className="grid grid-cols-2 gap-2">
                    <div>
                        <label className={labelCls}>Qualité cible</label>
                        <select className={inputCls} value={f.target_quality_id ?? ""}
                            onChange={(e) => setF({ ...f, target_quality_id: e.target.value || undefined })}>
                            <option value="">— aucune —</option>
                            {qualities.map((q) => <option key={q.id} value={q.id}>{q.name}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className={labelCls}>Spécialité cible</label>
                        <select className={inputCls} value={f.target_specialty_id ?? ""}
                            onChange={(e) => setF({ ...f, target_specialty_id: e.target.value || undefined })}>
                            <option value="">— aucune —</option>
                            {specialties.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                        </select>
                    </div>
                </div>
            )}

            <div>
                <label className={labelCls}>Description</label>
                <textarea className={inputCls} rows={2} value={f.description}
                    onChange={(e) => setF({ ...f, description: e.target.value })} />
            </div>
            {err && <p className="text-red-400 text-xs">{err}</p>}
            <div className="flex gap-2 pt-1">
                <Button variant="primary" className="flex-1" loading={m.isPending} onClick={() => m.mutate()}>
                    Créer
                </Button>
                <Button variant="secondary" onClick={onClose}>Annuler</Button>
            </div>
        </div>
    );
}

/* ─────────────────────────────── Panneau ────────────────────────────── */

type Tab = "characters" | "boosters" | "sets" | "types" | "resources" | "offers";

function Panel() {
    const navigate = useNavigate();
    const qc = useQueryClient();
    const [tab, setTab] = useState<Tab>("characters");
    const [search, setSearch] = useState("");
    const [editing, setEditing] = useState<
        | { kind: "set"; data: GameSet | null }
        | { kind: "booster"; data: AdminBooster | null }
        | { kind: "character"; data: AdminCharacter | null }
        | { kind: "type" }
        | { kind: "resource" }
        | { kind: "offer" }
        | null
    >(null);
    const [toDelete, setToDelete] = useState<{ kind: Tab; id: string; label: string } | null>(null);

    const setsQ = useQuery({ queryKey: ["admin", "sets"], queryFn: adminApi.listSets });
    const boostersQ = useQuery({ queryKey: ["admin", "boosters"], queryFn: adminApi.listBoosters });
    const charsQ = useQuery({ queryKey: ["admin", "characters"], queryFn: adminApi.listCharacters });
    const typesQ = useQuery({ queryKey: ["admin", "types"], queryFn: adminApi.listTypes, enabled: tab === "types" });
    const resourcesQ = useQuery({ queryKey: ["admin", "resources"], queryFn: adminApi.listResources });
    const offersQ = useQuery({ queryKey: ["admin", "offers"], queryFn: adminApi.listShopOffers, enabled: tab === "offers" });
    const tuningQ = useQuery({ queryKey: ["admin", "tuning"], queryFn: adminApi.tuning });

    const sets = setsQ.data ?? [];
    const resources = resourcesQ.data ?? [];

    const refresh = () => {
        qc.invalidateQueries({ queryKey: ["admin"] });
        qc.invalidateQueries({ queryKey: ["types"] }); // le jeu utilise le meme cache
        setEditing(null);
    };

    const del = useMutation({
        mutationFn: async (x: { kind: Tab; id: string }) => {
            if (x.kind === "sets") return adminApi.deleteSet(x.id);
            if (x.kind === "boosters") return adminApi.deleteBooster(x.id);
            if (x.kind === "types") return adminApi.deleteType(x.id);
            if (x.kind === "resources") return adminApi.deleteResource(x.id);
            if (x.kind === "offers") return adminApi.deleteShopOffer(x.id);
            return adminApi.deleteCharacter(x.id);
        },
        onSuccess: () => { refresh(); setToDelete(null); },
        onError: (e) => alert(errMsg(e)),
    });

    const toggleOffer = useMutation({
        mutationFn: (o: AdminShopOffer) => adminApi.setShopOfferActive(o.id, !o.active),
        onSuccess: refresh,
        onError: (e) => alert(errMsg(e)),
    });

    const q = search.trim().toLowerCase();
    const matches = (...vals: (string | undefined | null)[]) =>
        !q || vals.some((v) => v?.toLowerCase().includes(q));

    const filteredSets = useMemo(
        () => sets.filter((s) => matches(s.id, s.name)), [sets, q]
    );
    const filteredBoosters = useMemo(
        () => (boostersQ.data ?? []).filter((b) => matches(b.id, b.name)), [boostersQ.data, q]
    );
    const filteredChars = useMemo(
        () => (charsQ.data ?? []).filter((c) => matches(c.id, c.name, c.type)), [charsQ.data, q]
    );
    const filteredTypes = useMemo(
        () => (typesQ.data ?? []).filter((t) => matches(t.id, t.name)), [typesQ.data, q]
    );
    const filteredResources = useMemo(
        () => resources.filter((r) => matches(r.id, r.name)), [resources, q]
    );
    const filteredOffers = useMemo(
        () => (offersQ.data ?? []).filter((o) => matches(o.id, o.name)), [offersQ.data, q]
    );

    const Row = ({
        title, subtitle, onEdit, onDelete,
    }: { title: string; subtitle: string; onEdit?: () => void; onDelete: () => void }) => (
        <div className="flex items-center justify-between bg-game-surface/60 border border-white/5 rounded-lg px-3 py-2">
            {onEdit ? (
                <button className="text-left flex-1 min-w-0" onClick={onEdit}>
                    <p className="text-white text-sm font-semibold truncate">{title}</p>
                    <p className="text-white/40 text-xs truncate">{subtitle}</p>
                </button>
            ) : (
                <div className="flex-1 min-w-0">
                    <p className="text-white text-sm font-semibold truncate">{title}</p>
                    <p className="text-white/40 text-xs truncate">{subtitle}</p>
                </div>
            )}
            <button className="text-red-400/70 hover:text-red-400 text-sm px-2" onClick={onDelete}>
                Suppr.
            </button>
        </div>
    );

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate("/")}>
                    ← Jeu
                </button>
                <h1 className="text-white font-bold">Contenu</h1>
                <button
                    className="text-white/40 hover:text-white text-xs"
                    onClick={() => { adminKey.clear(); location.reload(); }}
                >
                    Verrouiller
                </button>
            </header>

            <div className="px-4 py-3 flex gap-2 overflow-x-auto no-scrollbar">
                {(["characters", "boosters", "sets", "types", "resources", "offers"] as Tab[]).map((t) => (
                    <button
                        key={t}
                        className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${tab === t ? "bg-accent text-white" : "bg-white/10 text-white/50 hover:bg-white/20"
                            }`}
                        onClick={() => setTab(t)}
                    >
                        {{
                            characters: "Personnages", boosters: "Boosters", sets: "Sets",
                            types: "Types", resources: "Ressources", offers: "Offres shop",
                        }[t]}
                    </button>
                ))}
            </div>

            <div className="px-4 pb-2">
                <input
                    type="search"
                    className={inputCls}
                    placeholder="Rechercher par nom ou id..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            <main className="flex-1 overflow-y-auto px-4 pb-6 space-y-2">
                <Button
                    variant="secondary"
                    size="sm"
                    className="w-full mb-2"
                    onClick={() =>
                        setEditing(
                            tab === "sets" ? { kind: "set", data: null }
                                : tab === "boosters" ? { kind: "booster", data: null }
                                    : tab === "types" ? { kind: "type" }
                                        : tab === "resources" ? { kind: "resource" }
                                            : tab === "offers" ? { kind: "offer" }
                                                : { kind: "character", data: null }
                        )
                    }
                >
                    ＋ Nouveau
                </Button>

                {tab === "sets" &&
                    (setsQ.isLoading ? <p className="text-white/40 text-sm">…</p> :
                        filteredSets.map((s) => (
                            <Row key={s.id}
                                title={`${s.name}  ·  ${s.id}`}
                                subtitle={`${s.booster_count ?? 0} booster(s), ${s.character_count ?? 0} perso(s) — ${s.description}`}
                                onEdit={() => setEditing({ kind: "set", data: s })}
                                onDelete={() => setToDelete({ kind: "sets", id: s.id, label: `le set « ${s.name} »` })}
                            />
                        )))}

                {tab === "boosters" &&
                    (boostersQ.isLoading ? <p className="text-white/40 text-sm">…</p> :
                        filteredBoosters.map((b) => (
                            <Row key={b.id}
                                title={`${b.name}  ·  ${b.id}`}
                                subtitle={`sets ${b.set_ids.join(", ")} — ${b.cards_count} cartes — ${b.price} 🪙${b.guaranteed_rare ? " — rare garantie" : ""}`}
                                onEdit={() => setEditing({ kind: "booster", data: b })}
                                onDelete={() => setToDelete({ kind: "boosters", id: b.id, label: `le booster « ${b.name} »` })}
                            />
                        )))}

                {tab === "characters" &&
                    (charsQ.isLoading ? <p className="text-white/40 text-sm">…</p> :
                        filteredChars.map((c) => (
                            <Row key={c.id}
                                title={`${c.name}  ·  ${c.id}`}
                                subtitle={`${c.type} · Gen ${c.gen} · sets: ${c.sets.map((l) => `${l.set_id}(${l.weight})`).join(", ") || "aucun"}`}
                                onEdit={() => setEditing({ kind: "character", data: c })}
                                onDelete={() => setToDelete({ kind: "characters", id: c.id, label: `le personnage « ${c.name} »` })}
                            />
                        )))}

                {tab === "types" &&
                    (typesQ.isLoading ? <p className="text-white/40 text-sm">…</p> :
                        filteredTypes.map((t) => (
                            <Row key={t.id}
                                title={`${t.name}  ·  ${t.id}`}
                                subtitle={`${t.in_use} personnage(s) l'utilisent`}
                                onDelete={() => setToDelete({ kind: "types", id: t.id, label: `le type « ${t.name} »` })}
                            />
                        )))}

                {tab === "resources" &&
                    (resourcesQ.isLoading ? <p className="text-white/40 text-sm">…</p> :
                        filteredResources.map((r) => (
                            <Row key={r.id}
                                title={`${r.name}  ·  ${r.id}`}
                                subtitle={r.description || "—"}
                                onDelete={() => setToDelete({ kind: "resources", id: r.id, label: `la ressource « ${r.name} »` })}
                            />
                        )))}

                {tab === "offers" &&
                    (offersQ.isLoading ? <p className="text-white/40 text-sm">…</p> :
                        filteredOffers.map((o) => (
                            <div key={o.id} className="flex items-center justify-between bg-game-surface/60 border border-white/5 rounded-lg px-3 py-2 gap-2">
                                <div className="flex-1 min-w-0">
                                    <p className={`text-sm font-semibold truncate ${o.active ? "text-white" : "text-white/30 line-through"}`}>
                                        {o.name}  ·  {o.id}
                                    </p>
                                    <p className="text-white/40 text-xs truncate">
                                        {o.kind} — {o.price} {o.resource_name}
                                    </p>
                                </div>
                                <button
                                    className="text-xs px-2 py-1 rounded-full bg-white/10 text-white/60 hover:bg-white/20 shrink-0"
                                    onClick={() => toggleOffer.mutate(o)}
                                >
                                    {o.active ? "Désactiver" : "Activer"}
                                </button>
                                <button className="text-red-400/70 hover:text-red-400 text-sm px-1 shrink-0"
                                    onClick={() => setToDelete({ kind: "offers", id: o.id, label: `l'offre « ${o.name} »` })}>
                                    Suppr.
                                </button>
                            </div>
                        )))}
            </main>

            <Modal
                open={!!editing}
                onClose={() => setEditing(null)}
                title={
                    editing?.kind === "set" ? "Set"
                        : editing?.kind === "booster" ? "Booster"
                            : editing?.kind === "type" ? "Nouveau type"
                                : editing?.kind === "resource" ? "Nouvelle ressource"
                                    : editing?.kind === "offer" ? "Nouvelle offre"
                                        : "Personnage"
                }
            >
                {editing?.kind === "set" && (
                    <SetForm initial={editing.data} onSaved={refresh} onClose={() => setEditing(null)} />
                )}
                {editing?.kind === "booster" && (
                    <BoosterForm initial={editing.data} sets={sets} onSaved={refresh} onClose={() => setEditing(null)} />
                )}
                {editing?.kind === "character" && (
                    <CharacterForm initial={editing.data} sets={sets} onSaved={refresh} onClose={() => setEditing(null)} />
                )}
                {editing?.kind === "type" && (
                    <TypeForm onSaved={refresh} onClose={() => setEditing(null)} />
                )}
                {editing?.kind === "resource" && (
                    <ResourceForm onSaved={refresh} onClose={() => setEditing(null)} />
                )}
                {editing?.kind === "offer" && (
                    <ShopOfferForm
                        resources={resources}
                        boosters={boostersQ.data ?? []}
                        characters={charsQ.data ?? []}
                        tuning={tuningQ.data}
                        onSaved={refresh}
                        onClose={() => setEditing(null)}
                    />
                )}
            </Modal>

            <ConfirmModal
                open={!!toDelete}
                title="Confirmer la suppression"
                message={toDelete ? `Supprimer définitivement ${toDelete.label} ? Cette action est irréversible.` : ""}
                busy={del.isPending}
                onConfirm={() => toDelete && del.mutate(toDelete)}
                onCancel={() => setToDelete(null)}
            />
        </div>
    );
}

export default function AdminPanel() {
    const [authed, setAuthed] = useState(!!adminKey.get());
    if (!authed) return <KeyGate onOk={() => setAuthed(true)} />;
    return <Panel />;
}

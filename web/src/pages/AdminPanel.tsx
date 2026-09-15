import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi, adminKey, type GameConfig } from "@/api/admin";
import { useTypes } from "@/hooks/useTypes";
import type {
    GameSet,
    AdminBooster,
    AdminCharacter,
    AdminType,
    AdminResource,
    AdminShopOffer,
    CharacterSetLink,
    Tuning,
    TuningEntry,
    TuningTable,
} from "@/types/content";
import { errMsg } from "@/utils/errors";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import ConfirmModal from "@/components/ui/ConfirmModal";
import AdminMessagesComposer from "@/components/admin/AdminMessagesComposer";
import AdminProgressionEditor from "@/components/admin/AdminProgressionEditor";
import AdminBugReports from "@/components/admin/AdminBugReports";

const inputCls =
    "w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white " +
    "placeholder-white/30 focus:border-accent focus:outline-none transition-colors";
const labelCls = "block text-white/60 text-xs mb-1";

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
    initial, sets, resources, onSaved, onClose,
}: {
    initial: AdminBooster | null; sets: GameSet[]; resources: AdminResource[];
    onSaved: () => void; onClose: () => void;
}) {
    const isNew = !initial;
    const [f, setF] = useState<AdminBooster>(
        initial ?? {
            id: "", name: "", set_ids: sets[0] ? [sets[0].id] : [], cards_count: 5,
            resource_id: "coins", resource_name: "Pièces", price: 100,
            guaranteed_rare: false, description: "",
            active: true, visible_in_shop: true, cover_image_url: "",
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
            <div>
                <label className={labelCls}>Monnaie</label>
                <select className={inputCls} value={f.resource_id}
                    onChange={(e) => setF({ ...f, resource_id: e.target.value })}>
                    {resources.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-white/80">
                <input type="checkbox" checked={f.guaranteed_rare}
                    onChange={(e) => setF({ ...f, guaranteed_rare: e.target.checked })} />
                Rare garantie
            </label>
            <label className="flex items-center gap-2 text-sm text-white/80">
                <input type="checkbox" checked={f.visible_in_shop}
                    onChange={(e) => setF({ ...f, visible_in_shop: e.target.checked })} />
                Visible dans la boutique classique (pièces)
            </label>
            <label className="flex items-center gap-2 text-sm text-white/80">
                <input type="checkbox" checked={f.active}
                    onChange={(e) => setF({ ...f, active: e.target.checked })} />
                Actif (décoche pour retirer partout, y compris le shop à ressources)
            </label>
            <div>
                <label className={labelCls}>Description</label>
                <textarea className={inputCls} rows={2} value={f.description}
                    onChange={(e) => setF({ ...f, description: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>
                    Couverture (nom de fichier dans <code>web/public/boosters/</code>)
                </label>
                <input className={inputCls} value={f.cover_image_url}
                    placeholder="mon-booster.png"
                    onChange={(e) => setF({ ...f, cover_image_url: e.target.value })} />
                <p className="text-white/30 text-xs mt-1">
                    Remplace le dos de pack générique et l'illustration en boutique. Laisse vide pour garder le visuel par défaut.
                </p>
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
                        Aucun set : le personnage n'apparaîtra dans aucun pack.
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

function TypeForm({
    initial, onSaved, onClose,
}: { initial: AdminType | null; onSaved: () => void; onClose: () => void }) {
    const isNew = !initial;
    const [f, setF] = useState(
        initial
            ? {
                id: initial.id, name: initial.name,
                color_r: initial.color[0], color_g: initial.color[1], color_b: initial.color[2],
            }
            : { id: "", name: "", color_r: 150, color_g: 150, color_b: 150 }
    );
    const [err, setErr] = useState("");
    const m = useMutation({
        mutationFn: () =>
            isNew
                ? adminApi.createType(f)
                : adminApi.updateType(f.id, {
                    name: f.name, color_r: f.color_r, color_g: f.color_g, color_b: f.color_b,
                }),
        onSuccess: onSaved,
        onError: (e) => setErr(errMsg(e)),
    });

    return (
        <div className="space-y-3">
            <div>
                <label className={labelCls}>Identifiant (slug)</label>
                <input className={inputCls} value={f.id} disabled={!isNew} placeholder="ex: cristal"
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
                    {isNew ? "Créer" : "Enregistrer"}
                </Button>
                <Button variant="secondary" onClick={onClose}>Annuler</Button>
            </div>
        </div>
    );
}

/* ────────────────────────── Formulaire Ressource ─────────────────────── */

function ResourceForm({
    initial, onSaved, onClose,
}: { initial: AdminResource | null; onSaved: () => void; onClose: () => void }) {
    const isNew = !initial;
    const [f, setF] = useState<AdminResource>(
        initial ?? { id: "", name: "", description: "", protected: false, starting_amount: 0 }
    );
    const [err, setErr] = useState("");
    const m = useMutation({
        mutationFn: () =>
            isNew
                ? adminApi.createResource(f)
                : adminApi.updateResource(f.id, { name: f.name, description: f.description }),
        onSuccess: onSaved,
        onError: (e) => setErr(errMsg(e)),
    });

    return (
        <div className="space-y-3">
            <div>
                <label className={labelCls}>Identifiant (slug)</label>
                <input className={inputCls} value={f.id} disabled={!isNew} placeholder="ex: shards"
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
                    {isNew ? "Créer" : "Enregistrer"}
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
    { value: "reroll", label: "Reroll (retirage)" },
];

function ShopOfferForm({
    initial, resources, boosters, characters, tuning, onSaved, onClose,
}: {
    initial: AdminShopOffer | null;
    resources: AdminResource[];
    boosters: AdminBooster[];
    characters: AdminCharacter[];
    tuning: Tuning | undefined;
    onSaved: () => void;
    onClose: () => void;
}) {
    const isNew = !initial;
    const [f, setF] = useState<Partial<AdminShopOffer>>(
        initial ?? {
            id: "", name: "", description: "", kind: "booster",
            resource_id: resources[0]?.id ?? "", price: 10,
            booster_id: boosters[0]?.id,
        }
    );
    const [err, setErr] = useState("");
    const m = useMutation({
        mutationFn: () => isNew ? adminApi.createShopOffer(f) : adminApi.updateShopOffer(f.id!, f),
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
                <input className={inputCls} value={f.id} disabled={!isNew} placeholder="ex: offre_pack_a1"
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
                <div className="space-y-2">
                    <div>
                        <label className={labelCls}>Booster</label>
                        <select className={inputCls} value={f.booster_id ?? ""}
                            onChange={(e) => setF({ ...f, booster_id: e.target.value })}>
                            {boosters.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                        </select>
                    </div>
                    <p className="text-white/40 text-xs">
                        Overrides propres à CETTE offre (n'affectent pas l'ouverture normale du même booster) :
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className={labelCls}>Rareté minimum garantie</label>
                            <select className={inputCls} value={f.force_min_rarity_id ?? ""}
                                onChange={(e) => setF({ ...f, force_min_rarity_id: e.target.value || undefined })}>
                                <option value="">— aucune —</option>
                                {rarities.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className={labelCls}>Multiplicateur proba rare+</label>
                            <input type="number" step="0.1" min="0" className={inputCls}
                                value={f.rarity_weight_multiplier ?? ""}
                                placeholder="ex: 2 = x2"
                                onChange={(e) => setF({ ...f, rarity_weight_multiplier: e.target.value ? +e.target.value : undefined })} />
                        </div>
                    </div>
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

            {f.kind === "reroll" && (
                <div className="space-y-2">
                    <label className={labelCls}>Axes retirés (le joueur choisit la carte à l'achat)</label>
                    <div className="flex flex-wrap gap-3">
                        {([
                            ["reroll_rarity", "Rareté"], ["reroll_quality", "Qualité"],
                            ["reroll_specialty", "Spécialité"], ["reroll_jewelry", "Jewelry"],
                            ["reroll_power", "Puissance"],
                        ] as const).map(([key, label]) => (
                            <label key={key} className="flex items-center gap-1.5 text-sm text-white/80">
                                <input type="checkbox" checked={!!f[key]}
                                    onChange={(e) => setF({ ...f, [key]: e.target.checked })} />
                                {label}
                            </label>
                        ))}
                    </div>
                    <div>
                        <label className={labelCls}>Mode</label>
                        <select className={inputCls} value={f.reroll_mode ?? ""}
                            onChange={(e) => setF({ ...f, reroll_mode: (e.target.value || undefined) as AdminShopOffer["reroll_mode"] })}>
                            <option value="">— choisir —</option>
                            <option value="random">Aléatoire (peut être pire qu'avant, moins cher)</option>
                            <option value="guaranteed_min">Garanti égal ou mieux (plus cher)</option>
                        </select>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className={labelCls}>Limite d'achat / jour / joueur</label>
                    <input type="number" min="1" className={inputCls}
                        value={f.purchase_limit_per_day ?? ""}
                        placeholder="illimité"
                        onChange={(e) => setF({ ...f, purchase_limit_per_day: e.target.value ? +e.target.value : undefined })} />
                </div>
                <label className="flex items-center gap-2 text-sm text-white/80 mt-5">
                    <input type="checkbox" checked={!!f.is_daily_pool}
                        onChange={(e) => setF({ ...f, is_daily_pool: e.target.checked })} />
                    Dans la rotation "du jour"
                </label>
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

/* ────────────────────────  Réglages globaux du jeu  ───────────────────── */

function GameConfigSection() {
    const qc = useQueryClient();
    const { data, isLoading } = useQuery({ queryKey: ["admin", "game-config"], queryFn: adminApi.getGameConfig });
    const [draft, setDraft] = useState<GameConfig | null>(null);
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const config = draft ?? data;

    const save = useMutation({
        mutationFn: (b: GameConfig) => adminApi.updateGameConfig(b),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "game-config"] }); setMsg({ text: "Enregistré.", ok: true }); },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    if (isLoading || !config) return <p className="text-white/40 text-sm">…</p>;

    return (
        <div className="bg-game-surface/60 border border-white/5 rounded-lg px-3 py-3 space-y-3 max-w-sm">
            {msg && <p className={`text-xs ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>}
            <div>
                <label className={labelCls}>Récompense quotidienne de base (pièces)</label>
                <input
                    type="number" className={inputCls} value={config.daily_base_reward}
                    onChange={(e) => setDraft({ ...config, daily_base_reward: Number(e.target.value) })}
                />
            </div>
            <div>
                <label className={labelCls}>Bonus par jour de série (pièces)</label>
                <input
                    type="number" className={inputCls} value={config.daily_streak_bonus}
                    onChange={(e) => setDraft({ ...config, daily_streak_bonus: Number(e.target.value) })}
                />
            </div>
            <Button variant="secondary" size="sm" loading={save.isPending} onClick={() => save.mutate(config)}>
                OK
            </Button>
        </div>
    );
}

/* ──────────────────  Poids de tirage & recyclage (rareté/qualité/...)  ────────────────── */

function TuningTableRows({ table, label, entries }: { table: TuningTable; label: string; entries: TuningEntry[] }) {
    const qc = useQueryClient();
    const [drafts, setDrafts] = useState<Record<string, Partial<TuningEntry>>>({});
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const save = useMutation({
        mutationFn: (e: TuningEntry) => adminApi.updateTuning(table, e.id, { weight: e.weight, recycle_value: e.recycle_value }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "tuning"] }); setMsg({ text: "Enregistré.", ok: true }); },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    return (
        <div>
            <h4 className="text-white/50 text-xs font-semibold uppercase mb-1.5">{label}</h4>
            {msg && <p className={`text-xs mb-1 ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>}
            <div className="space-y-2">
                {entries.map((entry) => {
                    const draft = { ...entry, ...drafts[entry.id] };
                    return (
                        <div key={entry.id} className="bg-game-surface/60 border border-white/5 rounded-lg px-3 py-2 flex items-center gap-2 flex-wrap">
                            <span className="text-white text-sm font-semibold w-24 shrink-0 truncate">{entry.name}</span>
                            <div className="flex-1 min-w-[90px]">
                                <label className="block text-white/40 text-[10px]">Poids (tirage)</label>
                                <input
                                    type="number" step="0.1" className={inputCls} value={draft.weight ?? 0}
                                    onChange={(e) => setDrafts((d) => ({ ...d, [entry.id]: { ...draft, weight: Number(e.target.value) } }))}
                                />
                            </div>
                            <div className="flex-1 min-w-[90px]">
                                <label className="block text-white/40 text-[10px]">Poussière (recyclage)</label>
                                <input
                                    type="number" className={inputCls} value={draft.recycle_value ?? 0}
                                    onChange={(e) => setDrafts((d) => ({ ...d, [entry.id]: { ...draft, recycle_value: Number(e.target.value) } }))}
                                />
                            </div>
                            <Button
                                variant="secondary" size="sm"
                                loading={save.isPending && save.variables?.id === entry.id}
                                onClick={() => save.mutate(draft as TuningEntry)}
                            >
                                OK
                            </Button>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function TuningSection() {
    const { data, isLoading } = useQuery({ queryKey: ["admin", "tuning"], queryFn: adminApi.tuning });
    if (isLoading || !data) return <p className="text-white/40 text-sm">…</p>;
    return (
        <div className="space-y-4">
            <TuningTableRows table="rarities" label="Raretés" entries={data.rarities} />
            <TuningTableRows table="qualities" label="Qualités" entries={data.qualities} />
            <TuningTableRows table="specialties" label="Spécialités" entries={data.specialties} />
            <TuningTableRows table="jewelries" label="Bijoux" entries={data.jewelries} />
        </div>
    );
}

/* ──────────────────────  Ressources de départ (création de compte)  ──────────────────────── */

function StartingResourcesSection() {
    const qc = useQueryClient();
    const { data, isLoading } = useQuery({ queryKey: ["admin", "resources"], queryFn: adminApi.listResources });
    const [drafts, setDrafts] = useState<Record<string, number>>({});
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const save = useMutation({
        mutationFn: (r: AdminResource) => adminApi.updateResource(r.id, { starting_amount: r.starting_amount }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "resources"] }); setMsg({ text: "Enregistré.", ok: true }); },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    if (isLoading || !data) return <p className="text-white/40 text-sm">…</p>;

    return (
        <div>
            <h4 className="text-white/50 text-xs font-semibold uppercase mb-1.5">Ressources de départ (nouveau compte)</h4>
            {msg && <p className={`text-xs mb-1 ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>}
            <div className="space-y-2">
                {data.map((r) => {
                    const value = drafts[r.id] ?? r.starting_amount;
                    return (
                        <div key={r.id} className="bg-game-surface/60 border border-white/5 rounded-lg px-3 py-2 flex items-center gap-2 flex-wrap">
                            <span className="text-white text-sm font-semibold flex-1 min-w-[80px] truncate">{r.name}</span>
                            <input
                                type="number" className={`${inputCls} w-28`} value={value}
                                onChange={(e) => setDrafts((d) => ({ ...d, [r.id]: Number(e.target.value) }))}
                            />
                            <Button
                                variant="secondary" size="sm"
                                loading={save.isPending && save.variables?.id === r.id}
                                onClick={() => save.mutate({ ...r, starting_amount: value })}
                            >
                                OK
                            </Button>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

/* ─────────────────────────────── Panneau ────────────────────────────── */

type Tab ="characters" | "boosters" | "sets" | "types" | "resources" | "offers" | "messages" | "progression" | "settings" | "bugReports";

function Panel() {
    const navigate = useNavigate();
    const qc = useQueryClient();
    const [tab, setTab] = useState<Tab>("characters");
    const [search, setSearch] = useState("");
    const [editing, setEditing] = useState<
        | { kind: "set"; data: GameSet | null }
        | { kind: "booster"; data: AdminBooster | null }
        | { kind: "character"; data: AdminCharacter | null }
        | { kind: "type"; data: AdminType | null }
        | { kind: "resource"; data: AdminResource | null }
        | { kind: "offer"; data: AdminShopOffer | null }
        | null
    >(null);
    const [toDelete, setToDelete] = useState<{ kind: Tab; id: string; label: string } | null>(null);
    const [pinChoice, setPinChoice] = useState("");

    const setsQ = useQuery({ queryKey: ["admin", "sets"], queryFn: adminApi.listSets });
    const boostersQ = useQuery({ queryKey: ["admin", "boosters"], queryFn: adminApi.listBoosters });
    const charsQ = useQuery({ queryKey: ["admin", "characters"], queryFn: adminApi.listCharacters });
    const typesQ = useQuery({ queryKey: ["admin", "types"], queryFn: adminApi.listTypes, enabled: tab === "types" });
    const resourcesQ = useQuery({ queryKey: ["admin", "resources"], queryFn: adminApi.listResources });
    const offersQ = useQuery({ queryKey: ["admin", "offers"], queryFn: adminApi.listShopOffers, enabled: tab === "offers" });
    const tuningQ = useQuery({ queryKey: ["admin", "tuning"], queryFn: adminApi.tuning });
    const dailyFeatureQ = useQuery({
        queryKey: ["admin", "daily-feature"], queryFn: adminApi.getDailyFeature, enabled: tab === "offers",
    });

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

    const pinFeature = useMutation({
        mutationFn: (offerId: string) => adminApi.setDailyFeature(offerId),
        onSuccess: refresh,
        onError: (e) => alert(errMsg(e)),
    });
    const unpinFeature = useMutation({
        mutationFn: () => adminApi.clearDailyFeature(new Date().toISOString().slice(0, 10)),
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
    }: { title: string; subtitle: string; onEdit?: () => void; onDelete?: () => void }) => (
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
            {onDelete ? (
                <button className="text-red-400/70 hover:text-red-400 text-sm px-2" onClick={onDelete}>
                    Suppr.
                </button>
            ) : (
                <span className="text-white/25 text-xs px-2 shrink-0">protégée</span>
            )}
        </div>
    );

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button
                    className="text-accent text-sm font-semibold"
                    onClick={() => { adminKey.clear(); navigate("/"); }}
                >
                    Jeu
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
                {(["characters", "boosters", "sets", "types", "resources", "offers", "messages", "progression", "settings", "bugReports"] as Tab[]).map((t) => (
                    <button
                        key={t}
                        className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${tab === t ? "bg-accent text-white" : "bg-white/10 text-white/50 hover:bg-white/20"
                            }`}
                        onClick={() => setTab(t)}
                    >
                        {{
                            characters: "Personnages", boosters: "Boosters", sets: "Sets",
                            types: "Types", resources: "Ressources", offers: "Offres shop",
                            messages: "Messagerie", progression: "Progression", settings: "Réglages", bugReports: "Signalements",
                        }[t]}
                    </button>
                ))}
            </div>

            {tab !== "messages" && tab !== "progression" && tab !== "settings" && tab !== "bugReports" && (
                <div className="px-4 pb-2">
                    <input
                        type="search"
                        className={inputCls}
                        placeholder="Rechercher par nom ou id..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
            )}

            <main className="flex-1 overflow-y-auto px-4 pb-6 space-y-2">
                {tab !== "messages" && tab !== "progression" && tab !== "settings" && tab !== "bugReports" && (
                    <Button
                        variant="secondary"
                        size="sm"
                        className="w-full mb-2"
                        onClick={() =>
                            setEditing(
                                tab === "sets" ? { kind: "set", data: null }
                                    : tab === "boosters" ? { kind: "booster", data: null }
                                        : tab === "types" ? { kind: "type", data: null }
                                            : tab === "resources" ? { kind: "resource", data: null }
                                                : tab === "offers" ? { kind: "offer", data: null }
                                                    : { kind: "character", data: null }
                            )
                        }
                    >
                        ＋ Nouveau
                    </Button>
                )}

                {tab === "messages" && <AdminMessagesComposer resources={resources} />}
                {tab === "progression" && <AdminProgressionEditor resources={resources} boosters={boostersQ.data ?? []} />}
                {tab === "settings" && (
                    <div className="space-y-6">
                        <GameConfigSection />
                        <StartingResourcesSection />
                        <TuningSection />
                    </div>
                )}
                {tab === "bugReports" && <AdminBugReports />}

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
                                title={`${b.active ? "" : "[inactif] "}${b.name}  ·  ${b.id}`}
                                subtitle={`sets ${b.set_ids.join(", ")} — ${b.cards_count} cartes — ${b.price} ${b.resource_name}`
                                    + `${b.guaranteed_rare ? " — rare garantie" : ""}`
                                    + `${!b.visible_in_shop ? " — masqué de la boutique classique" : ""}`}
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
                                onEdit={() => setEditing({ kind: "type", data: t })}
                                onDelete={() => setToDelete({ kind: "types", id: t.id, label: `le type « ${t.name} »` })}
                            />
                        )))}

                {tab === "resources" &&
                    (resourcesQ.isLoading ? <p className="text-white/40 text-sm">…</p> :
                        filteredResources.map((r) => (
                            <Row key={r.id}
                                title={`${r.name}  ·  ${r.id}`}
                                subtitle={r.description || "—"}
                                onEdit={() => setEditing({ kind: "resource", data: r })}
                                onDelete={r.protected
                                    ? undefined
                                    : () => setToDelete({ kind: "resources", id: r.id, label: `la ressource « ${r.name} »` })}
                            />
                        )))}

                {tab === "offers" && (
                    <div className="bg-game-surface/40 border border-white/10 rounded-lg px-3 py-2 mb-2">
                        <p className="text-white/60 text-xs mb-1.5">
                            Booster du jour : {dailyFeatureQ.data
                                ? <span className="text-white font-semibold">{dailyFeatureQ.data.offer_name} (épinglé)</span>
                                : <span className="text-white/40">rotation automatique (pool "dans la rotation du jour")</span>}
                        </p>
                        <div className="flex gap-2">
                            <select className={inputCls + " flex-1"} value={pinChoice}
                                onChange={(e) => setPinChoice(e.target.value)}>
                                <option value="" disabled>Épingler une offre pour aujourd'hui…</option>
                                {(offersQ.data ?? []).map((o) => (
                                    <option key={o.id} value={o.id}>{o.name}</option>
                                ))}
                            </select>
                            <Button variant="secondary" size="sm" loading={pinFeature.isPending}
                                disabled={!pinChoice}
                                onClick={() => pinChoice && pinFeature.mutate(pinChoice)}>
                                Épingler
                            </Button>
                            {dailyFeatureQ.data && (
                                <Button variant="secondary" size="sm" loading={unpinFeature.isPending}
                                    onClick={() => unpinFeature.mutate()}>
                                    Retirer
                                </Button>
                            )}
                        </div>
                    </div>
                )}

                {tab === "offers" &&
                    (offersQ.isLoading ? <p className="text-white/40 text-sm">…</p> :
                        filteredOffers.map((o) => (
                            <div key={o.id} className="flex items-center justify-between bg-game-surface/60 border border-white/5 rounded-lg px-3 py-2 gap-2">
                                <button
                                    className="flex-1 min-w-0 text-left"
                                    onClick={() => setEditing({ kind: "offer", data: o })}
                                    title="Modifier cette offre"
                                >
                                    <p className={`text-sm font-semibold truncate ${o.active ? "text-white" : "text-white/30 line-through"}`}>
                                        {o.featured_today && "[mis en avant] "}{o.name}  ·  {o.id}
                                    </p>
                                    <p className="text-white/40 text-xs truncate">
                                        {o.kind} — {o.price} {o.resource_name}
                                        {o.purchase_limit_per_day ? ` — limite ${o.purchase_limit_per_day}/j` : ""}
                                        {o.is_daily_pool ? " — pool du jour" : ""}
                                        {o.kind === "booster" && o.force_min_rarity_name ? ` — min. ${o.force_min_rarity_name}` : ""}
                                        {o.kind === "booster" && o.rarity_weight_multiplier ? ` — x${o.rarity_weight_multiplier} rare+` : ""}
                                        {o.kind === "reroll" ? ` — ${[
                                            o.reroll_rarity && "rareté", o.reroll_quality && "qualité",
                                            o.reroll_specialty && "spécialité", o.reroll_jewelry && "jewelry",
                                            o.reroll_power && "puissance",
                                        ].filter(Boolean).join("+")} (${o.reroll_mode === "guaranteed_min" ? "garanti" : "aléatoire"})` : ""}
                                    </p>
                                </button>
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
                            : editing?.kind === "type" ? "Type"
                                : editing?.kind === "resource" ? "Ressource"
                                    : editing?.kind === "offer" ? (editing.data ? "Modifier l'offre" : "Nouvelle offre")
                                        : "Personnage"
                }
            >
                {editing?.kind === "set" && (
                    <SetForm initial={editing.data} onSaved={refresh} onClose={() => setEditing(null)} />
                )}
                {editing?.kind === "booster" && (
                    <BoosterForm initial={editing.data} sets={sets} resources={resources} onSaved={refresh} onClose={() => setEditing(null)} />
                )}
                {editing?.kind === "character" && (
                    <CharacterForm initial={editing.data} sets={sets} onSaved={refresh} onClose={() => setEditing(null)} />
                )}
                {editing?.kind === "type" && (
                    <TypeForm initial={editing.data} onSaved={refresh} onClose={() => setEditing(null)} />
                )}
                {editing?.kind === "resource" && (
                    <ResourceForm initial={editing.data} onSaved={refresh} onClose={() => setEditing(null)} />
                )}
                {editing?.kind === "offer" && (
                    <ShopOfferForm
                        initial={editing.data}
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
                confirmLabel="Supprimer"
                confirmVariant="danger"
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

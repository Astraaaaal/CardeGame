import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi, adminKey } from "@/api/admin";
import type {
    GameSet,
    AdminBooster,
    AdminCharacter,
    CharacterSetLink,
} from "@/types/content";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";

const inputCls =
    "w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white " +
    "placeholder-white/30 focus:border-accent focus:outline-none transition-colors";
const labelCls = "block text-white/60 text-xs mb-1";

const CHAR_TYPES = [
    "Plantes", "Feu", "Eau", "Électrique", "Ténèbres", "Lumière", "Glace",
    "Roche", "Vent", "Poison", "Métal", "Psychique", "Dragon", "Fée",
    "Combat", "Normal",
];

function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof r?.data?.detail === "string") return r.data.detail;
    }
    return "Erreur.";
}

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
    initial,
    onSaved,
    onClose,
}: {
    initial: GameSet | null;
    onSaved: () => void;
    onClose: () => void;
}) {
    const isNew = !initial;
    const [f, setF] = useState<GameSet>(
        initial ?? { id: "", name: "", description: "" }
    );
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
                <input
                    className={inputCls}
                    value={f.id}
                    disabled={!isNew}
                    placeholder="ex: A3"
                    onChange={(e) => setF({ ...f, id: e.target.value })}
                />
            </div>
            <div>
                <label className={labelCls}>Nom</label>
                <input
                    className={inputCls}
                    value={f.name}
                    onChange={(e) => setF({ ...f, name: e.target.value })}
                />
            </div>
            <div>
                <label className={labelCls}>Description</label>
                <textarea
                    className={inputCls}
                    rows={2}
                    value={f.description}
                    onChange={(e) => setF({ ...f, description: e.target.value })}
                />
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

/* ───────────────────────── Formulaire Booster ───────────────────────── */

function BoosterForm({
    initial,
    sets,
    onSaved,
    onClose,
}: {
    initial: AdminBooster | null;
    sets: GameSet[];
    onSaved: () => void;
    onClose: () => void;
}) {
    const isNew = !initial;
    const [f, setF] = useState<AdminBooster>(
        initial ?? {
            id: "", name: "", set_id: sets[0]?.id ?? "", cards_count: 5,
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

    return (
        <div className="space-y-3">
            <div>
                <label className={labelCls}>Identifiant</label>
                <input
                    className={inputCls}
                    value={f.id}
                    disabled={!isNew}
                    placeholder="ex: booster_A3"
                    onChange={(e) => setF({ ...f, id: e.target.value })}
                />
            </div>
            <div>
                <label className={labelCls}>Nom</label>
                <input className={inputCls} value={f.name}
                    onChange={(e) => setF({ ...f, name: e.target.value })} />
            </div>
            <div>
                <label className={labelCls}>Set</label>
                <select className={inputCls} value={f.set_id}
                    onChange={(e) => setF({ ...f, set_id: e.target.value })}>
                    {sets.map((s) => (
                        <option key={s.id} value={s.id}>{s.name} ({s.id})</option>
                    ))}
                </select>
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
                <Button variant="primary" className="flex-1" loading={m.isPending} onClick={() => m.mutate()}>
                    {isNew ? "Créer" : "Enregistrer"}
                </Button>
                <Button variant="secondary" onClick={onClose}>Annuler</Button>
            </div>
        </div>
    );
}

/* ──────────────────────── Formulaire Personnage ─────────────────────── */

function CharacterForm({
    initial,
    sets,
    onSaved,
    onClose,
}: {
    initial: AdminCharacter | null;
    sets: GameSet[];
    onSaved: () => void;
    onClose: () => void;
}) {
    const isNew = !initial;
    const [f, setF] = useState<AdminCharacter>(
        initial ?? {
            id: "", name: "", description: "", type: "Normal", gen: 1,
            image_url: "", sets: [],
        }
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
    const rmLink = (i: number) =>
        setF({ ...f, sets: f.sets.filter((_, j) => j !== i) });

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
                    {CHAR_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
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
                                {sets.map((s) => (
                                    <option key={s.id} value={s.id}>{s.id}</option>
                                ))}
                            </select>
                            <input type="number" step="0.1" className={inputCls + " w-24"}
                                value={l.weight}
                                onChange={(e) => setLink(i, { weight: +e.target.value })} />
                            <button className="text-red-400 text-lg px-1" onClick={() => rmLink(i)}>
                                ×
                            </button>
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

/* ─────────────────────────────── Panneau ────────────────────────────── */

type Tab = "sets" | "boosters" | "characters";

function Panel() {
    const navigate = useNavigate();
    const qc = useQueryClient();
    const [tab, setTab] = useState<Tab>("characters");
    const [editing, setEditing] = useState<
        | { kind: "set"; data: GameSet | null }
        | { kind: "booster"; data: AdminBooster | null }
        | { kind: "character"; data: AdminCharacter | null }
        | null
    >(null);

    const setsQ = useQuery({ queryKey: ["admin", "sets"], queryFn: adminApi.listSets });
    const boostersQ = useQuery({ queryKey: ["admin", "boosters"], queryFn: adminApi.listBoosters, enabled: tab === "boosters" });
    const charsQ = useQuery({ queryKey: ["admin", "characters"], queryFn: adminApi.listCharacters, enabled: tab === "characters" });

    const sets = setsQ.data ?? [];

    const refresh = () => {
        qc.invalidateQueries({ queryKey: ["admin"] });
        setEditing(null);
    };

    const del = useMutation({
        mutationFn: async (x: { kind: Tab; id: string }) => {
            if (x.kind === "sets") return adminApi.deleteSet(x.id);
            if (x.kind === "boosters") return adminApi.deleteBooster(x.id);
            return adminApi.deleteCharacter(x.id);
        },
        onSuccess: refresh,
        onError: (e) => alert(errMsg(e)),
    });

    const askDelete = (kind: Tab, id: string) => {
        if (confirm(`Supprimer « ${id} » ?`)) del.mutate({ kind, id });
    };

    const Row = ({
        title, subtitle, onEdit, onDelete,
    }: { title: string; subtitle: string; onEdit: () => void; onDelete: () => void }) => (
        <div className="flex items-center justify-between bg-game-surface/60 border border-white/5 rounded-lg px-3 py-2">
            <button className="text-left flex-1 min-w-0" onClick={onEdit}>
                <p className="text-white text-sm font-semibold truncate">{title}</p>
                <p className="text-white/40 text-xs truncate">{subtitle}</p>
            </button>
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

            <div className="px-4 py-3 flex gap-2">
                {(["characters", "boosters", "sets"] as Tab[]).map((t) => (
                    <button
                        key={t}
                        className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${tab === t ? "bg-accent text-white" : "bg-white/10 text-white/50 hover:bg-white/20"
                            }`}
                        onClick={() => setTab(t)}
                    >
                        {t === "characters" ? "Personnages" : t === "boosters" ? "Boosters" : "Sets"}
                    </button>
                ))}
            </div>

            <main className="flex-1 overflow-y-auto px-4 pb-6 space-y-2">
                <Button
                    variant="secondary"
                    size="sm"
                    className="w-full mb-2"
                    onClick={() =>
                        setEditing(
                            tab === "sets"
                                ? { kind: "set", data: null }
                                : tab === "boosters"
                                    ? { kind: "booster", data: null }
                                    : { kind: "character", data: null }
                        )
                    }
                >
                    ＋ Nouveau
                </Button>

                {tab === "sets" &&
                    (setsQ.isLoading ? <p className="text-white/40 text-sm">…</p> :
                        sets.map((s) => (
                            <Row key={s.id}
                                title={`${s.name}  ·  ${s.id}`}
                                subtitle={`${s.booster_count ?? 0} booster(s), ${s.character_count ?? 0} perso(s) — ${s.description}`}
                                onEdit={() => setEditing({ kind: "set", data: s })}
                                onDelete={() => askDelete("sets", s.id)}
                            />
                        )))}

                {tab === "boosters" &&
                    (boostersQ.isLoading ? <p className="text-white/40 text-sm">…</p> :
                        (boostersQ.data ?? []).map((b) => (
                            <Row key={b.id}
                                title={`${b.name}  ·  ${b.id}`}
                                subtitle={`set ${b.set_id} — ${b.cards_count} cartes — ${b.price} 🪙${b.guaranteed_rare ? " — rare garantie" : ""}`}
                                onEdit={() => setEditing({ kind: "booster", data: b })}
                                onDelete={() => askDelete("boosters", b.id)}
                            />
                        )))}

                {tab === "characters" &&
                    (charsQ.isLoading ? <p className="text-white/40 text-sm">…</p> :
                        (charsQ.data ?? []).map((c) => (
                            <Row key={c.id}
                                title={`${c.name}  ·  ${c.id}`}
                                subtitle={`${c.type} · Gen ${c.gen} · sets: ${c.sets.map((l) => `${l.set_id}(${l.weight})`).join(", ") || "aucun"}`}
                                onEdit={() => setEditing({ kind: "character", data: c })}
                                onDelete={() => askDelete("characters", c.id)}
                            />
                        )))}
            </main>

            <Modal
                open={!!editing}
                onClose={() => setEditing(null)}
                title={
                    editing?.kind === "set" ? "Set"
                        : editing?.kind === "booster" ? "Booster"
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
            </Modal>
        </div>
    );
}

export default function AdminPanel() {
    const [authed, setAuthed] = useState(!!adminKey.get());
    if (!authed) return <KeyGate onOk={() => setAuthed(true)} />;
    return <Panel />;
}

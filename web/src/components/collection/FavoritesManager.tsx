import { useState } from "react";
import { toast } from "@/stores/toastStore";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FAVORITE_COLORS, favoritesApi, type FavoriteCategory } from "@/api/favorites";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import { errMsg } from "@/utils/errors";

export const FAVORITES_KEY = ["favorites"];
const MAX = 10;
const inputCls = "flex-1 min-w-0 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30";

function ColorPicker({ value, onChange }: { value: string; onChange: (c: string) => void }) {
    return (
        <div className="flex flex-wrap gap-1.5">
            {FAVORITE_COLORS.map((c) => (
                <button key={c} type="button" aria-label={c}
                    className={`w-6 h-6 rounded-full border-2 ${value === c ? "border-white" : "border-transparent"}`}
                    style={{ background: c }} onClick={() => onChange(c)} />
            ))}
        </div>
    );
}

/** Création, renommage, couleur et suppression des catégories de favoris (10 au plus). */
export default function FavoritesManager({ open, onClose }: { open: boolean; onClose: () => void }) {
    const qc = useQueryClient();
    const { data: cats } = useQuery({ queryKey: FAVORITES_KEY, queryFn: favoritesApi.list });
    const [name, setName] = useState("");
    const [color, setColor] = useState(FAVORITE_COLORS[0]);
    const [editing, setEditing] = useState<FavoriteCategory | null>(null);
    const setErr = (m: string | null) => { if (m) toast.error(m); };

    const onSuccess = (list: FavoriteCategory[]) => {
        qc.setQueryData(FAVORITES_KEY, list);
        qc.invalidateQueries({ queryKey: ["collection"] });
        qc.invalidateQueries({ queryKey: ["card-copies"] });
        setErr("");
    };
    const onError = (e: unknown) => setErr(errMsg(e));
    const create = useMutation({
        mutationFn: () => favoritesApi.create(name.trim(), color),
        onSuccess: (l) => { onSuccess(l); setName(""); }, onError,
    });
    const save = useMutation({
        mutationFn: (c: FavoriteCategory) => favoritesApi.update(c.id, c.name.trim(), c.color),
        onSuccess: (l) => { onSuccess(l); setEditing(null); }, onError,
    });
    const remove = useMutation({ mutationFn: (id: number) => favoritesApi.remove(id), onSuccess, onError });

    return (
        <Modal open={open} onClose={onClose} title="Mes favoris">
            <div className="space-y-4">
                <p className="text-white/40 text-xs">
                    Jusqu'à {MAX} catégories. Range tes cartes depuis leur détail, puis filtre ta collection.
                </p>
                {(cats ?? []).map((c) => (
                    editing?.id === c.id ? (
                        <div key={c.id} className="bg-black/20 rounded-xl p-3 space-y-2">
                            <div className="flex gap-2">
                                <input className={inputCls} maxLength={24} value={editing.name}
                                    onChange={(e) => setEditing({ ...editing, name: e.target.value })} />
                                <Button size="sm" disabled={!editing.name.trim()} loading={save.isPending} success={save.isSuccess} onClick={() => save.mutate(editing)}>OK</Button>
                            </div>
                            <ColorPicker value={editing.color} onChange={(col) => setEditing({ ...editing, color: col })} />
                        </div>
                    ) : (
                        <div key={c.id} className="flex items-center gap-2 bg-black/20 rounded-xl px-3 py-2">
                            <span className="w-3 h-3 rounded-full shrink-0" style={{ background: c.color }} />
                            <span className="flex-1 text-white text-sm truncate">{c.name}</span>
                            <span className="text-white/40 text-xs">{c.count}</span>
                            <button className="text-white/50 hover:text-white text-xs px-1" onClick={() => setEditing(c)}>✎</button>
                            <button className="text-red-400/70 hover:text-red-400 text-xs px-1"
                                onClick={() => window.confirm(`Supprimer la catégorie « ${c.name} » ? Les cartes ne sont pas supprimées.`) && remove.mutate(c.id)}>
                                🗑
                            </button>
                        </div>
                    )
                ))}
                {(cats?.length ?? 0) < MAX && (
                    <div className="border-t border-white/10 pt-3 space-y-2">
                        <div className="flex gap-2">
                            <input className={inputCls} maxLength={24} placeholder="Nouvelle catégorie" value={name}
                                onChange={(e) => setName(e.target.value)} />
                            <Button size="sm" disabled={!name.trim()} loading={create.isPending} success={create.isSuccess} onClick={() => create.mutate()}>Créer</Button>
                        </div>
                        <ColorPicker value={color} onChange={setColor} />
                    </div>
                )}
            </div>
        </Modal>
    );
}

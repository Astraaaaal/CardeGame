import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { showcaseApi } from "@/api/showcase";
import { useAuthStore } from "@/stores/authStore";
import { useCollection } from "@/hooks/useCollection";
import type { Card } from "@/types/card";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import CardImage from "@/components/card/CardImage";
import CardPickerModal from "@/components/card/CardPickerModal";

function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof r?.data?.detail === "string") return r.data.detail;
    }
    return "Erreur.";
}

/** Sélecteur d'avatar : un des personnages possédés (déduplique les variantes). */
function AvatarPickerModal({
    onPick, onClose,
}: { onPick: (characterId: string, imageUrl: string) => void; onClose: () => void }) {
    const { data } = useCollection({ sort_by: "name" });
    const characters = useMemo(() => {
        const seen = new Map<string, { id: string; name: string; image_url: string }>();
        for (const g of data?.groups ?? []) {
            if (!seen.has(g.card.character_id)) {
                seen.set(g.card.character_id, {
                    id: g.card.character_id, name: g.card.character_name, image_url: g.card.image_url,
                });
            }
        }
        return [...seen.values()];
    }, [data]);

    return (
        <Modal open onClose={onClose} title="Choisis un avatar">
            {characters.length === 0 ? (
                <p className="text-white/40 text-sm text-center py-6">
                    Tu dois posséder au moins un personnage pour choisir un avatar.
                </p>
            ) : (
                <div className="grid grid-cols-4 gap-3 max-h-[60vh] overflow-y-auto">
                    {characters.map((c) => (
                        <button
                            key={c.id}
                            className="flex flex-col items-center gap-1"
                            onClick={() => onPick(c.id, c.image_url)}
                        >
                            <div className="w-16 h-16 rounded-full overflow-hidden border-2 border-white/10 hover:border-accent transition-colors">
                                <img src={`/characters/${c.image_url}`} alt="" className="w-full h-full object-cover" />
                            </div>
                            <span className="text-white/60 text-[10px] truncate w-16 text-center">{c.name}</span>
                        </button>
                    ))}
                </div>
            )}
        </Modal>
    );
}

export default function ShowcaseEditor() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const qc = useQueryClient();

    const { data: showcase, isLoading } = useQuery({
        queryKey: ["showcase", user?.id],
        queryFn: () => showcaseApi.get(user!.id),
        enabled: !!user,
    });
    const { data: collection } = useCollection({ sort_by: "rarity" });

    const [avatarId, setAvatarId] = useState<string | null>(null);
    const [avatarImg, setAvatarImg] = useState<string | null>(null);
    const [slots, setSlots] = useState<(string | null)[]>([null, null, null]);
    const [initialized, setInitialized] = useState(false);
    const [avatarPickerOpen, setAvatarPickerOpen] = useState(false);
    const [slotPicker, setSlotPicker] = useState<number | null>(null);
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

    useEffect(() => {
        if (showcase && !initialized) {
            setAvatarId(showcase.avatar?.character_id ?? null);
            setAvatarImg(showcase.avatar?.image_url ?? null);
            setSlots([0, 1, 2].map((i) => showcase.cards[i]?.id ?? null));
            setInitialized(true);
        }
    }, [showcase, initialized]);

    // Fusionne la collection actuelle + les cartes déjà en vitrine : une carte
    // choisie il y a longtemps peut ne plus être "représentative" de son groupe
    // dans /collection (ordre non garanti côté BDD) sans pour autant avoir été recyclée.
    const cardById = useMemo(() => {
        const map = new Map<string, Card>();
        for (const g of collection?.groups ?? []) map.set(g.card.id, g.card);
        for (const c of showcase?.cards ?? []) map.set(c.id, c);
        return map;
    }, [collection, showcase]);

    const save = useMutation({
        mutationFn: () => showcaseApi.update(avatarId, slots),
        onSuccess: (updated) => {
            qc.setQueryData(["showcase", user?.id], updated);
            setMsg({ text: "Vitrine enregistrée.", ok: true });
        },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    if (isLoading) return <p className="text-white/40 text-sm">Chargement...</p>;

    return (
        <div className="space-y-6">
            <div className="bg-game-surface rounded-2xl border border-white/10 p-4">
                <h3 className="text-white font-bold text-sm mb-3">Avatar</h3>
                <button
                    className="w-20 h-20 rounded-full overflow-hidden border-2 border-white/10 hover:border-accent
                               bg-black/30 flex items-center justify-center transition-colors"
                    onClick={() => setAvatarPickerOpen(true)}
                >
                    {avatarImg ? (
                        <img src={`/characters/${avatarImg}`} alt="" className="w-full h-full object-cover" />
                    ) : (
                        <span className="text-3xl text-white/20">?</span>
                    )}
                </button>
                <p className="text-white/30 text-xs mt-2">Clique pour choisir un personnage possédé.</p>
            </div>

            <div className="bg-game-surface rounded-2xl border border-white/10 p-4">
                <h3 className="text-white font-bold text-sm mb-3">Cartes mises en avant (3 max)</h3>
                <div className="grid grid-cols-3 gap-2">
                    {slots.map((slotId, i) => {
                        const card = slotId ? cardById.get(slotId) : undefined;
                        return (
                            <div key={i} className="space-y-1">
                                {card ? (
                                    <button onClick={() => setSlotPicker(i)} className="w-full">
                                        <CardImage card={card} size="sm" />
                                    </button>
                                ) : (
                                    <button
                                        onClick={() => setSlotPicker(i)}
                                        className="w-full aspect-[5/7] rounded-lg border-2 border-dashed border-white/15
                                                   text-white/30 text-xs flex items-center justify-center hover:border-accent hover:text-accent transition-colors"
                                    >
                                        + Choisir
                                    </button>
                                )}
                                {card && (
                                    <button
                                        className="text-red-400/70 hover:text-red-400 text-[10px] w-full text-center"
                                        onClick={() => setSlots((s) => s.map((v, j) => (j === i ? null : v)))}
                                    >
                                        Retirer
                                    </button>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {msg && (
                <p className={`text-xs ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>
            )}

            <div className="flex gap-2">
                <Button variant="primary" className="flex-1" loading={save.isPending} onClick={() => save.mutate()}>
                    Enregistrer
                </Button>
                <Button
                    variant="secondary"
                    onClick={() => user && navigate(`/players/${user.id}`)}
                >
                    👁️ Voir comme un autre joueur
                </Button>
            </div>

            {avatarPickerOpen && (
                <AvatarPickerModal
                    onClose={() => setAvatarPickerOpen(false)}
                    onPick={(characterId, imageUrl) => {
                        setAvatarId(characterId);
                        setAvatarImg(imageUrl);
                        setAvatarPickerOpen(false);
                    }}
                />
            )}
            {slotPicker !== null && (
                <CardPickerModal
                    onClose={() => setSlotPicker(null)}
                    onPick={(cardId) => {
                        setSlots((s) => s.map((v, j) => (j === slotPicker ? cardId : v)));
                        setSlotPicker(null);
                    }}
                />
            )}
        </div>
    );
}

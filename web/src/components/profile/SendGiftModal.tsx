import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { messagesApi } from "@/api/messages";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import CardImage from "@/components/card/CardImage";
import ResourceIcon from "@/components/ui/ResourceIcon";
import AddResourceModal from "@/components/trade/AddResourceModal";
import AddBoosterModal from "@/components/trade/AddBoosterModal";
import type { Card } from "@/types/card";

function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof r?.data?.detail === "string") return r.data.detail;
    }
    return "Erreur.";
}

export interface SendGiftInitialState {
    username: string;
    subject: string;
    body: string;
    pickedCard: { id: string; preview: Card } | null;
}

interface SendGiftModalProps {
    presetUsername?: string;
    /** Chemin de la page qui monte ce modal — sert de point de retour après
     * être passé par la Collection pour choisir une carte. */
    returnTo: string;
    /** D'où vient l'ouverture (ligne d'ami vs messagerie) — transporté dans le
     * contexte de sélection pour que le parent sache quel onglet restaurer. */
    origin: "friend" | "inbox";
    initialState?: SendGiftInitialState;
    onClose: () => void;
    onSent?: () => void;
}

export default function SendGiftModal({ presetUsername, returnTo, origin, initialState, onClose, onSent }: SendGiftModalProps) {
    const navigate = useNavigate();
    const requestSelection = useCardSelectionStore((s) => s.requestSelection);

    const [username, setUsername] = useState(initialState?.username ?? presetUsername ?? "");
    const [subject, setSubject] = useState(initialState?.subject ?? "Cadeau");
    const [body, setBody] = useState(initialState?.body ?? "");
    const [pickedCard, setPickedCard] = useState<{ id: string; preview: Card } | null>(initialState?.pickedCard ?? null);
    const [pickedResource, setPickedResource] = useState<{ id: string; amount: number } | null>(null);
    const [pickedBooster, setPickedBooster] = useState<{ id: string; name: string; quantity: number } | null>(null);
    const [resourcePickerOpen, setResourcePickerOpen] = useState(false);
    const [boosterPickerOpen, setBoosterPickerOpen] = useState(false);
    const [err, setErr] = useState("");

    const send = useMutation({
        mutationFn: () => {
            if (pickedCard) {
                return messagesApi.sendGift({
                    username: username.trim(), subject, body, item_type: "card", user_card_id: pickedCard.id,
                });
            }
            if (pickedBooster) {
                return messagesApi.sendGift({
                    username: username.trim(), subject, body, item_type: "booster",
                    booster_id: pickedBooster.id, amount: pickedBooster.quantity,
                });
            }
            return messagesApi.sendGift({
                username: username.trim(), subject, body, item_type: "resource",
                resource_id: pickedResource!.id, amount: pickedResource!.amount,
            });
        },
        onSuccess: () => { onSent?.(); onClose(); },
        onError: (e) => setErr(errMsg(e)),
    });

    const canSend = !!username.trim() && (!!pickedCard || !!pickedResource || !!pickedBooster);

    const chooseCard = () => {
        requestSelection({
            max: 1,
            title: "Choisis une carte à offrir",
            excludeIds: [],
            returnTo,
            context: { purpose: "gift", origin, username, subject, body },
        });
        onClose();
        navigate("/collection");
    };

    return (
        <>
            <Modal open onClose={onClose} title="Envoyer un cadeau">
                <div className="space-y-3">
                    {!presetUsername && (
                        <input
                            className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30"
                            placeholder="Pseudo du destinataire..."
                            value={username}
                            onChange={(e) => { setUsername(e.target.value); setErr(""); }}
                        />
                    )}

                    <div className="flex gap-2">
                        <input
                            className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                            placeholder="Objet"
                            maxLength={100}
                            value={subject}
                            onChange={(e) => setSubject(e.target.value)}
                        />
                    </div>
                    <textarea
                        className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 resize-none"
                        placeholder="Petit mot (optionnel)..."
                        rows={2}
                        maxLength={2000}
                        value={body}
                        onChange={(e) => setBody(e.target.value)}
                    />

                    {pickedCard ? (
                        <div className="flex items-center gap-3 bg-black/20 border border-white/5 rounded-lg p-2">
                            <div className="w-16 shrink-0">
                                <CardImage card={pickedCard.preview} size="sm" />
                            </div>
                            <span className="flex-1 text-white text-sm">{pickedCard.preview.character_name}</span>
                            <button className="text-white/40 hover:text-red-400 text-xs" onClick={() => setPickedCard(null)}>
                                Retirer
                            </button>
                        </div>
                    ) : pickedResource ? (
                        <div className="flex items-center gap-3 bg-black/20 border border-white/5 rounded-lg p-3">
                            <ResourceIcon resourceId={pickedResource.id} className="w-6 h-6" />
                            <span className="flex-1 text-white text-sm font-bold">
                                {pickedResource.amount.toLocaleString("fr-FR")}
                            </span>
                            <button className="text-white/40 hover:text-red-400 text-xs" onClick={() => setPickedResource(null)}>
                                Retirer
                            </button>
                        </div>
                    ) : pickedBooster ? (
                        <div className="flex items-center gap-3 bg-black/20 border border-white/5 rounded-lg p-3">
                            <span className="flex-1 text-white text-sm font-bold">
                                {pickedBooster.name} ×{pickedBooster.quantity}
                            </span>
                            <button className="text-white/40 hover:text-red-400 text-xs" onClick={() => setPickedBooster(null)}>
                                Retirer
                            </button>
                        </div>
                    ) : (
                        <div className="flex gap-2 flex-wrap">
                            <Button variant="secondary" size="sm" className="flex-1" onClick={chooseCard}>
                                Choisir une carte
                            </Button>
                            <Button variant="secondary" size="sm" className="flex-1" onClick={() => setResourcePickerOpen(true)}>
                                + Choisir une ressource
                            </Button>
                            <Button variant="secondary" size="sm" className="flex-1" onClick={() => setBoosterPickerOpen(true)}>
                                Choisir un booster
                            </Button>
                        </div>
                    )}

                    {err && <p className="text-red-400 text-xs">{err}</p>}

                    <Button variant="gold" className="w-full" disabled={!canSend} loading={send.isPending} onClick={() => send.mutate()}>
                        Envoyer le cadeau
                    </Button>
                </div>
            </Modal>

            {resourcePickerOpen && (
                <AddResourceModal
                    current={{}}
                    onPick={(resourceId, amount) => { setPickedResource({ id: resourceId, amount }); setResourcePickerOpen(false); }}
                    onClose={() => setResourcePickerOpen(false)}
                />
            )}
            {boosterPickerOpen && (
                <AddBoosterModal
                    onPick={(boosterId, name, quantity) => { setPickedBooster({ id: boosterId, name, quantity }); setBoosterPickerOpen(false); }}
                    onClose={() => setBoosterPickerOpen(false)}
                />
            )}
        </>
    );
}

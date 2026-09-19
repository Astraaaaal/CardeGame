import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { messagesApi } from "@/api/messages";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import CardImage from "@/components/card/CardImage";
import ResourceIcon from "@/components/ui/ResourceIcon";
import InventoryItemPicker, { type InventoryItem } from "@/components/inventory/InventoryItemPicker";
import type { Card } from "@/types/card";
import { errMsg } from "@/utils/errors";
import EmojiPicker from "@/components/ui/EmojiPicker";

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
    const qc = useQueryClient();

    const [username, setUsername] = useState(initialState?.username ?? presetUsername ?? "");
    const [subject, setSubject] = useState(initialState?.subject ?? "Cadeau");
    const [body, setBody] = useState(initialState?.body ?? "");
    const subjectRef = useRef<HTMLInputElement>(null);
    const bodyRef = useRef<HTMLTextAreaElement>(null);
    const [pickedCard, setPickedCard] = useState<{ id: string; preview: Card } | null>(initialState?.pickedCard ?? null);
    const [pickedItem, setPickedItem] = useState<InventoryItem | null>(null);
    const [itemPickerOpen, setItemPickerOpen] = useState(false);
    const [err, setErr] = useState("");

    const send = useMutation({
        mutationFn: () => {
            if (pickedCard) {
                return messagesApi.sendGift({
                    username: username.trim(), subject, body, item_type: "card", user_card_id: pickedCard.id,
                });
            }
            const item = pickedItem!;
            const base = { username: username.trim(), subject, body, amount: item.amount };
            if (item.kind === "booster") {
                return messagesApi.sendGift({
                    ...base, item_type: "booster", booster_id: item.boosterId, bonus_id: item.bonusId ?? undefined,
                });
            }
            if (item.kind === "reroll") {
                return messagesApi.sendGift({ ...base, item_type: "reroll", reroll_token_id: item.tokenId });
            }
            return messagesApi.sendGift({ ...base, item_type: "resource", resource_id: item.resourceId });
        },
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["booster-inventory"] });
            qc.invalidateQueries({ queryKey: ["reroll-tokens"] });
            onSent?.();
            onClose();
        },
        onError: (e) => setErr(errMsg(e)),
    });

    const canSend = !!username.trim() && (!!pickedCard || !!pickedItem);

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
                            ref={subjectRef}
                            className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                            placeholder="Objet"
                            maxLength={100}
                            value={subject}
                            onChange={(e) => setSubject(e.target.value)}
                        />
                        <EmojiPicker target={subjectRef} value={subject} onChange={setSubject} />
                    </div>
                    <div className="flex gap-2 items-start">
                    <textarea
                        ref={bodyRef}
                        className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 resize-none"
                        placeholder="Petit mot (optionnel)..."
                        rows={2}
                        maxLength={2000}
                        value={body}
                        onChange={(e) => setBody(e.target.value)}
                    />
                    <EmojiPicker target={bodyRef} value={body} onChange={setBody} />
                    </div>

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
                    ) : pickedItem ? (
                        <div className="flex items-center gap-3 bg-black/20 border border-white/5 rounded-lg p-3">
                            {pickedItem.kind === "resource" ? (
                                <ResourceIcon resourceId={pickedItem.resourceId} className="w-6 h-6" />
                            ) : (
                                <span className="text-xl">{pickedItem.kind === "booster" ? "🎴" : "🎲"}</span>
                            )}
                            <span className="flex-1 text-white text-sm font-bold">
                                {pickedItem.kind === "resource"
                                    ? `${pickedItem.amount.toLocaleString("fr-FR")} ${pickedItem.name}`
                                    : `${pickedItem.name} ×${pickedItem.amount}`}
                            </span>
                            <button className="text-white/40 hover:text-red-400 text-xs" onClick={() => setPickedItem(null)}>
                                Retirer
                            </button>
                        </div>
                    ) : (
                        <div className="flex gap-2 flex-wrap">
                            <Button variant="secondary" size="sm" className="flex-1" onClick={chooseCard}>
                                Choisir une carte
                            </Button>
                            <Button variant="secondary" size="sm" className="flex-1" onClick={() => setItemPickerOpen(true)}>
                                + Choisir un objet
                            </Button>
                        </div>
                    )}

                    {err && <p className="text-red-400 text-xs">{err}</p>}

                    <Button variant="gold" className="w-full" disabled={!canSend} loading={send.isPending} onClick={() => send.mutate()}>
                        Envoyer le cadeau
                    </Button>
                </div>
            </Modal>

            {itemPickerOpen && (
                <InventoryItemPicker
                    onPick={(item) => { setPickedItem(item); setItemPickerOpen(false); }}
                    onClose={() => setItemPickerOpen(false)}
                />
            )}
        </>
    );
}

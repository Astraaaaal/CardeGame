import { useState } from "react";
import { BoosterIcon, RerollIcon } from "@/components/ui/ItemIcon";
import { toast } from "@/stores/toastStore";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { messagesApi } from "@/api/messages";
import type { AppMessage } from "@/types/message";
import Button from "@/components/ui/Button";
import CardImage from "@/components/card/CardImage";
import ResourceIcon from "@/components/ui/ResourceIcon";
import { errMsg } from "@/utils/errors";
import { rewardItems, showRewards, type RewardItem } from "@/stores/rewardPopupStore";
import EmojiText from "@/components/ui/EmojiText";

function fmt(iso: string): string {
    return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function MessageRow({ message }: { message: AppMessage }) {
    const qc = useQueryClient();
    const [open, setOpen] = useState(false);
    const setErr = (m: string | null) => { if (m) toast.error(m); };

    const markRead = useMutation({
        mutationFn: () => messagesApi.markRead(message.id),
        onSuccess: (m) => {
            qc.setQueryData<AppMessage[]>(["messages"], (old) => old?.map((x) => x.id === m.id ? m : x));
            qc.invalidateQueries({ queryKey: ["messages-unread-count"] });
        },
    });
    const claim = useMutation({
        mutationFn: () => messagesApi.claim(message.id),
        onSuccess: (m) => {
            if (m.claimed_at && !m.claim_error) {
                const items: RewardItem[] = rewardItems(m);
                if (m.reward_card) items.push({ kind: "card", card: m.reward_card });
                for (const r of m.reward_items) {
                    if (r.kind === "resource" && r.resource_id) items.push({ kind: "resource", resourceId: r.resource_id, amount: r.quantity, name: r.name });
                    if (r.kind === "booster" && r.booster_id) items.push({ kind: "booster", boosterId: r.booster_id, quantity: r.quantity, name: r.label ?? r.name });
                    if (r.kind === "reroll") items.push({ kind: "reroll_token", name: r.name, quantity: r.quantity });
                    if (r.kind === "card" && r.card) items.push({ kind: "card", card: r.card });
                }
                if (m.reward_reroll_label && m.reward_reroll_qty) {
                    items.push({ kind: "reroll_token", name: m.reward_reroll_label, quantity: m.reward_reroll_qty });
                }
                showRewards({ title: m.subject || "Cadeau", items });
            }
            qc.invalidateQueries({ queryKey: ["booster-inventory"] });
            qc.invalidateQueries({ queryKey: ["reroll-tokens"] });
            qc.setQueryData<AppMessage[]>(["messages"], (old) => old?.map((x) => x.id === m.id ? m : x));
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["collection"] });
            qc.invalidateQueries({ queryKey: ["messages-unread-count"] });
        },
        onError: (e) => setErr(errMsg(e)),
    });
    const remove = useMutation({
        mutationFn: () => messagesApi.remove(message.id),
        onSuccess: () => qc.setQueryData<AppMessage[]>(["messages"], (old) => old?.filter((x) => x.id !== message.id)),
        onError: (e) => setErr(errMsg(e)),
    });

    const toggle = () => {
        setOpen((v) => !v);
        if (!message.read_at) markRead.mutate();
    };

    const unclaimedReward = message.has_reward && !message.claimed_at;

    return (
        <div className="bg-game-surface rounded-2xl border border-white/10 overflow-hidden">
            <button className="w-full flex items-center gap-2 px-4 py-3 text-left" onClick={toggle}>
                {!message.read_at && <span className="w-2 h-2 rounded-full bg-accent shrink-0" />}
                <div className="flex-1 min-w-0">
                    <p className="text-white text-sm font-semibold truncate"><EmojiText text={message.subject} /></p>
                    <p className="text-white/40 text-xs">
                        {message.sender_display_name} · {fmt(message.created_at)}
                    </p>
                </div>
                {unclaimedReward && <span className="text-gold text-xs font-bold shrink-0">Cadeau</span>}
                <span className="text-white/30 text-xs shrink-0">{open ? "▲" : "▼"}</span>
            </button>

            {open && (
                <div className="px-4 pb-4 space-y-3">
                    {message.body && <p className="text-white/70 text-sm whitespace-pre-wrap"><EmojiText text={message.body} /></p>}

                    {message.reward_card && (
                        <div className="flex items-center gap-3 bg-black/20 rounded-lg p-2">
                            <div className="w-16 shrink-0">
                                <CardImage card={message.reward_card} size="sm" />
                            </div>
                            <span className="text-white text-sm">{message.reward_card.character_name}</span>
                        </div>
                    )}
                    {message.reward_resource_id && message.reward_amount != null && (
                        <div className="flex items-center gap-2 bg-black/20 rounded-lg p-3">
                            <ResourceIcon resourceId={message.reward_resource_id} className="w-5 h-5" />
                            <span className="text-white text-sm font-bold">
                                {message.reward_amount.toLocaleString("fr-FR")} {message.reward_resource_name}
                            </span>
                        </div>
                    )}
                    {message.reward_booster_id && message.reward_booster_qty != null && (
                        <div className="flex items-center gap-3 bg-black/20 rounded-lg p-2">
                            {message.reward_booster_cover_url && (
                                <img
                                    src={`/boosters/${message.reward_booster_cover_url}`}
                                    alt=""
                                    className="w-10 h-10 rounded object-cover shrink-0"
                                />
                            )}
                            <span className="text-white text-sm">
                                {message.reward_booster_name} ×{message.reward_booster_qty}
                                {message.reward_booster_label && (
                                    <span className="block text-gold text-xs">{message.reward_booster_label}</span>
                                )}
                            </span>
                        </div>
                    )}
                    {message.reward_reroll_label && message.reward_reroll_qty != null && (
                        <div className="flex items-center gap-2 bg-black/20 rounded-lg p-3">
                            <RerollIcon className="w-5 h-5 text-white/80" />
                            <span className="text-white text-sm">
                                {message.reward_reroll_label} ×{message.reward_reroll_qty}
                            </span>
                        </div>
                    )}

                    {message.reward_items.map((r, i) => (
                        <div key={i} className="flex items-center gap-3 bg-black/20 rounded-lg p-2">
                            {r.kind === "card" && r.card ? (
                                <div className="w-12 shrink-0"><CardImage card={r.card} size="sm" /></div>
                            ) : r.kind === "resource" && r.resource_id ? (
                                <ResourceIcon resourceId={r.resource_id} className="w-5 h-5" />
                            ) : (
                                r.kind === "booster" ? <BoosterIcon className="w-5 h-5 text-white/80" /> : <RerollIcon className="w-5 h-5 text-white/80" />
                            )}
                            <span className="text-white text-sm">
                                {r.kind === "resource" ? `${r.quantity.toLocaleString("fr-FR")} ${r.name}`
                                    : r.kind === "card" && r.card
                                        ? [r.card.character_name, r.card.rarity_name, r.card.quality_name].filter(Boolean).join(" · ")
                                        : `${r.name} ×${r.quantity}`}
                                {r.label && <span className="block text-gold text-xs">{r.label}</span>}
                            </span>
                        </div>
                    ))}

                    {message.claim_error && (
                        <p className="text-red-400 text-xs">{message.claim_error}</p>
                    )}

                    <div className="flex items-center gap-2">
                        {unclaimedReward && (
                            <Button variant="gold" size="sm" className="flex-1" loading={claim.isPending} success={claim.isSuccess} onClick={() => claim.mutate()}>
                                {message.tax > 0 ? `Récupérer (taxe ${message.tax.toLocaleString("fr-FR")} pièces)` : "Récupérer"}
                            </Button>
                        )}
                        {message.claimed_at && message.has_reward && (
                            <span className="flex-1 text-center text-green-400 text-xs font-semibold py-1.5">
                                Récupéré
                            </span>
                        )}
                        {!unclaimedReward && (
                            <button
                                className="text-white/40 hover:text-red-400 text-xs"
                                onClick={() => remove.mutate()}
                                disabled={remove.isPending}
                            >
                                Supprimer
                            </button>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

interface MessagesInboxProps {
    /** La modale de cadeau est possédée par le panneau parent (FriendsPanel) —
     * un seul propriétaire évite une course entre deux `consumeResult()` au
     * retour de la Collection en mode sélection. */
    onSendGift: () => void;
}

export default function MessagesInbox({ onSendGift }: MessagesInboxProps) {
    const { data, isLoading } = useQuery({ queryKey: ["messages"], queryFn: messagesApi.list });

    return (
        <div className="space-y-3">
            <Button variant="primary" size="sm" className="w-full" onClick={onSendGift}>
                Envoyer un cadeau
            </Button>

            {isLoading ? (
                <p className="text-white/40 text-sm">Chargement...</p>
            ) : (data ?? []).length === 0 ? (
                <p className="text-white/30 text-sm text-center py-8">Aucun message pour l'instant.</p>
            ) : (
                <div className="space-y-2">
                    {(data ?? []).map((m) => <MessageRow key={m.id} message={m} />)}
                </div>
            )}
        </div>
    );
}

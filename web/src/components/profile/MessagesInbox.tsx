import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { messagesApi } from "@/api/messages";
import type { AppMessage } from "@/types/message";
import Button from "@/components/ui/Button";
import CardImage from "@/components/card/CardImage";
import ResourceIcon from "@/components/ui/ResourceIcon";
import { errMsg } from "@/utils/errors";

function fmt(iso: string): string {
    return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function MessageRow({ message }: { message: AppMessage }) {
    const qc = useQueryClient();
    const [open, setOpen] = useState(false);
    const [err, setErr] = useState("");

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
                    <p className="text-white text-sm font-semibold truncate">{message.subject}</p>
                    <p className="text-white/40 text-xs">
                        {message.sender_display_name} · {fmt(message.created_at)}
                    </p>
                </div>
                {unclaimedReward && <span className="text-gold text-xs font-bold shrink-0">Cadeau</span>}
                <span className="text-white/30 text-xs shrink-0">{open ? "▲" : "▼"}</span>
            </button>

            {open && (
                <div className="px-4 pb-4 space-y-3">
                    {message.body && <p className="text-white/70 text-sm whitespace-pre-wrap">{message.body}</p>}

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
                            </span>
                        </div>
                    )}

                    {message.claim_error && (
                        <p className="text-red-400 text-xs">{message.claim_error}</p>
                    )}
                    {err && <p className="text-red-400 text-xs">{err}</p>}

                    <div className="flex items-center gap-2">
                        {unclaimedReward && (
                            <Button variant="gold" size="sm" className="flex-1" loading={claim.isPending} onClick={() => claim.mutate()}>
                                Récupérer
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

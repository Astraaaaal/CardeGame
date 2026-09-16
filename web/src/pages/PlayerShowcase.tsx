import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { showcaseApi } from "@/api/showcase";
import { friendsApi } from "@/api/friends";
import { useAuthStore } from "@/stores/authStore";
import CardImage from "@/components/card/CardImage";
import CardDetail from "@/components/card/CardDetail";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Button from "@/components/ui/Button";
import BottomNav from "@/components/layout/BottomNav";
import { errMsg } from "@/utils/errors";
import type { Card } from "@/types/card";
import { showRewards } from "@/stores/rewardPopupStore";

export default function PlayerShowcase() {
    const navigate = useNavigate();
    const { userId } = useParams<{ userId: string }>();
    const { user } = useAuthStore();
    const qc = useQueryClient();
    const id = Number(userId);
    const isSelf = user?.id === id;
    const [msg, setMsg] = useState<{ slot: number; text: string; ok: boolean } | null>(null);
    const [detailCard, setDetailCard] = useState<Card | null>(null);
    const [friendMsg, setFriendMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const { data, isLoading } = useQuery({
        queryKey: ["showcase", id],
        queryFn: () => showcaseApi.get(id),
        enabled: Number.isFinite(id),
    });

    const buy = useMutation({
        mutationFn: (slot: number) => showcaseApi.buyTradeListing(id, slot),
        onSuccess: (updated, slot) => {
            const bought = data?.trade_listings.find((l) => l.slot === slot);
            if (bought) showRewards({ title: "Achat réussi", items: [{ kind: "card", card: bought.card }] });
            qc.setQueryData(["showcase", id], updated);
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["collection"] });
            setMsg({ slot, text: "Achat réussi !", ok: true });
        },
        onError: (e, slot) => setMsg({ slot, text: errMsg(e), ok: false }),
    });

    const propose = useMutation({
        mutationFn: (slot: number) => showcaseApi.proposeTradeListing(id, slot),
        onSuccess: (_res, slot) => setMsg({ slot, text: "Demande d'échange envoyée.", ok: true }),
        onError: (e, slot) => setMsg({ slot, text: errMsg(e), ok: false }),
    });

    const addFriend = useMutation({
        mutationFn: (username: string) => friendsApi.send(username),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["showcase", id] });
            setFriendMsg({ text: "Demande d'ami envoyée.", ok: true });
        },
        onError: (e) => setFriendMsg({ text: errMsg(e), ok: false }),
    });

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate(-1)}>
                    Retour
                </button>
                <h1 className="text-white font-bold">Profil du joueur</h1>
                <span className="w-14" />
            </header>

            <main className="flex-1 px-4 py-6 max-w-sm mx-auto w-full">
                {isLoading || !data ? (
                    <LoadingSpinner text="Chargement..." />
                ) : (
                    <div className="space-y-6">
                        {isSelf && (
                            <p className="text-center text-gold text-xs bg-gold/10 border border-gold/30 rounded-lg px-3 py-2">
                                Aperçu — c'est ce que les autres joueurs voient de ton profil.
                            </p>
                        )}

                        <div className="flex flex-col items-center gap-2">
                            <div className="w-24 h-24 rounded-full overflow-hidden border-2 border-accent bg-black/30 flex items-center justify-center">
                                {data.avatar ? (
                                    <img
                                        src={`/characters/${data.avatar.image_url}`}
                                        alt=""
                                        className="w-full h-full object-cover"
                                    />
                                ) : (
                                    <span className="text-4xl text-white/20">?</span>
                                )}
                            </div>
                            <h2 className="text-white font-bold text-lg">{data.display_name}</h2>
                            <p className="text-white/40 text-xs">@{data.username}</p>
                            <div className="grid grid-cols-3 gap-2 w-full mt-2">
                                {[
                                    { label: "Niveau", value: String(data.level) },
                                    { label: "Meilleure série", value: `${data.best_login_streak} j` },
                                    { label: "Meilleur rang", value: data.best_global_rank ? `#${data.best_global_rank}` : "—" },
                                ].map((stat) => (
                                    <div key={stat.label} className="bg-game-surface border border-white/10 rounded-xl px-2 py-2 text-center">
                                        <p className="text-accent font-extrabold text-lg leading-tight">{stat.value}</p>
                                        <p className="text-white/40 text-[10px] uppercase tracking-wide">{stat.label}</p>
                                    </div>
                                ))}
                            </div>
                            {!isSelf && data.friendship_status === "none" && (
                                <>
                                    <Button
                                        variant="secondary"
                                        size="sm"
                                        loading={addFriend.isPending}
                                        onClick={() => addFriend.mutate(data.username)}
                                    >
                                        + Ajouter en ami
                                    </Button>
                                    {friendMsg && (
                                        <p className={`text-xs ${friendMsg.ok ? "text-green-400" : "text-red-400"}`}>
                                            {friendMsg.text}
                                        </p>
                                    )}
                                </>
                            )}
                            {!isSelf && data.friendship_status === "pending" && (
                                <Button variant="secondary" size="sm" disabled>
                                    Réponse en attente
                                </Button>
                            )}
                        </div>

                        {data.achievements.length > 0 && (
                            <div>
                                <p className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-2">
                                    Achievements
                                </p>
                                <div className="space-y-2">
                                    {data.achievements.map((a) => (
                                        <div key={a.id} className="flex items-center gap-3 bg-gold/10 border border-gold/30 rounded-xl px-3 py-2.5">
                                            <span className="text-xl">🏆</span>
                                            <div className="min-w-0">
                                                <p className="text-white text-sm font-semibold truncate">{a.name}</p>
                                                <p className="text-white/40 text-xs">{a.description}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div>
                            <p className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-2">
                                Cartes mises en avant
                            </p>
                            {data.cards.length === 0 ? (
                                <p className="text-white/30 text-sm text-center py-6">
                                    {isSelf ? "Tu n'as choisi aucune carte à afficher." : "Aucune carte mise en avant."}
                                </p>
                            ) : (
                                <div className="grid grid-cols-3 gap-2">
                                    {data.cards.map((c) => (
                                        <CardImage key={c.id} card={c} size="sm" onClick={() => setDetailCard(c)} />
                                    ))}
                                </div>
                            )}
                        </div>

                        <div>
                            <p className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-2">
                                Cartes à échanger
                            </p>
                            {data.trade_listings.length === 0 ? (
                                <p className="text-white/30 text-sm text-center py-6">
                                    {isSelf ? "Tu n'as listé aucune carte à échanger." : "Aucune carte à échanger."}
                                </p>
                            ) : (
                                <div className="grid grid-cols-3 gap-2">
                                    {data.trade_listings.map((listing) => (
                                        <div key={listing.slot} className="space-y-1">
                                            <CardImage card={listing.card} size="sm" onClick={() => setDetailCard(listing.card)} />
                                            <p className="text-center text-xs font-semibold text-gold">
                                                {listing.price} {listing.resource_name}
                                            </p>
                                            {!isSelf && (
                                                <Button
                                                    variant={listing.mode === "buy_now" ? "gold" : "secondary"}
                                                    size="sm"
                                                    className="w-full !text-[10px] !px-1 !py-1"
                                                    loading={
                                                        (buy.isPending && buy.variables === listing.slot) ||
                                                        (propose.isPending && propose.variables === listing.slot)
                                                    }
                                                    onClick={() =>
                                                        listing.mode === "buy_now"
                                                            ? buy.mutate(listing.slot)
                                                            : propose.mutate(listing.slot)
                                                    }
                                                >
                                                    {listing.mode === "buy_now" ? "Acheter" : "Proposer un échange"}
                                                </Button>
                                            )}
                                            {msg?.slot === listing.slot && (
                                                <p className={`text-[10px] text-center ${msg.ok ? "text-green-400" : "text-red-400"}`}>
                                                    {msg.text}
                                                </p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        <p className="text-white/20 text-xs text-center">
                            D'autres infos (badges, etc.) pourront apparaître ici plus tard.
                        </p>
                    </div>
                )}
            </main>

            <CardDetail
                open={!!detailCard}
                card={detailCard}
                readOnly={!isSelf}
                onClose={() => setDetailCard(null)}
            />

            <BottomNav />
        </div>
    );
}

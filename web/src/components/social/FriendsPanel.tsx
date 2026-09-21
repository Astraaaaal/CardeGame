import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { friendsApi } from "@/api/friends";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import { TRADE_PULSE_KEY, useTradePulse } from "@/hooks/useTradePulse";
import type { Friend } from "@/types/social";
import Button from "@/components/ui/Button";
import ConfirmModal from "@/components/ui/ConfirmModal";
import Modal from "@/components/ui/Modal";
import CollapsibleSection from "@/components/ui/CollapsibleSection";
import SendGiftModal, { type SendGiftInitialState } from "@/components/profile/SendGiftModal";
import MessagesInbox from "@/components/profile/MessagesInbox";
import { errMsg } from "@/utils/errors";

type Tab = "friends" | "trades" | "messages";

interface FriendsPanelProps {
    open: boolean;
    onClose: () => void;
}

export default function FriendsPanel({ open, onClose }: FriendsPanelProps) {
    const navigate = useNavigate();
    const qc = useQueryClient();
    // Si on revient d'une sélection de carte pour un cadeau envoyé depuis la
    // messagerie (cf. MessagesInbox via onSendGift), rouvre directement cet onglet.
    const [tab, setTab] = useState<Tab>(() =>
        useCardSelectionStore.getState().result?.context?.origin === "inbox" ? "messages" : "friends"
    );
    const [username, setUsername] = useState("");
    const [err, setErr] = useState("");
    const [tradeUsername, setTradeUsername] = useState("");
    const [tradeErr, setTradeErr] = useState("");
    const [toRemove, setToRemove] = useState<{ id: number; name: string } | null>(null);

    const [giftOpen, setGiftOpen] = useState(false);
    const [giftOrigin, setGiftOrigin] = useState<"friend" | "inbox">("friend");
    const [giftPresetUsername, setGiftPresetUsername] = useState<string | undefined>(undefined);
    const [giftInitialState, setGiftInitialState] = useState<SendGiftInitialState | undefined>(undefined);
    const consumeCardSelection = useCardSelectionStore((s) => s.consumeResultIfPurpose);

    const [groupPickerFor, setGroupPickerFor] = useState<number | null>(null);
    const [creatingGroup, setCreatingGroup] = useState(false);
    const [newGroupName, setNewGroupName] = useState("");
    const [renamingGroup, setRenamingGroup] = useState<{ id: number; name: string } | null>(null);
    const [toDeleteGroup, setToDeleteGroup] = useState<{ id: number; name: string } | null>(null);

    // Retour depuis la Collection (mode sélection) après avoir choisi une
    // carte pour un cadeau (ligne d'ami OU messagerie) — rouvre le compositeur
    // avec tout ce qui était tapé, sur le bon onglet. Revérifié à chaque
    // ouverture du panneau (pas seulement au montage) : si le panneau reste
    // monté entre deux ouvertures (toggle sans démonter), un montage unique
    // ratait la sélection en attente au retour de la Collection.
    useEffect(() => {
        if (!open) return;
        const result = consumeCardSelection(["gift"]);
        if (!result) return;
        const card = result.selectedCards[0];
        const isFriendOrigin = result.context?.origin !== "inbox";
        setGiftOrigin(isFriendOrigin ? "friend" : "inbox");
        setGiftInitialState({
            username: result.context?.username ?? "",
            subject: result.context?.subject ?? "Cadeau",
            body: result.context?.body ?? "",
            pickedCard: card ? { id: card.id, preview: card.preview } : null,
        });
        setGiftPresetUsername(isFriendOrigin ? (result.context?.username || undefined) : undefined);
        setGiftOpen(true);
    }, [open, consumeCardSelection]);

    const friendsQ = useQuery({
        queryKey: ["friends"], queryFn: friendsApi.list,
        enabled: open, refetchInterval: open ? 20_000 : false,
    });
    const requestsQ = useQuery({
        queryKey: ["friend-requests"], queryFn: friendsApi.listRequests,
        enabled: open, refetchInterval: open ? 20_000 : false,
    });
    // Pas de polling propre : TradeWatcher invalide cette liste dès que l'état
    // des échanges change (cf. useTradePulse).
    const tradesQ = useQuery({
        queryKey: ["trade-requests"], queryFn: friendsApi.listTradeRequests, enabled: open,
    });
    const groupsQ = useQuery({
        queryKey: ["friend-groups"], queryFn: friendsApi.listGroups, enabled: open,
    });
    const { data: pulse } = useTradePulse();
    const unseenTradeCount = pulse?.incoming_unseen.length ?? 0;

    useEffect(() => {
        if (!open || tab !== "trades" || unseenTradeCount === 0) return;
        friendsApi.markTradeRequestsSeen().then(() => qc.invalidateQueries({ queryKey: TRADE_PULSE_KEY }));
    }, [open, tab, unseenTradeCount, qc]);

    const refreshAll = () => {
        qc.invalidateQueries({ queryKey: ["friends"] });
        qc.invalidateQueries({ queryKey: ["friend-requests"] });
    };
    const refreshTrades = () => {
        qc.invalidateQueries({ queryKey: ["trade-requests"] });
        qc.invalidateQueries({ queryKey: TRADE_PULSE_KEY });
    };

    const sendReq = useMutation({
        mutationFn: () => friendsApi.send(username.trim()),
        onSuccess: () => { setUsername(""); setErr(""); refreshAll(); },
        onError: (e) => setErr(errMsg(e)),
    });
    const acceptReq = useMutation({
        mutationFn: (id: number) => friendsApi.accept(id),
        onSuccess: refreshAll,
    });
    const declineReq = useMutation({
        mutationFn: (id: number) => friendsApi.decline(id),
        onSuccess: refreshAll,
    });
    const removeFriend = useMutation({
        mutationFn: (userId: number) => friendsApi.remove(userId),
        onSuccess: () => { setToRemove(null); refreshAll(); },
    });
    const proposeTrade = useMutation({
        mutationFn: (userId: number) => friendsApi.proposeTrade(userId),
        onSuccess: () => { setErr(""); refreshTrades(); },
        onError: (e) => setErr(errMsg(e)),
    });
    const sendTradeReq = useMutation({
        mutationFn: () => friendsApi.sendTrade(tradeUsername.trim()),
        onSuccess: () => {
            setTradeUsername(""); setTradeErr("");
            refreshTrades();
        },
        onError: (e) => setTradeErr(errMsg(e)),
    });
    const cancelTrade = useMutation({
        mutationFn: (id: number) => friendsApi.cancelTradeRequest(id),
        onSuccess: refreshTrades,
    });
    const acceptTrade = useMutation({
        mutationFn: (id: number) => friendsApi.acceptTradeRequest(id),
        onSuccess: (session) => {
            refreshTrades();
            onClose();
            navigate(`/trade/${session.id}`);
        },
        onError: (e) => setTradeErr(errMsg(e)),
    });
    const toggleCloseFriend = useMutation({
        mutationFn: ({ userId, isClose }: { userId: number; isClose: boolean }) =>
            isClose ? friendsApi.removeCloseFriend(userId) : friendsApi.addCloseFriend(userId),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["friends"] }),
    });

    const createGroup = useMutation({
        mutationFn: (name: string) => friendsApi.createGroup(name),
        onSuccess: () => {
            setNewGroupName(""); setCreatingGroup(false);
            qc.invalidateQueries({ queryKey: ["friend-groups"] });
        },
    });
    const renameGroupM = useMutation({
        mutationFn: ({ id, name }: { id: number; name: string }) => friendsApi.renameGroup(id, name),
        onSuccess: () => { setRenamingGroup(null); qc.invalidateQueries({ queryKey: ["friend-groups"] }); },
    });
    const deleteGroupM = useMutation({
        mutationFn: (id: number) => friendsApi.deleteGroup(id),
        onSuccess: () => {
            setToDeleteGroup(null);
            qc.invalidateQueries({ queryKey: ["friend-groups"] });
            qc.invalidateQueries({ queryKey: ["friends"] });
        },
    });
    const addToGroupM = useMutation({
        mutationFn: ({ userId, groupId }: { userId: number; groupId: number }) => friendsApi.addToGroup(userId, groupId),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["friends"] }),
    });
    const removeFromGroupM = useMutation({
        mutationFn: ({ userId, groupId }: { userId: number; groupId: number }) => friendsApi.removeFromGroup(userId, groupId),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["friends"] }),
    });

    const openGift = (origin: "friend" | "inbox", presetUsername?: string) => {
        setGiftOrigin(origin);
        setGiftPresetUsername(presetUsername);
        setGiftInitialState(undefined);
        setGiftOpen(true);
    };

    const friends = friendsQ.data ?? [];
    const groups = groupsQ.data ?? [];
    const incomingReq = requestsQ.data?.incoming ?? [];
    const outgoingReq = requestsQ.data?.outgoing ?? [];
    const incomingTrades = tradesQ.data?.incoming ?? [];
    const outgoingTrades = tradesQ.data?.outgoing ?? [];

    const outgoingTradeTo = (userId: number) => outgoingTrades.find((t) => t.user_id === userId);

    const onlineFriends = friends.filter((f) => f.online);
    const closeFriends = friends.filter((f) => f.close_friend);
    const friendsInGroup = (groupId: number) => friends.filter((f) => f.group_ids.includes(groupId));
    const otherFriends = friends.filter((f) => !f.close_friend && f.group_ids.length === 0);

    const tabs: { key: Tab; label: string; badge: number }[] = [
        { key: "friends", label: "Amis", badge: incomingReq.length },
        { key: "trades", label: "Échanges", badge: pulse?.incoming_ids.length ?? incomingTrades.length },
        { key: "messages", label: "Messages", badge: 0 },
    ];

    const renderFriendRow = (f: Friend) => {
        const pendingTrade = outgoingTradeTo(f.user_id);
        return (
            <div
                key={f.user_id}
                className="bg-black/20 border border-white/5 rounded-lg px-3 py-2.5 cursor-pointer hover:border-white/20 transition-colors"
                onClick={() => { onClose(); navigate(`/players/${f.user_id}`); }}
            >
                <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2 min-w-0">
                        <span
                            className={`w-2 h-2 rounded-full shrink-0 ${f.online ? "bg-green-400" : "bg-white/20"}`}
                            title={f.online ? "En ligne" : "Hors ligne"}
                        />
                        {f.guild && (
                            <span className="text-[10px] font-bold shrink-0" style={{ color: f.guild.color }}>[{f.guild.tag}]</span>
                        )}
                        <span className="text-white text-sm font-semibold truncate">{f.display_name}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                        <button
                            className="text-sm text-white/20 hover:text-white/50"
                            title="Classer dans un groupe"
                            onClick={(e) => { e.stopPropagation(); setGroupPickerFor(groupPickerFor === f.user_id ? null : f.user_id); }}
                        >
                            🏷️
                        </button>
                        <button
                            className={`text-sm ${f.close_friend ? "text-gold" : "text-white/20 hover:text-white/50"}`}
                            title={f.close_friend ? "Ami proche — clique pour retirer" : "Marquer comme ami proche"}
                            disabled={toggleCloseFriend.isPending}
                            onClick={(e) => { e.stopPropagation(); toggleCloseFriend.mutate({ userId: f.user_id, isClose: f.close_friend }); }}
                        >
                            {f.close_friend ? "★" : "☆"}
                        </button>
                        <button
                            className="text-red-400/70 hover:text-red-400 text-xs"
                            onClick={(e) => { e.stopPropagation(); setToRemove({ id: f.user_id, name: f.display_name }); }}
                        >
                            Retirer
                        </button>
                    </div>
                </div>
                <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                    <Button
                        variant="secondary" size="sm" className="flex-1"
                        disabled={!!pendingTrade}
                        loading={proposeTrade.isPending && proposeTrade.variables === f.user_id}
                        onClick={() => proposeTrade.mutate(f.user_id)}
                    >
                        {pendingTrade ? "Échange en attente..." : "Proposer un échange"}
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => openGift("friend", f.username)}>
                        🎁
                    </Button>
                </div>
                {groupPickerFor === f.user_id && (
                    <div className="mt-2 pt-2 border-t border-white/5 space-y-1" onClick={(e) => e.stopPropagation()}>
                        {groups.length === 0 ? (
                            <p className="text-white/30 text-xs">Aucun groupe — crée-en un plus bas.</p>
                        ) : groups.map((g) => (
                            <label key={g.id} className="flex items-center gap-2 text-xs text-white/70 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={f.group_ids.includes(g.id)}
                                    onChange={() =>
                                        f.group_ids.includes(g.id)
                                            ? removeFromGroupM.mutate({ userId: f.user_id, groupId: g.id })
                                            : addToGroupM.mutate({ userId: f.user_id, groupId: g.id })
                                    }
                                />
                                {g.name}
                            </label>
                        ))}
                    </div>
                )}
            </div>
        );
    };

    return (
        <>
            <AnimatePresence>
                {open && (
                    <>
                        <motion.div
                            className="fixed inset-0 bg-black/60 z-40"
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            onClick={onClose}
                        />
                        <motion.aside
                            className="fixed top-0 right-0 h-full w-full max-w-sm bg-game-surface
                                       border-l border-white/10 z-50 flex flex-col shadow-2xl"
                            initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
                            transition={{ type: "tween", duration: 0.25 }}
                        >
                            <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
                                <h2 className="text-white font-bold">Social</h2>
                                <button className="text-white/40 hover:text-white text-xl leading-none" onClick={onClose}>
                                    ×
                                </button>
                            </div>

                            <div className="flex border-b border-white/5">
                                {tabs.map((t) => (
                                    <button
                                        key={t.key}
                                        className={`flex-1 py-2.5 text-sm font-semibold relative transition-colors ${
                                            tab === t.key ? "text-accent border-b-2 border-accent" : "text-white/40 hover:text-white/70"
                                        }`}
                                        onClick={() => setTab(t.key)}
                                    >
                                        {t.label}
                                        {t.badge > 0 && (
                                            <span className="ml-1.5 inline-flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4">
                                                {t.badge}
                                            </span>
                                        )}
                                    </button>
                                ))}
                            </div>

                            <div className="flex-1 overflow-y-auto p-4 space-y-3">
                                {tab === "friends" && (
                                    <>
                                        <div className="flex gap-2">
                                            <input
                                                className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30"
                                                placeholder="Pseudo à ajouter..."
                                                value={username}
                                                onChange={(e) => { setUsername(e.target.value); setErr(""); }}
                                                onKeyDown={(e) => e.key === "Enter" && username.trim() && sendReq.mutate()}
                                            />
                                            <Button
                                                variant="primary" size="sm"
                                                disabled={!username.trim()}
                                                loading={sendReq.isPending} success={sendReq.isSuccess}
                                                onClick={() => sendReq.mutate()}
                                            >
                                                Ajouter
                                            </Button>
                                        </div>
                                        {err && <p className="text-red-400 text-xs">{err}</p>}

                                        {friendsQ.isLoading ? (
                                            <p className="text-white/40 text-sm">Chargement...</p>
                                        ) : (
                                            <div className="space-y-2">
                                                <CollapsibleSection title="Demandes" badge={incomingReq.length} defaultOpen={incomingReq.length > 0}>
                                                    <div>
                                                        <p className="text-white/40 text-xs font-semibold mb-2 uppercase tracking-wide">
                                                            Reçues
                                                        </p>
                                                        {incomingReq.length === 0 ? (
                                                            <p className="text-white/30 text-sm">Aucune demande reçue.</p>
                                                        ) : (
                                                            <div className="space-y-2">
                                                                {incomingReq.map((r) => (
                                                                    <div key={r.id} className="bg-black/20 border border-white/5 rounded-lg px-3 py-2.5">
                                                                        <p className="text-white text-sm font-semibold mb-2">{r.display_name}</p>
                                                                        <div className="flex gap-2">
                                                                            <Button variant="primary" size="sm" className="flex-1"
                                                                                loading={acceptReq.isPending && acceptReq.variables === r.id}
                                                                                onClick={() => acceptReq.mutate(r.id)}>
                                                                                Accepter
                                                                            </Button>
                                                                            <Button variant="secondary" size="sm" className="flex-1"
                                                                                loading={declineReq.isPending && declineReq.variables === r.id}
                                                                                onClick={() => declineReq.mutate(r.id)}>
                                                                                Refuser
                                                                            </Button>
                                                                        </div>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                    <div>
                                                        <p className="text-white/40 text-xs font-semibold mb-2 mt-4 uppercase tracking-wide">
                                                            Envoyées
                                                        </p>
                                                        {outgoingReq.length === 0 ? (
                                                            <p className="text-white/30 text-sm">Aucune demande envoyée.</p>
                                                        ) : (
                                                            <div className="space-y-2">
                                                                {outgoingReq.map((r) => (
                                                                    <div key={r.id} className="flex items-center justify-between bg-black/20 border border-white/5 rounded-lg px-3 py-2.5">
                                                                        <span className="text-white text-sm">{r.display_name}</span>
                                                                        <button
                                                                            className="text-white/40 hover:text-red-400 text-xs"
                                                                            onClick={() => declineReq.mutate(r.id)}
                                                                        >
                                                                            Annuler
                                                                        </button>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                </CollapsibleSection>

                                                <CollapsibleSection title="Amis en ligne" badge={onlineFriends.length} defaultOpen>
                                                    {onlineFriends.length === 0 ? (
                                                        <p className="text-white/30 text-sm">Aucun ami en ligne pour l'instant.</p>
                                                    ) : onlineFriends.map(renderFriendRow)}
                                                </CollapsibleSection>

                                                <CollapsibleSection title="Amis proches" badge={closeFriends.length}>
                                                    {closeFriends.length === 0 ? (
                                                        <p className="text-white/30 text-sm">Aucun ami proche pour l'instant.</p>
                                                    ) : closeFriends.map(renderFriendRow)}
                                                </CollapsibleSection>

                                                {groups.map((g) => {
                                                    const members = friendsInGroup(g.id);
                                                    return (
                                                        <CollapsibleSection
                                                            key={g.id}
                                                            title={g.name}
                                                            badge={members.length}
                                                            actions={
                                                                <>
                                                                    <button
                                                                        className="text-white/30 hover:text-white text-xs"
                                                                        title="Renommer"
                                                                        onClick={() => setRenamingGroup({ id: g.id, name: g.name })}
                                                                    >
                                                                        ✎
                                                                    </button>
                                                                    <button
                                                                        className="text-white/30 hover:text-red-400 text-xs"
                                                                        title="Supprimer le groupe"
                                                                        onClick={() => setToDeleteGroup({ id: g.id, name: g.name })}
                                                                    >
                                                                        🗑
                                                                    </button>
                                                                </>
                                                            }
                                                        >
                                                            {members.length === 0 ? (
                                                                <p className="text-white/30 text-sm">Aucun ami dans ce groupe.</p>
                                                            ) : members.map(renderFriendRow)}
                                                        </CollapsibleSection>
                                                    );
                                                })}

                                                {creatingGroup ? (
                                                    <div className="flex gap-2">
                                                        <input
                                                            className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30"
                                                            placeholder="Nom du groupe..."
                                                            maxLength={30}
                                                            value={newGroupName}
                                                            onChange={(e) => setNewGroupName(e.target.value)}
                                                            onKeyDown={(e) => e.key === "Enter" && newGroupName.trim() && createGroup.mutate(newGroupName.trim())}
                                                            autoFocus
                                                        />
                                                        <Button
                                                            variant="primary" size="sm"
                                                            disabled={!newGroupName.trim()}
                                                            loading={createGroup.isPending} success={createGroup.isSuccess}
                                                            onClick={() => createGroup.mutate(newGroupName.trim())}
                                                        >
                                                            Créer
                                                        </Button>
                                                    </div>
                                                ) : (
                                                    <button
                                                        className="text-accent text-xs font-semibold px-1"
                                                        onClick={() => setCreatingGroup(true)}
                                                    >
                                                        + Nouveau groupe
                                                    </button>
                                                )}

                                                <CollapsibleSection title="Autres amis" badge={otherFriends.length} defaultOpen={groups.length === 0}>
                                                    {friends.length === 0 ? (
                                                        <p className="text-white/30 text-sm text-center py-6">
                                                            Aucun ami pour l'instant.
                                                        </p>
                                                    ) : otherFriends.length === 0 ? (
                                                        <p className="text-white/30 text-sm">Tous tes amis sont déjà classés.</p>
                                                    ) : otherFriends.map(renderFriendRow)}
                                                </CollapsibleSection>
                                            </div>
                                        )}
                                    </>
                                )}

                                {tab === "trades" && (
                                    <>
                                        <p className="text-white/30 text-xs bg-white/5 rounded-lg px-3 py-2">
                                            Propose un échange, puis composez votre offre ensemble une fois
                                            acceptée. Pas besoin d'être ami : ça dépend des paramètres de
                                            l'autre joueur (utile pour un échange ponctuel).
                                        </p>
                                        <div className="flex gap-2">
                                            <input
                                                className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30"
                                                placeholder="Pseudo du joueur..."
                                                value={tradeUsername}
                                                onChange={(e) => { setTradeUsername(e.target.value); setTradeErr(""); }}
                                                onKeyDown={(e) => e.key === "Enter" && tradeUsername.trim() && sendTradeReq.mutate()}
                                            />
                                            <Button
                                                variant="primary" size="sm"
                                                disabled={!tradeUsername.trim()}
                                                loading={sendTradeReq.isPending} success={sendTradeReq.isSuccess}
                                                onClick={() => sendTradeReq.mutate()}
                                            >
                                                Envoyer
                                            </Button>
                                        </div>
                                        {tradeErr && <p className="text-red-400 text-xs">{tradeErr}</p>}
                                        <div>
                                            <p className="text-white/40 text-xs font-semibold mb-2 mt-2 uppercase tracking-wide">
                                                Reçues
                                            </p>
                                            {incomingTrades.length === 0 ? (
                                                <p className="text-white/30 text-sm">Aucune proposition reçue.</p>
                                            ) : (
                                                <div className="space-y-2">
                                                    {incomingTrades.map((t) => (
                                                        <div key={t.id} className="bg-black/20 border border-white/5 rounded-lg px-3 py-2.5">
                                                            <p className="text-white text-sm mb-2">{t.display_name} propose un échange</p>
                                                            <div className="flex gap-2">
                                                                <Button variant="primary" size="sm" className="flex-1"
                                                                    loading={acceptTrade.isPending && acceptTrade.variables === t.id}
                                                                    onClick={() => acceptTrade.mutate(t.id)}>
                                                                    Accepter
                                                                </Button>
                                                                <Button variant="secondary" size="sm" className="flex-1"
                                                                    loading={cancelTrade.isPending && cancelTrade.variables === t.id}
                                                                    onClick={() => cancelTrade.mutate(t.id)}>
                                                                    Refuser
                                                                </Button>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <div>
                                            <p className="text-white/40 text-xs font-semibold mb-2 mt-4 uppercase tracking-wide">
                                                Envoyées
                                            </p>
                                            {outgoingTrades.length === 0 ? (
                                                <p className="text-white/30 text-sm">Aucune proposition envoyée.</p>
                                            ) : (
                                                <div className="space-y-2">
                                                    {outgoingTrades.map((t) => (
                                                        <div key={t.id} className="flex items-center justify-between bg-black/20 border border-white/5 rounded-lg px-3 py-2.5">
                                                            <span className="text-white text-sm">En attente de {t.display_name}</span>
                                                            <button
                                                                className="text-white/40 hover:text-red-400 text-xs shrink-0"
                                                                onClick={() => cancelTrade.mutate(t.id)}
                                                            >
                                                                Annuler
                                                            </button>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </>
                                )}

                                {tab === "messages" && (
                                    <MessagesInbox onSendGift={() => openGift("inbox")} />
                                )}
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>

            <ConfirmModal
                open={!!toRemove}
                title="Retirer cet ami"
                message={toRemove ? `Retirer ${toRemove.name} de tes amis ?` : ""}
                confirmLabel="Retirer"
                busy={removeFriend.isPending}
                onConfirm={() => toRemove && removeFriend.mutate(toRemove.id)}
                onCancel={() => setToRemove(null)}
            />

            <ConfirmModal
                open={!!toDeleteGroup}
                title="Supprimer ce groupe"
                message={toDeleteGroup ? `Supprimer le groupe « ${toDeleteGroup.name} » ? Les amis n'en seront pas retirés d'ailleurs — juste de ce groupe.` : ""}
                confirmLabel="Supprimer"
                busy={deleteGroupM.isPending}
                onConfirm={() => toDeleteGroup && deleteGroupM.mutate(toDeleteGroup.id)}
                onCancel={() => setToDeleteGroup(null)}
            />

            {renamingGroup && (
                <Modal open onClose={() => setRenamingGroup(null)} title="Renommer le groupe">
                    <div className="space-y-3">
                        <input
                            className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                            maxLength={30}
                            value={renamingGroup.name}
                            onChange={(e) => setRenamingGroup({ ...renamingGroup, name: e.target.value })}
                            onKeyDown={(e) => e.key === "Enter" && renamingGroup.name.trim() && renameGroupM.mutate(renamingGroup)}
                            autoFocus
                        />
                        <div className="flex gap-2">
                            <Button
                                variant="primary" className="flex-1"
                                disabled={!renamingGroup.name.trim()}
                                loading={renameGroupM.isPending} success={renameGroupM.isSuccess}
                                onClick={() => renameGroupM.mutate(renamingGroup)}
                            >
                                Enregistrer
                            </Button>
                            <Button variant="secondary" onClick={() => setRenamingGroup(null)}>Annuler</Button>
                        </div>
                    </div>
                </Modal>
            )}

            {giftOpen && (
                <SendGiftModal
                    presetUsername={giftPresetUsername}
                    returnTo="/"
                    origin={giftOrigin}
                    initialState={giftInitialState}
                    onClose={() => setGiftOpen(false)}
                />
            )}
        </>
    );
}

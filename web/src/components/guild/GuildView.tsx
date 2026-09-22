import { formatNumber as fmt, parseUtc as utc } from "@/utils/format";
import { inputCls } from "@/components/ui/formStyles";
import { useEffect, useRef, useState } from "react";
import { toast } from "@/stores/toastStore";
import { useToastMessage } from "@/hooks/useToastMessage";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { guildsApi, type GuildDetail, type GuildRole, type JoinPolicy } from "@/api/guilds";
import { useAuthStore } from "@/stores/authStore";
import Button from "@/components/ui/Button";
import { errMsg } from "@/utils/errors";
import ResourceIcon from "@/components/ui/ResourceIcon";
import EmojiText from "@/components/ui/EmojiText";
import EmojiPicker from "@/components/ui/EmojiPicker";
import GuildEmblem, { GUILD_COLORS, GUILD_ICONS, POLICY_LABEL, ROLE_LABEL } from "./GuildEmblem";
import { MY_GUILD_KEY } from "./NoGuild";

type Tab = "challenge" | "chest" | "members" | "wall";
const TABS: { key: Tab; label: string }[] = [
    { key: "challenge", label: "Défi" },
    { key: "chest", label: "Coffre" },
    { key: "members", label: "Membres" },
    { key: "wall", label: "Tchat" },
];

function remaining(expires: string) {
    const ms = utc(expires).getTime() - Date.now();
    const h = Math.max(0, Math.floor(ms / 3600_000));
    return h >= 24 ? `${Math.floor(h / 24)} j ${h % 24} h` : `${h} h ${Math.max(0, Math.floor((ms % 3600_000) / 60_000))} min`;
}

/** Hook commun : met à jour le cache de la guilde avec la réponse du serveur. */
function useGuildActions() {
    const qc = useQueryClient();
    const [msg, setMsg] = useToastMessage();
    const setDetail = (guild: GuildDetail) =>
        qc.setQueryData(MY_GUILD_KEY, (old: object | undefined) => (old ? { ...old, guild } : old));
    const refresh = () => {
        qc.invalidateQueries({ queryKey: MY_GUILD_KEY });
        qc.invalidateQueries({ queryKey: ["player"] });
    };
    const onError = (e: unknown) => setMsg({ text: errMsg(e), ok: false });
    return { msg, setMsg, setDetail, refresh, onError };
}

export default function GuildView({ guild }: { guild: GuildDetail }) {
    const [tab, setTab] = useState<Tab>("challenge");
    const span = guild.xp_next_level - guild.xp_current_level;
    const pct = span > 0 ? Math.min(100, ((guild.xp - guild.xp_current_level) / span) * 100) : 100;

    return (
        <div className="space-y-4">
            <section className="bg-game-surface rounded-2xl border border-white/10 p-4 space-y-3">
                <div className="flex items-center gap-3">
                    <GuildEmblem icon={guild.icon} color={guild.color} size={52} />
                    <div className="flex-1 min-w-0">
                        <p className="text-white font-bold truncate">
                            <span style={{ color: guild.color }}>[{guild.tag}]</span> {guild.name}
                        </p>
                        <p className="text-white/40 text-xs">
                            {guild.members}/{guild.max_members} membres · puissance {fmt(guild.power)} · {ROLE_LABEL[guild.my_role]}
                        </p>
                    </div>
                </div>
                <div>
                    <div className="flex justify-between text-[11px] text-white/50 mb-1">
                        <span>Niveau {guild.level}</span>
                        <span>{fmt(guild.xp - guild.xp_current_level)} / {fmt(span)} XP</span>
                    </div>
                    <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                        <div className="h-full bg-accent transition-all" style={{ width: `${pct}%` }} />
                    </div>
                </div>
                {guild.welcome_message && <p className="text-white/70 text-xs italic whitespace-pre-line">« {guild.welcome_message} »</p>}
                {guild.buffs.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                        {guild.buffs.map((b) => (
                            <span key={b.kind} className="text-[11px] bg-green-500/15 text-green-300 border border-green-500/30 rounded-full px-2 py-0.5">
                                {b.label} · {remaining(b.expires_at)}
                            </span>
                        ))}
                    </div>
                )}
            </section>

            <div className="flex border-b border-white/5">
                {TABS.map((t) => (
                    <button key={t.key}
                        className={`flex-1 py-2 text-sm font-semibold ${tab === t.key ? "text-accent border-b-2 border-accent" : "text-white/40"}`}
                        onClick={() => setTab(t.key)}>
                        {t.label}
                        {t.key === "members" && guild.requests.length > 0 && (
                            <span className="ml-1 text-[10px] bg-red-500 text-white rounded-full px-1.5">{guild.requests.length}</span>
                        )}
                    </button>
                ))}
            </div>

            {tab === "challenge" && <ChallengeTab guild={guild} />}
            {tab === "chest" && <ChestTab guild={guild} />}
            {tab === "members" && <MembersTab guild={guild} />}
            {tab === "wall" && <WallTab />}
        </div>
    );
}

function ChallengeTab({ guild }: { guild: GuildDetail }) {
    const { setMsg, refresh, onError } = useGuildActions();
    const claim = useMutation({
        mutationFn: (metric: string) => guildsApi.claimObjective(metric),
        onSuccess: (r) => { setMsg({ text: `+${fmt(r.coins)} pièces et +${fmt(r.dust)} poussière !`, ok: true }); refresh(); },
        onError,
    });
    const done = guild.objectives.filter((o) => o.completed_at).length;

    return (
        <div className="space-y-3">
            <p className="text-white/50 text-xs">
                Palier {guild.challenge_tier} · {done}/{guild.objectives.length} objectifs · record {guild.challenge_best_tier}.
                Tout réussir = palier suivant la semaine prochaine, sinon il est divisé par deux.
            </p>
            {guild.objectives.map((o) => {
                const p = Math.min(100, (o.progress / o.target) * 100);
                return (
                    <div key={o.metric} className="bg-game-surface border border-white/10 rounded-xl p-3 space-y-2">
                        <div className="flex justify-between gap-2">
                            <span className="text-white text-sm font-semibold">{o.label}</span>
                            <span className={`text-xs ${o.completed_at ? "text-green-400" : "text-white/50"}`}>
                                {fmt(Math.min(o.progress, o.target))} / {fmt(o.target)}
                            </span>
                        </div>
                        <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                            <div className={`h-full ${o.completed_at ? "bg-green-500" : "bg-accent"}`} style={{ width: `${p}%` }} />
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-white/40">
                            <span>Ta contribution : {fmt(o.my_contribution)} · <ResourceIcon resourceId="coins" /> {fmt(o.reward_coins)} · ✨ {fmt(o.reward_dust)}</span>
                            {o.claimed ? (
                                <span className="text-green-400">Récupéré ✓</span>
                            ) : o.claimable ? (
                                <Button variant="gold" size="sm" loading={claim.isPending && claim.variables === o.metric}
                                    onClick={() => claim.mutate(o.metric)}>Récupérer</Button>
                            ) : null}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

function ChestTab({ guild }: { guild: GuildDetail }) {
    const { setMsg, setDetail, refresh, onError } = useGuildActions();
    const [resource, setResource] = useState<"coins" | "dust">("coins");
    const [amount, setAmount] = useState("");
    const rate = resource === "coins" ? guild.points_per_coins : guild.points_per_dust;
    const value = Math.max(0, Math.floor(Number(amount) || 0));
    const canManage = guild.my_role !== "member";

    const donate = useMutation({
        mutationFn: () => guildsApi.donate(resource, value),
        onSuccess: (r) => { setMsg({ text: `Merci ! +${fmt(r.points)} points pour la guilde.`, ok: true }); setAmount(""); refresh(); },
        onError,
    });
    const buy = useMutation({
        mutationFn: (kind: string) => guildsApi.buyBuff(kind),
        onSuccess: (g) => { setDetail(g); setMsg({ text: "Bonus activé pour toute la guilde !", ok: true }); },
        onError,
    });

    return (
        <div className="space-y-4">
            <section className="bg-game-surface border border-white/10 rounded-xl p-3 space-y-2">
                <div className="flex justify-between">
                    <span className="text-white text-sm font-semibold">Coffre</span>
                    <span className="text-gold text-sm font-bold">{fmt(guild.chest_points)} points</span>
                </div>
                <p className="text-white/40 text-[11px]">
                    1 point = {guild.points_per_coins} pièces ou {guild.points_per_dust} poussière. Chaque point donne aussi 1 XP à la guilde.
                </p>
                <div className="flex gap-1.5">
                    {(["coins", "dust"] as const).map((r) => (
                        <button key={r}
                            className={`flex-1 py-1.5 rounded-lg text-xs font-bold ${resource === r ? "bg-accent text-white" : "bg-white/10 text-white/60"}`}
                            onClick={() => setResource(r)}>{r === "coins" ? <><ResourceIcon resourceId="coins" /> Pièces</> : "✨ Poussière"}</button>
                    ))}
                </div>
                <div className="flex gap-2">
                    <input className={inputCls} type="number" min={rate} step={rate} placeholder={`Montant (multiple de ${rate})`}
                        value={amount} onChange={(e) => setAmount(e.target.value)} />
                    <Button variant="gold" size="sm" loading={donate.isPending} success={donate.isSuccess} disabled={value < rate}
                        onClick={() => { setMsg(null); donate.mutate(); }}>Donner</Button>
                </div>
                {value >= rate && <p className="text-white/40 text-[11px]">→ {fmt(Math.floor(value / rate))} points</p>}
            </section>

            <section className="bg-game-surface border border-white/10 rounded-xl p-3 space-y-1">
                <span className="text-white text-sm font-semibold">Avantages du niveau {guild.level}</span>
                <p className="text-white/60 text-xs">• Récompense quotidienne : +{guild.perks.daily_bonus_pct} %</p>
                <p className="text-white/60 text-xs">
                    • Emplacement d'expédition supplémentaire :{" "}
                    {guild.perks.extra_expedition_slots > 0 ? "oui" : `au niveau ${guild.perks.expedition_slot_level}`}
                </p>
                <p className="text-white/60 text-xs">• Membres maximum : {guild.max_members}</p>
            </section>

            <section className="space-y-2">
                <h3 className="text-white/50 text-xs font-semibold uppercase tracking-wide">Bonus de guilde</h3>
                {!canManage && <p className="text-white/30 text-[11px]">Seuls le chef et les officiers peuvent dépenser les points.</p>}
                {guild.shop.map((s) => {
                    const active = guild.buffs.find((b) => b.kind === s.kind);
                    const duration = s.hours >= 24 ? `${s.hours / 24} j` : `${s.hours} h`;
                    return (
                        <div key={s.kind} className="flex items-center gap-2 bg-game-surface border border-white/10 rounded-xl p-3">
                            <div className="flex-1 min-w-0">
                                <p className="text-white text-sm">{s.label}</p>
                                <p className="text-white/40 text-[11px]">
                                    {duration} · {fmt(s.cost)} points{active ? ` · actif encore ${remaining(active.expires_at)}` : ""}
                                </p>
                            </div>
                            {canManage && (
                                <Button variant="secondary" size="sm" disabled={guild.chest_points < s.cost}
                                    loading={buy.isPending && buy.variables === s.kind}
                                    onClick={() => { setMsg(null); buy.mutate(s.kind); }}>
                                    {active ? "Prolonger" : "Acheter"}
                                </Button>
                            )}
                        </div>
                    );
                })}
            </section>
        </div>
    );
}

function MembersTab({ guild }: { guild: GuildDetail }) {
    const me = useAuthStore((s) => s.user);
    const navigate = useNavigate();
    const { setMsg, setDetail, refresh, onError } = useGuildActions();
    const [username, setUsername] = useState("");
    const [welcome, setWelcome] = useState(guild.welcome_message);
    const isLeader = guild.my_role === "leader";
    const canManage = guild.my_role !== "member";

    const answer = useMutation({
        mutationFn: ({ id, accept }: { id: number; accept: boolean }) => guildsApi.answerRequest(id, accept),
        onSuccess: setDetail, onError,
    });
    const setRole = useMutation({
        mutationFn: ({ id, role }: { id: number; role: GuildRole }) => guildsApi.setRole(id, role),
        onSuccess: setDetail, onError,
    });
    const kick = useMutation({ mutationFn: (id: number) => guildsApi.kick(id), onSuccess: setDetail, onError });
    const invite = useMutation({
        mutationFn: () => guildsApi.invite(username.trim()),
        onSuccess: () => { setMsg({ text: `Invitation envoyée à ${username.trim()}.`, ok: true }); setUsername(""); },
        onError,
    });
    const settings = useMutation({
        mutationFn: (b: Partial<{ welcome_message: string; join_policy: JoinPolicy; icon: string; color: string }>) => guildsApi.settings(b),
        onSuccess: (g) => { setDetail(g); setMsg({ text: "Réglages enregistrés.", ok: true }); },
        onError,
    });
    const leave = useMutation({ mutationFn: () => guildsApi.leave(), onSuccess: refresh, onError });

    const order: Record<GuildRole, number> = { leader: 0, officer: 1, member: 2 };
    const [sortBy, setSortBy] = useState<"role" | "power" | "donated">("role");
    const members = [...guild.members_list].sort((a, b) =>
        sortBy === "power" ? b.power - a.power
            : sortBy === "donated" ? b.donated_points - a.donated_points
            : order[a.role] - order[b.role] || b.donated_points - a.donated_points);

    const confirmLeave = () => {
        const last = guild.members === 1;
        const text = last
            ? "Tu es le dernier membre : la guilde sera dissoute. Continuer ?"
            : isLeader ? "Le chef passera à l'officier (ou au membre) le plus ancien. Quitter la guilde ?" : "Quitter la guilde ?";
        if (window.confirm(text)) leave.mutate();
    };

    return (
        <div className="space-y-4">

            {canManage && guild.requests.length > 0 && (
                <section className="space-y-2">
                    <h3 className="text-white/50 text-xs font-semibold uppercase tracking-wide">Demandes d'adhésion</h3>
                    {guild.requests.map((r) => (
                        <div key={r.id} className="flex items-center gap-2 bg-accent/10 border border-accent/30 rounded-xl p-2.5">
                            <span className="flex-1 text-white text-sm truncate">{r.display_name} <span className="text-white/30">@{r.username}</span></span>
                            <Button variant="gold" size="sm" onClick={() => answer.mutate({ id: r.id, accept: true })}>Accepter</Button>
                            <button className="text-white/40 text-xs" onClick={() => answer.mutate({ id: r.id, accept: false })}>Refuser</button>
                        </div>
                    ))}
                </section>
            )}

            <section className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-[11px] text-white/40">
                    Trier par
                    {([["role", "Hiérarchie"], ["power", "Puissance"], ["donated", "Points donnés"]] as const).map(([key, label]) => (
                        <button key={key}
                            className={`px-2 py-0.5 rounded-full font-bold ${sortBy === key ? "bg-accent text-white" : "bg-white/10 text-white/60"}`}
                            onClick={() => setSortBy(key)}>{label}</button>
                    ))}
                </div>
                {members.map((m) => {
                    const self = m.user_id === me?.id;
                    return (
                        <div key={m.user_id} className="flex items-center gap-2 bg-game-surface border border-white/10 rounded-xl p-2.5">
                            <button className="flex-1 min-w-0 text-left" onClick={() => navigate(`/players/${m.user_id}`)}>
                                <p className="text-white text-sm truncate hover:underline">
                                    {m.display_name}{self && <span className="text-white/30"> (toi)</span>}
                                </p>
                                <p className="text-white/40 text-[11px]">
                                    {ROLE_LABEL[m.role]} · ⚡ {fmt(m.power)} · {fmt(m.donated_points)} points donnés
                                </p>
                            </button>
                            {isLeader && !self && (
                                <select className="bg-black/40 text-white text-xs rounded-lg px-1.5 py-1 border border-white/10"
                                    value={m.role}
                                    onChange={(e) => {
                                        const role = e.target.value as GuildRole;
                                        if (role === "leader" && !window.confirm(`Céder la direction à ${m.display_name} ? Tu deviendras officier.`)) return;
                                        setRole.mutate({ id: m.user_id, role });
                                    }}>
                                    <option value="member">Membre</option>
                                    <option value="officer">Officier</option>
                                    <option value="leader">Chef</option>
                                </select>
                            )}
                            {canManage && !self && order[m.role] > order[guild.my_role] && (
                                <button className="text-red-400/70 text-xs px-1"
                                    onClick={() => window.confirm(`Exclure ${m.display_name} ?`) && kick.mutate(m.user_id)}>
                                    Exclure
                                </button>
                            )}
                        </div>
                    );
                })}
            </section>

            {canManage && (
                <section className="bg-game-surface border border-white/10 rounded-xl p-3 space-y-2">
                    <span className="text-white text-sm font-semibold">Inviter un joueur</span>
                    <div className="flex gap-2">
                        <input className={inputCls} placeholder="Pseudo" value={username} onChange={(e) => setUsername(e.target.value)} />
                        <Button variant="secondary" size="sm" disabled={!username.trim()} loading={invite.isPending} success={invite.isSuccess}
                            onClick={() => { setMsg(null); invite.mutate(); }}>Inviter</Button>
                    </div>
                </section>
            )}

            {canManage && (
                <section className="bg-game-surface border border-white/10 rounded-xl p-3 space-y-2">
                    <span className="text-white text-sm font-semibold">Réglages</span>
                    <div className="flex gap-1.5">
                        {(Object.keys(POLICY_LABEL) as JoinPolicy[]).map((p) => (
                            <button key={p}
                                className={`flex-1 py-1.5 rounded-lg text-[11px] font-bold ${guild.join_policy === p ? "bg-accent text-white" : "bg-white/10 text-white/60"}`}
                                onClick={() => settings.mutate({ join_policy: p })}>{POLICY_LABEL[p]}</button>
                        ))}
                    </div>
                    <textarea className={`${inputCls} resize-none`} rows={2} maxLength={300} placeholder="Message d'accueil"
                        value={welcome} onChange={(e) => setWelcome(e.target.value)} />
                    <Button variant="secondary" size="sm" className="w-full" disabled={welcome === guild.welcome_message}
                        onClick={() => settings.mutate({ welcome_message: welcome })}>Enregistrer le message</Button>
                    {isLeader && (
                        <>
                            <div className="flex flex-wrap gap-1.5 pt-1">
                                {GUILD_ICONS.map((icon) => (
                                    <button key={icon} className={`w-8 h-8 rounded-lg ${guild.icon === icon ? "bg-accent" : "bg-white/10"}`}
                                        onClick={() => settings.mutate({ icon })}>{icon}</button>
                                ))}
                            </div>
                            <div className="flex gap-1.5">
                                {GUILD_COLORS.map((color) => (
                                    <button key={color} aria-label={color}
                                        className={`w-7 h-7 rounded-full border-2 ${guild.color === color ? "border-white" : "border-transparent"}`}
                                        style={{ background: color }} onClick={() => settings.mutate({ color })} />
                                ))}
                            </div>
                        </>
                    )}
                </section>
            )}

            <Button variant="danger" size="sm" className="w-full" loading={leave.isPending} success={leave.isSuccess} onClick={confirmLeave}>
                Quitter la guilde
            </Button>
        </div>
    );
}

function WallTab() {
    const me = useAuthStore((s) => s.user);
    const qc = useQueryClient();
    const navigate = useNavigate();
    const [text, setText] = useState("");
    const setErr = (m: string | null) => { if (m) toast.error(m); };
    const bottom = useRef<HTMLDivElement>(null);
    const input = useRef<HTMLInputElement>(null);
    const { data: messages } = useQuery({ queryKey: ["guild", "wall"], queryFn: guildsApi.wall, refetchInterval: 15_000 });
    const post = useMutation({
        mutationFn: () => guildsApi.post(text.trim()),
        onSuccess: (list) => { qc.setQueryData(["guild", "wall"], list); setText(""); },
        onError: (e) => setErr(errMsg(e)),
    });
    useEffect(() => { bottom.current?.scrollIntoView({ block: "nearest" }); }, [messages?.length]);
    const send = () => {
        setErr(null);
        if (text.trim() && !post.isPending) post.mutate();
    };

    return (
        <div className="space-y-3">
            <div className="bg-game-surface border border-white/10 rounded-xl p-3 space-y-2 max-h-[55vh] overflow-y-auto">
                {(messages ?? []).map((m) =>
                    m.system ? (
                        <p key={m.id} className="text-center text-[11px] text-white/40 italic">{m.body}</p>
                    ) : m.user_id === me?.id ? (
                        // Mes messages : à droite, sans lien vers mon propre profil.
                        <div key={m.id} className="flex flex-col items-end">
                            <p className="text-[11px] text-white/40">
                                {utc(m.created_at).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
                            </p>
                            <p className="text-white text-sm whitespace-pre-line break-words bg-accent/25 rounded-xl rounded-tr-sm px-3 py-1.5 max-w-[85%]">
                                <EmojiText text={m.body} />
                            </p>
                        </div>
                    ) : (
                        <div key={m.id} className="flex flex-col items-start">
                            <p className="text-[11px] text-white/40">
                                {m.user_id ? (
                                    <button className="text-accent font-semibold hover:underline" onClick={() => navigate(`/players/${m.user_id}`)}>
                                        {m.author}
                                    </button>
                                ) : (
                                    <span className="text-accent font-semibold">{m.author}</span>
                                )} ·{" "}
                                {utc(m.created_at).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
                            </p>
                            <p className="text-white text-sm whitespace-pre-line break-words bg-white/10 rounded-xl rounded-tl-sm px-3 py-1.5 max-w-[85%]">
                                <EmojiText text={m.body} />
                            </p>
                        </div>
                    ),
                )}
                {messages?.length === 0 && <p className="text-white/30 text-sm text-center">Aucun message pour l'instant.</p>}
                <div ref={bottom} />
            </div>
            <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); send(); }}>
                <input ref={input} className={inputCls} maxLength={200} placeholder="Écrire un message..." value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); send(); } }} />
                <EmojiPicker target={input} value={text} onChange={setText} />
                <Button variant="primary" size="sm" type="submit" loading={post.isPending} success={post.isSuccess} disabled={!text.trim()}>Envoyer</Button>
            </form>
        </div>
    );
}

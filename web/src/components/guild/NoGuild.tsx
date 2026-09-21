import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { guildsApi, type JoinPolicy, type MyGuildState } from "@/api/guilds";
import Button from "@/components/ui/Button";
import { errMsg } from "@/utils/errors";
import GuildEmblem, { GUILD_COLORS, GUILD_ICONS, POLICY_LABEL } from "./GuildEmblem";

const inputCls = "w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30";
export const MY_GUILD_KEY = ["guild", "me"];

/** Sans guilde : invitations reçues, création et recherche. */
export default function NoGuild({ state }: { state: MyGuildState }) {
    const qc = useQueryClient();
    const [query, setQuery] = useState("");
    const [form, setForm] = useState({ name: "", tag: "", icon: GUILD_ICONS[0], color: GUILD_COLORS[0], join_policy: "request" as JoinPolicy });
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
    const { data: results } = useQuery({ queryKey: ["guild", "search", query], queryFn: () => guildsApi.search(query) });

    const refresh = () => { qc.invalidateQueries({ queryKey: MY_GUILD_KEY }); qc.invalidateQueries({ queryKey: ["player"] }); };
    const onError = (e: unknown) => setMsg({ text: errMsg(e), ok: false });

    const create = useMutation({ mutationFn: () => guildsApi.create(form), onSuccess: refresh, onError });
    const join = useMutation({
        mutationFn: (id: number) => guildsApi.join(id),
        onSuccess: (res) => {
            if (res.result === "requested") setMsg({ text: "Demande envoyée : le chef ou un officier doit l'accepter.", ok: true });
            refresh();
        },
        onError,
    });
    const answer = useMutation({
        mutationFn: ({ id, accept }: { id: number; accept: boolean }) => guildsApi.answerInvite(id, accept),
        onSuccess: refresh,
        onError,
    });

    const cooldownEnd = state.left_at ? new Date(new Date(state.left_at + "Z").getTime() + state.cooldown_hours * 3600_000) : null;
    const waiting = cooldownEnd && cooldownEnd > new Date();

    return (
        <div className="space-y-5">
            {waiting && (
                <p className="text-amber-300/80 text-xs">
                    Tu as quitté une guilde récemment : tu pourras en rejoindre une à partir de{" "}
                    {cooldownEnd!.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}.
                </p>
            )}
            {msg && <p className={`text-xs ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>}

            {state.invites.length > 0 && (
                <section className="space-y-2">
                    <h2 className="text-white/50 text-xs font-semibold uppercase tracking-wide">Invitations</h2>
                    {state.invites.map((inv) => (
                        <div key={inv.id} className="flex items-center gap-3 bg-accent/10 border border-accent/30 rounded-xl p-3">
                            <GuildEmblem icon={inv.guild.icon} color={inv.guild.color} size={32} />
                            <span className="flex-1 text-white text-sm">[{inv.guild.tag}] {inv.guild.name}</span>
                            <Button variant="gold" size="sm" onClick={() => answer.mutate({ id: inv.id, accept: true })}>Rejoindre</Button>
                            <button className="text-white/40 text-xs" onClick={() => answer.mutate({ id: inv.id, accept: false })}>Refuser</button>
                        </div>
                    ))}
                </section>
            )}

            <section className="bg-game-surface rounded-2xl border border-white/10 p-4 space-y-3">
                <h2 className="text-white font-bold text-sm">Fonder une guilde ({state.creation_cost.toLocaleString("fr-FR")} pièces)</h2>
                <div className="grid grid-cols-[1fr_5rem] gap-2">
                    <input className={inputCls} placeholder="Nom (3 à 24 caractères)" maxLength={24}
                        value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                    <input className={`${inputCls} uppercase`} placeholder="TAG" maxLength={4}
                        value={form.tag} onChange={(e) => setForm({ ...form, tag: e.target.value.toUpperCase() })} />
                </div>
                <div className="flex flex-wrap gap-1.5">
                    {GUILD_ICONS.map((icon) => (
                        <button key={icon}
                            className={`w-9 h-9 rounded-lg text-lg ${form.icon === icon ? "bg-accent" : "bg-white/10"}`}
                            onClick={() => setForm({ ...form, icon })}>{icon}</button>
                    ))}
                </div>
                <div className="flex gap-1.5">
                    {GUILD_COLORS.map((color) => (
                        <button key={color} aria-label={color}
                            className={`w-7 h-7 rounded-full border-2 ${form.color === color ? "border-white" : "border-transparent"}`}
                            style={{ background: color }} onClick={() => setForm({ ...form, color })} />
                    ))}
                </div>
                <div className="flex gap-1.5">
                    {(Object.keys(POLICY_LABEL) as JoinPolicy[]).map((p) => (
                        <button key={p}
                            className={`flex-1 py-1.5 rounded-lg text-xs font-bold ${form.join_policy === p ? "bg-accent text-white" : "bg-white/10 text-white/60"}`}
                            onClick={() => setForm({ ...form, join_policy: p })}>{POLICY_LABEL[p]}</button>
                    ))}
                </div>
                <div className="flex items-center gap-2">
                    <GuildEmblem icon={form.icon} color={form.color} size={36} />
                    <span className="text-white text-sm flex-1 truncate">[{form.tag || "TAG"}] {form.name || "Ta guilde"}</span>
                </div>
                <Button variant="primary" className="w-full" loading={create.isPending} success={create.isSuccess}
                    disabled={form.name.trim().length < 3 || form.tag.length < 2}
                    onClick={() => { setMsg(null); create.mutate(); }}>
                    Fonder la guilde
                </Button>
            </section>

            <section className="space-y-2">
                <h2 className="text-white/50 text-xs font-semibold uppercase tracking-wide">Rejoindre une guilde</h2>
                <input className={inputCls} placeholder="Rechercher par nom ou tag..." value={query} onChange={(e) => setQuery(e.target.value)} />
                {(results ?? []).map((g) => (
                    <div key={g.id} className="flex items-center gap-3 bg-game-surface border border-white/10 rounded-xl p-3">
                        <GuildEmblem icon={g.icon} color={g.color} size={36} />
                        <div className="flex-1 min-w-0">
                            <p className="text-white text-sm font-semibold truncate">[{g.tag}] {g.name}</p>
                            <p className="text-white/40 text-[11px]">
                                Niv. {g.level} · {g.members}/{g.max_members} membres · {POLICY_LABEL[g.join_policy]}
                            </p>
                        </div>
                        {g.join_policy !== "invite" && g.members < g.max_members && (
                            <Button variant="secondary" size="sm" loading={join.isPending && join.variables === g.id}
                                onClick={() => { setMsg(null); join.mutate(g.id); }}>
                                {g.join_policy === "open" ? "Rejoindre" : "Demander"}
                            </Button>
                        )}
                    </div>
                ))}
                {results?.length === 0 && <p className="text-white/30 text-sm">Aucune guilde trouvée.</p>}
            </section>
        </div>
    );
}

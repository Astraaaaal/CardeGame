import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { adminMessagesApi } from "@/api/admin";
import type { AdminResource } from "@/types/content";
import Button from "@/components/ui/Button";

const inputCls =
    "w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white " +
    "placeholder-white/30 focus:border-accent focus:outline-none transition-colors";
const labelCls = "block text-white/60 text-xs mb-1";

function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof r?.data?.detail === "string") return r.data.detail;
    }
    return "Erreur.";
}

interface AdminMessagesComposerProps {
    resources: AdminResource[];
}

export default function AdminMessagesComposer({ resources }: AdminMessagesComposerProps) {
    const [audience, setAudience] = useState<"all" | "specific">("all");
    const [usernames, setUsernames] = useState("");
    const [subject, setSubject] = useState("");
    const [body, setBody] = useState("");
    const [rewardResourceId, setRewardResourceId] = useState("");
    const [rewardAmount, setRewardAmount] = useState<number | "">("");
    const [result, setResult] = useState<{ text: string; ok: boolean } | null>(null);

    const send = useMutation({
        mutationFn: () => adminMessagesApi.send({
            usernames: audience === "all" ? null : usernames.split(",").map((u) => u.trim()).filter(Boolean),
            subject: subject.trim(),
            body: body.trim(),
            reward_resource_id: rewardResourceId || null,
            reward_amount: rewardResourceId ? (rewardAmount || null) : null,
        }),
        onSuccess: (res) => {
            setResult({ text: `Message envoyé à ${res.sent_count} joueur(s).`, ok: true });
            setSubject(""); setBody(""); setRewardResourceId(""); setRewardAmount(""); setUsernames("");
        },
        onError: (e) => setResult({ text: errMsg(e), ok: false }),
    });

    const canSend = !!subject.trim() && (audience === "all" || usernames.trim().length > 0);

    return (
        <div className="bg-game-surface/40 border border-white/10 rounded-lg p-4 space-y-3">
            <div>
                <p className={labelCls}>Destinataires</p>
                <div className="flex gap-2 mb-2">
                    <button
                        className={`flex-1 py-1.5 rounded-lg text-xs font-semibold ${audience === "all" ? "bg-accent text-white" : "bg-white/10 text-white/50"}`}
                        onClick={() => setAudience("all")}
                    >
                        Tous les joueurs
                    </button>
                    <button
                        className={`flex-1 py-1.5 rounded-lg text-xs font-semibold ${audience === "specific" ? "bg-accent text-white" : "bg-white/10 text-white/50"}`}
                        onClick={() => setAudience("specific")}
                    >
                        Pseudos précis
                    </button>
                </div>
                {audience === "specific" && (
                    <input
                        className={inputCls}
                        placeholder="pseudo1, pseudo2, ..."
                        value={usernames}
                        onChange={(e) => setUsernames(e.target.value)}
                    />
                )}
            </div>

            <div>
                <p className={labelCls}>Objet</p>
                <input className={inputCls} maxLength={100} value={subject} onChange={(e) => setSubject(e.target.value)} />
            </div>

            <div>
                <p className={labelCls}>Message</p>
                <textarea
                    className={`${inputCls} resize-none`} rows={3} maxLength={2000}
                    value={body} onChange={(e) => setBody(e.target.value)}
                />
            </div>

            <div>
                <p className={labelCls}>Récompense (optionnel)</p>
                <div className="flex gap-2">
                    <select
                        className={inputCls}
                        value={rewardResourceId}
                        onChange={(e) => setRewardResourceId(e.target.value)}
                    >
                        <option value="">Aucune</option>
                        {resources.map((r) => (
                            <option key={r.id} value={r.id}>{r.name}</option>
                        ))}
                    </select>
                    {rewardResourceId && (
                        <input
                            type="number" min={1} className={`${inputCls} max-w-[100px]`}
                            placeholder="Qté" value={rewardAmount}
                            onChange={(e) => setRewardAmount(e.target.value ? Number(e.target.value) : "")}
                        />
                    )}
                </div>
            </div>

            {result && (
                <p className={`text-xs ${result.ok ? "text-green-400" : "text-red-400"}`}>{result.text}</p>
            )}

            <Button variant="primary" className="w-full" disabled={!canSend} loading={send.isPending} onClick={() => send.mutate()}>
                Envoyer
            </Button>
        </div>
    );
}

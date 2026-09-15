import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { supportApi } from "@/api/support";
import Button from "@/components/ui/Button";
import { errMsg } from "@/utils/errors";

export default function SupportPanel() {
    const [subject, setSubject] = useState("");
    const [body, setBody] = useState("");
    const [err, setErr] = useState("");
    const [sent, setSent] = useState(false);

    const submit = useMutation({
        mutationFn: () => supportApi.submitBugReport({
            subject: subject.trim(), body: body.trim(), page_context: window.location.pathname,
        }),
        onSuccess: () => {
            setSent(true);
            setSubject("");
            setBody("");
        },
        onError: (e) => setErr(errMsg(e)),
    });

    const canSend = subject.trim().length > 0 && body.trim().length > 0;

    return (
        <div className="space-y-4">
            <div className="bg-game-surface rounded-2xl border border-white/10 p-4">
                <h3 className="text-white font-bold text-sm mb-1">Signaler un bug</h3>
                <p className="text-white/40 text-xs mb-3">
                    Décris le problème rencontré (ce que tu faisais, ce qui s'est passé, ce que tu
                    attendais) — le signalement sera consulté par l'équipe.
                </p>
                <div className="space-y-2">
                    <input
                        className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30"
                        placeholder="Résumé du problème"
                        maxLength={100}
                        value={subject}
                        onChange={(e) => { setSubject(e.target.value); setSent(false); }}
                    />
                    <textarea
                        className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 resize-none"
                        placeholder="Détails..."
                        rows={5}
                        maxLength={2000}
                        value={body}
                        onChange={(e) => { setBody(e.target.value); setSent(false); }}
                    />
                </div>
                {err && <p className="text-red-400 text-xs mt-2">{err}</p>}
                {sent && !err && <p className="text-green-400 text-xs mt-2">Signalement envoyé, merci !</p>}
                <Button
                    variant="primary" className="w-full mt-3"
                    disabled={!canSend} loading={submit.isPending}
                    onClick={() => { setErr(""); submit.mutate(); }}
                >
                    Envoyer le signalement
                </Button>
            </div>

            <Link
                to="/legal"
                className="block text-center text-white/40 hover:text-white/70 text-xs underline"
            >
                Mentions légales
            </Link>
        </div>
    );
}

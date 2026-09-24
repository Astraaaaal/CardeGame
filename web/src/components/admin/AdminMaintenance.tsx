import { inputCls } from "@/components/ui/formStyles";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminMaintenanceApi } from "@/api/admin";
import Button from "@/components/ui/Button";
import { errMsg } from "@/utils/errors";

const CONFIRM_WORD = "REINITIALISER";

/** Jeu fermé (pause entre deux versions) et remise à zéro de tous les comptes. */
export default function AdminMaintenance() {
    const qc = useQueryClient();
    const statusQ = useQuery({ queryKey: ["admin", "game-status"], queryFn: adminMaintenanceApi.getStatus });
    const [message, setMessage] = useState("");
    const [confirm, setConfirm] = useState("");
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
    const [distinctionId, setDistinctionId] = useState("");
    const [reason, setReason] = useState("");
    const distinctionsQ = useQuery({ queryKey: ["admin", "distinctions"], queryFn: adminMaintenanceApi.listDistinctions });

    useEffect(() => { if (statusQ.data) setMessage(statusQ.data.message); }, [statusQ.data]);

    const save = useMutation({
        mutationFn: (closed: boolean) => adminMaintenanceApi.setStatus({ closed, message }),
        onSuccess: (s) => {
            qc.setQueryData(["admin", "game-status"], s);
            setMsg({ text: s.closed ? "Jeu fermé : seuls les porteurs de la clé admin peuvent se connecter." : "Jeu ouvert.", ok: true });
        },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });
    const reset = useMutation({
        mutationFn: () => adminMaintenanceApi.resetAccounts(confirm),
        onSuccess: (r) => {
            setConfirm("");
            qc.invalidateQueries({ queryKey: ["admin", "distinctions"] });
            setMsg({
                text: `${r.users} comptes remis à zéro (${r.cards_removed.toLocaleString("fr-FR")} cartes supprimées), `
                    + `${r.founders_granted} distinction(s) de fondateur gravée(s). Tout le monde est déconnecté.`,
                ok: true,
            });
        },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });
    const grant = useMutation({
        mutationFn: () => adminMaintenanceApi.grantDistinctionToAll({
            distinction_id: distinctionId, reason: reason.trim() || undefined,
        }),
        onSuccess: (r) => {
            qc.invalidateQueries({ queryKey: ["admin", "distinctions"] });
            setMsg({ text: `${r.granted} attribution(s) sur ${r.accounts} compte(s).`, ok: true });
        },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    if (!statusQ.data) return <p className="text-white/40 text-sm">…</p>;
    const closed = statusQ.data.closed;

    return (
        <div className="space-y-6 max-w-lg">
            {msg && <p className={`text-sm ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>}

            <section className="bg-game-surface border border-white/10 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                    <h3 className="text-white font-bold">Jeu {closed ? "fermé" : "ouvert"}</h3>
                    <span className={`w-3 h-3 rounded-full ${closed ? "bg-red-500" : "bg-green-500"}`} />
                </div>
                <p className="text-white/50 text-xs">
                    Fermé : connexion, inscription et toutes les pages du jeu sont refusées aux joueurs, qui sont renvoyés vers la
                    page de connexion avec le message ci-dessous. Toi, tu peux continuer à jouer depuis ce navigateur tant que
                    la clé admin est saisie (dans le même onglet).
                </p>
                <textarea className={`${inputCls} resize-none`} rows={3} maxLength={1000}
                    placeholder={statusQ.data.default_message} value={message} onChange={(e) => setMessage(e.target.value)} />
                <p className="text-white/30 text-[11px]">Vide = message par défaut.</p>
                <div className="flex gap-2">
                    <Button variant={closed ? "primary" : "danger"} size="sm" loading={save.isPending}
                        onClick={() => { setMsg(null); save.mutate(!closed); }}>
                        {closed ? "Rouvrir le jeu" : "Fermer le jeu"}
                    </Button>
                    {closed && (
                        <Button variant="secondary" size="sm" loading={save.isPending} onClick={() => { setMsg(null); save.mutate(true); }}>
                            Enregistrer le message
                        </Button>
                    )}
                </div>
            </section>

            <section className="bg-red-950/40 border border-red-500/40 rounded-xl p-4 space-y-3">
                <h3 className="text-white font-bold">Remettre tous les comptes à zéro</h3>
                <p className="text-white/60 text-xs leading-relaxed">
                    Gardé : comptes (pseudo, e-mail, mot de passe), réglages, amis et groupes d'amis.<br />
                    Gardé aussi, délibérément : les cosmétiques possédés et celui qui est porté, les distinctions
                    permanentes, et l'historique des achats en euros — ce qui a été payé ne s'efface pas. Seules les
                    limites « une fois par compte » se rouvrent.<br />
                    Effacé : cartes, ressources (retour aux montants de départ), boosters et rerolls stockés, niveaux, quêtes,
                    achievements, statistiques, séries, activités, vitrine, guildes, messages et cadeaux,
                    échanges et annonces, demandes d'ami en attente. Tout le monde est déconnecté.
                    <br /><span className="text-red-300 font-semibold">Irréversible.</span>
                </p>
                <input className={inputCls} placeholder={`Tape ${CONFIRM_WORD} pour confirmer`}
                    value={confirm} onChange={(e) => setConfirm(e.target.value)} />
                <Button variant="danger" size="sm" disabled={confirm.trim() !== CONFIRM_WORD} loading={reset.isPending}
                    onClick={() => { setMsg(null); reset.mutate(); }}>
                    Remettre tous les comptes à zéro
                </Button>
            </section>

            <section className="bg-game-surface border border-white/10 rounded-xl p-4 space-y-3">
                <h3 className="text-white font-bold">Offrir une distinction à tous les comptes</h3>
                <p className="text-white/50 text-xs leading-relaxed">
                    À lancer <span className="font-semibold">après</span> la remise à zéro, et avant le message qui
                    l'annonce. Relancer ne crée pas de doublon et ne retire rien.
                </p>
                <select className={inputCls} value={distinctionId} onChange={(e) => setDistinctionId(e.target.value)}>
                    <option value="">Choisir une distinction…</option>
                    {(distinctionsQ.data ?? []).map((d) => (
                        <option key={d.id} value={d.id}>{d.name} — {d.holders} porteur(s)</option>
                    ))}
                </select>
                <input className={inputCls} maxLength={100} placeholder="Raison (facultatif, ex. « première bêta »)"
                    value={reason} onChange={(e) => setReason(e.target.value)} />
                <Button variant="secondary" size="sm" disabled={!distinctionId} loading={grant.isPending}
                    onClick={() => { setMsg(null); grant.mutate(); }}>
                    Attribuer à tous les comptes
                </Button>
            </section>
        </div>
    );
}

import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { activitiesApi, type ExpeditionOut } from "@/api/activities";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import { showRewards, type RewardItem } from "@/stores/rewardPopupStore";
import Button from "@/components/ui/Button";
import CardImage from "@/components/card/CardImage";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { errMsg } from "@/utils/errors";

export const EXPEDITION_PURPOSE = "expedition";
const EXPEDITIONS_KEY = ["expeditions"];

function fmtDuration(minutes: number): string {
    return minutes >= 60 ? `${minutes / 60} h` : `${minutes} min`;
}

function fmtCountdown(seconds: number): string {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return h ? `${h} h ${String(m).padStart(2, "0")}` : `${m} min ${String(s).padStart(2, "0")} s`;
}

const pct = (x: number) => `${Math.round(x * 100)} %`;

/** Expédition en cours : équipe, compte à rebours, butin attendu, récupération. */
function ActiveExpedition({ exp, onClaim, claiming }: { exp: ExpeditionOut; onClaim: () => void; claiming: boolean }) {
    // Compte à rebours local, recalé sur la date de retour.
    const [now, setNow] = useState(Date.now());
    useEffect(() => {
        const t = window.setInterval(() => setNow(Date.now()), 1000);
        return () => window.clearInterval(t);
    }, []);
    const remaining = Math.max(0, Math.round((new Date(exp.ends_at + "Z").getTime() - now) / 1000));
    const done = exp.done || remaining === 0;

    return (
        <div className="space-y-3">
            <div className="flex gap-2">
                {exp.cards.map((c) => (
                    <div key={c.id} className="w-16"><CardImage card={c} size="sm" /></div>
                ))}
            </div>
            <div className="text-xs text-white/60 space-y-0.5">
                <p>Mission de {fmtDuration(exp.duration_minutes)} · puissance {exp.total_power.toLocaleString("fr-FR")} (×{exp.estimate.power_factor})</p>
                <p>
                    Butin : {exp.estimate.coins.toLocaleString("fr-FR")} pièces + {exp.estimate.dust.toLocaleString("fr-FR")} poussière
                    {exp.estimate.booster_chance > 0 && ` · booster ${pct(exp.estimate.booster_chance)}`}
                    {exp.estimate.rare_card_chance > 0 && ` · carte rare ${pct(exp.estimate.rare_card_chance)}`}
                </p>
            </div>
            {done ? (
                <Button variant="gold" className="w-full" loading={claiming} onClick={onClaim}>Récupérer le butin</Button>
            ) : (
                <div>
                    <div className="h-1.5 bg-black/30 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-accent transition-all"
                            style={{ width: `${100 - (remaining / (exp.duration_minutes * 60)) * 100}%` }}
                        />
                    </div>
                    <p className="text-white/40 text-xs mt-1">Retour dans {fmtCountdown(remaining)}</p>
                </div>
            )}
        </div>
    );
}

export default function ExpeditionsTab() {
    const navigate = useNavigate();
    const qc = useQueryClient();
    const requestSelection = useCardSelectionStore((s) => s.requestSelection);
    const consumeResultIfPurpose = useCardSelectionStore((s) => s.consumeResultIfPurpose);
    const { data, isLoading } = useQuery({ queryKey: EXPEDITIONS_KEY, queryFn: activitiesApi.expeditions });
    const [durations, setDurations] = useState<Record<number, number>>({});
    const [err, setErr] = useState("");
    const handled = useRef(false);

    const start = useMutation({
        mutationFn: ({ slot, duration, cardIds }: { slot: number; duration: number; cardIds: string[] }) =>
            activitiesApi.startExpedition(slot, duration, cardIds),
        onSuccess: () => { setErr(""); qc.invalidateQueries({ queryKey: EXPEDITIONS_KEY }); },
        onError: (e) => setErr(errMsg(e)),
    });

    const claim = useMutation({
        mutationFn: (id: number) => activitiesApi.claimExpedition(id),
        onSuccess: (res) => {
            const items: RewardItem[] = [
                { kind: "resource", resourceId: "coins", amount: res.coins, name: "Pièces" },
                { kind: "resource", resourceId: "dust", amount: res.dust, name: "Poussière" },
            ];
            if (res.booster_id) items.push({ kind: "booster", boosterId: res.booster_id, quantity: 1, name: res.booster_name });
            if (res.card) items.push({ kind: "card", card: res.card });
            showRewards({ title: "Retour d'expédition", items });
            qc.invalidateQueries({ queryKey: EXPEDITIONS_KEY });
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["collection"] });
            qc.invalidateQueries({ queryKey: ["booster-inventory"] });
        },
        onError: (e) => setErr(errMsg(e)),
    });

    // Retour de la Collection avec l'équipe choisie : départ immédiat.
    useEffect(() => {
        if (handled.current) return;
        const result = consumeResultIfPurpose([EXPEDITION_PURPOSE]);
        if (!result) return;
        handled.current = true;
        const slot = Number(result.context?.slot);
        const duration = Number(result.context?.duration);
        const cardIds = result.selectedCards.map((c) => c.id);
        if (cardIds.length) start.mutate({ slot, duration, cardIds });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    if (isLoading || !data) return <LoadingSpinner text="Chargement des expéditions..." />;

    const chooseTeam = (slot: number) => {
        const duration = durations[slot] ?? data.durations[0];
        requestSelection({
            max: data.max_cards,
            title: `Équipe d'expédition (1 à ${data.max_cards} cartes)`,
            excludeIds: data.locked_card_ids,
            returnTo: "/activities",
            context: { purpose: EXPEDITION_PURPOSE, slot: String(slot), duration: String(duration) },
        });
        navigate("/collection");
    };

    return (
        <div className="space-y-3">
            <p className="text-white/40 text-xs">
                Envoie jusqu'à {data.max_cards} cartes en mission : plus elles sont puissantes et plus la mission est
                longue, plus le butin est gros. Les cartes parties ne peuvent être ni échangées, ni recyclées, ni offertes.
            </p>
            {err && <p className="text-red-400 text-xs">{err}</p>}
            {data.slots.map(({ slot, expedition }) => (
                <div key={slot} className="bg-game-surface rounded-2xl border border-white/10 p-4">
                    <p className="text-white/40 text-[11px] font-semibold uppercase tracking-wide mb-2">Expédition {slot + 1}</p>
                    {expedition ? (
                        <ActiveExpedition
                            exp={expedition}
                            claiming={claim.isPending && claim.variables === expedition.id}
                            onClaim={() => claim.mutate(expedition.id)}
                        />
                    ) : (
                        <div className="space-y-2">
                            <div className="flex gap-1.5">
                                {data.durations.map((d) => {
                                    const selected = (durations[slot] ?? data.durations[0]) === d;
                                    return (
                                        <button
                                            key={d}
                                            className={`flex-1 py-1.5 rounded-lg text-xs font-bold ${selected ? "bg-accent text-white" : "bg-white/10 text-white/60"}`}
                                            onClick={() => setDurations((prev) => ({ ...prev, [slot]: d }))}
                                        >
                                            {fmtDuration(d)}
                                        </button>
                                    );
                                })}
                            </div>
                            <Button
                                variant="primary" size="sm" className="w-full"
                                loading={start.isPending && start.variables?.slot === slot}
                                onClick={() => chooseTeam(slot)}
                            >
                                Choisir l'équipe
                            </Button>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

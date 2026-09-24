import { useState } from "react";
import { toast } from "@/stores/toastStore";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { activitiesApi, type HigherLowerGameState } from "@/api/activities";
import { useAuthStore } from "@/stores/authStore";
import { getResourceBalance } from "@/utils/resources";
import Button from "@/components/ui/Button";
import CardImage from "@/components/card/CardImage";
import { errMsg } from "@/utils/errors";

const HL_KEY = ["higher-lower"];
const OUTCOME_LABEL = { win: "Bien vu !", tie: "Égalité : on continue.", lose: "Perdu…" } as const;

/** « Plus ou moins » : la carte suivante est-elle plus ou moins puissante ? */
export default function HigherLowerGame() {
    const qc = useQueryClient();
    const { user } = useAuthStore();
    const { data } = useQuery({ queryKey: HL_KEY, queryFn: activitiesApi.higherLower });
    const [resourceId, setResourceId] = useState("coins");
    const [stake, setStake] = useState(100);
    const [last, setLast] = useState<HigherLowerGameState | null>(null);
    const setErr = (m: string | null) => { if (m) toast.error(m); };

    const refresh = (game: HigherLowerGameState | null) => {
        qc.setQueryData(HL_KEY, (old: typeof data) => (old ? { ...old, game: game?.status === "active" ? game : null } : old));
        qc.invalidateQueries({ queryKey: ["player"] });
    };
    const onError = (e: unknown) => setErr(errMsg(e));

    const start = useMutation({
        // La ressource vient de l'appelant : celle affichée peut différer de
        // l'état si le joueur n'a plus de quoi miser celle qu'il avait choisie.
        mutationFn: (id: string) => activitiesApi.startHigherLower(id, stake),
        onSuccess: (g) => { setErr(""); setLast(null); refresh(g); },
        onError,
    });
    const guess = useMutation({
        mutationFn: ({ id, g }: { id: number; g: "higher" | "lower" }) => activitiesApi.guessHigherLower(id, g),
        onSuccess: (g) => { setLast(g); refresh(g); },
        onError,
    });
    const cashout = useMutation({
        mutationFn: (id: number) => activitiesApi.cashoutHigherLower(id),
        onSuccess: (g) => { setLast(g); refresh(g); },
        onError,
    });

    if (!data) return null;
    const game = data.game;
    // Ne proposer que ce qu'on possède : miser suppose d'avoir de quoi.
    const minStake = (id: string) => (id === "coins" ? data.min_stake : data.min_stake_other);
    const stakeable = data.resources.filter((r) => getResourceBalance(user, r.id) >= minStake(r.id));
    const unit = (id: string) => data.resources.find((r) => r.id === id)?.name.toLowerCase() ?? id;

    if (!game) {
        const chosen = stakeable.some((r) => r.id === resourceId) ? resourceId : stakeable[0]?.id;
        const balance = chosen ? getResourceBalance(user, chosen) : 0;
        const floor = chosen ? minStake(chosen) : data.min_stake;
        return (
            <div className="space-y-3">
                {last && last.status !== "active" && (
                    <p className={`text-sm font-semibold ${last.status === "cashed" ? "text-green-400" : "text-red-400"}`}>
                        {last.status === "cashed"
                            ? `Encaissé : +${last.cashout_value.toLocaleString("fr-FR")} ${unit(last.resource_id)}`
                            : `${OUTCOME_LABEL.lose} La carte suivante avait ⚡ ${last.current_card.power?.toLocaleString("fr-FR")}`
                              + ` (contre ⚡ ${last.previous_card?.power?.toLocaleString("fr-FR")}) : `
                              + `la mise de ${last.stake.toLocaleString("fr-FR")} est perdue.`}
                    </p>
                )}
                {stakeable.length === 0 ? (
                    <p className="text-white/40 text-[11px]">
                        Rien à miser pour l'instant : il faut au moins {data.min_stake} pièces.
                    </p>
                ) : (
                    <div className="flex gap-2 flex-wrap">
                        {stakeable.map((r) => (
                            <button
                                key={r.id}
                                className={`py-1.5 px-3 rounded-lg text-xs font-bold ${chosen === r.id ? "bg-accent text-white" : "bg-white/10 text-white/60"}`}
                                onClick={() => { setResourceId(r.id); setStake(minStake(r.id)); }}
                            >
                                {r.name}
                            </button>
                        ))}
                    </div>
                )}
                <div className="flex items-center gap-2">
                    <input
                        type="number" min={floor} max={data.max_stake} value={stake}
                        onChange={(e) => setStake(Math.max(0, Number(e.target.value) || 0))}
                        className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                    />
                    <span className="text-white/40 text-xs shrink-0">solde {balance.toLocaleString("fr-FR")}</span>
                </div>
                <p className="text-white/40 text-[11px]">
                    Mise {floor} à {data.max_stake.toLocaleString("fr-FR")}. Pari risqué = gros gain. Encaisse dès la
                    manche {data.min_cashout_step} ; une erreur fait tout perdre.
                </p>
                <Button
                    variant="primary" className="w-full" loading={start.isPending} success={start.isSuccess}
                    disabled={!chosen || stake < floor || stake > data.max_stake || stake > balance}
                    onClick={() => chosen && start.mutate(chosen)}
                >
                    Miser {stake.toLocaleString("fr-FR")} {chosen ? unit(chosen) : ""}
                </Button>
            </div>
        );
    }

    const busy = guess.isPending || cashout.isPending;
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-white/50">
                <span>Mise {game.stake.toLocaleString("fr-FR")} {unit(game.resource_id)}</span>
                <span>Manche {game.step} / {game.max_steps} · ×{game.total_multiplier.toLocaleString("fr-FR")}</span>
            </div>
            <div className="flex items-center justify-center gap-4">
                <div className="w-32"><CardImage card={game.current_card} size="md" /></div>
                <div className="w-24 aspect-[5/7] rounded-xl border-2 border-dashed border-white/20 flex items-center justify-center text-white/30 text-4xl">
                    ?
                </div>
            </div>
            <p className="text-center text-gold font-extrabold text-lg">⚡ {game.current_card.power?.toLocaleString("fr-FR")}</p>
            {last?.outcome && last.status === "active" && (
                <p className="text-center text-sm text-white/70">
                    {OUTCOME_LABEL[last.outcome]}
                    {last.won_multiplier ? ` ×${last.won_multiplier.toLocaleString("fr-FR")}` : ""}
                    {" "}La carte précédente avait ⚡ {last.previous_card?.power?.toLocaleString("fr-FR")}.
                </p>
            )}
            <div className="grid grid-cols-2 gap-2">
                {(["higher", "lower"] as const).map((g) => {
                    const m = game.odds[g];
                    return (
                        <Button key={g} variant="secondary" disabled={busy || m == null} onClick={() => guess.mutate({ id: game.id, g })}>
                            <span className="flex flex-col items-center leading-tight">
                                <span>{g === "higher" ? "Plus ▲" : "Moins ▼"}</span>
                                <span className="text-[11px] text-gold">{m == null ? "impossible" : `×${m.toLocaleString("fr-FR")}`}</span>
                            </span>
                        </Button>
                    );
                })}
            </div>
            <Button variant="gold" className="w-full" disabled={busy || !game.can_cashout} loading={cashout.isPending} success={cashout.isSuccess} onClick={() => cashout.mutate(game.id)}>
                {game.can_cashout
                    ? `Encaisser ${game.cashout_value.toLocaleString("fr-FR")} ${unit(game.resource_id)}`
                    : `Encaisser dès la manche ${game.min_cashout_step} (${game.cashout_value.toLocaleString("fr-FR")})`}
            </Button>
        </div>
    );
}

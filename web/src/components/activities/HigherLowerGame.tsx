import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { activitiesApi, type HigherLowerGameState } from "@/api/activities";
import { useAuthStore } from "@/stores/authStore";
import { getResourceBalance } from "@/utils/resources";
import Button from "@/components/ui/Button";
import CardImage from "@/components/card/CardImage";
import { errMsg } from "@/utils/errors";

const HL_KEY = ["higher-lower"];
const RESOURCES = [{ id: "coins", name: "Pièces" }, { id: "dust", name: "Poussière" }];
const OUTCOME_LABEL = { win: "Bien vu !", tie: "Égalité : on continue.", lose: "Perdu…" } as const;

/** « Plus ou moins » : la carte suivante est-elle plus ou moins puissante ? */
export default function HigherLowerGame() {
    const qc = useQueryClient();
    const { user } = useAuthStore();
    const { data } = useQuery({ queryKey: HL_KEY, queryFn: activitiesApi.higherLower });
    const [resourceId, setResourceId] = useState("coins");
    const [stake, setStake] = useState(100);
    const [last, setLast] = useState<HigherLowerGameState | null>(null);
    const [err, setErr] = useState("");

    const refresh = (game: HigherLowerGameState | null) => {
        qc.setQueryData(HL_KEY, (old: typeof data) => (old ? { ...old, game: game?.status === "active" ? game : null } : old));
        qc.invalidateQueries({ queryKey: ["player"] });
    };
    const onError = (e: unknown) => setErr(errMsg(e));

    const start = useMutation({
        mutationFn: () => activitiesApi.startHigherLower(resourceId, stake),
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
    const unit = (id: string) => (id === "coins" ? "pièces" : "poussière");

    if (!game) {
        const balance = getResourceBalance(user, resourceId);
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
                <div className="flex gap-2">
                    {RESOURCES.map((r) => (
                        <button
                            key={r.id}
                            className={`flex-1 py-1.5 rounded-lg text-xs font-bold ${resourceId === r.id ? "bg-accent text-white" : "bg-white/10 text-white/60"}`}
                            onClick={() => setResourceId(r.id)}
                        >
                            {r.name}
                        </button>
                    ))}
                </div>
                <div className="flex items-center gap-2">
                    <input
                        type="number" min={data.min_stake} max={data.max_stake} value={stake}
                        onChange={(e) => setStake(Math.max(0, Number(e.target.value) || 0))}
                        className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                    />
                    <span className="text-white/40 text-xs shrink-0">solde {balance.toLocaleString("fr-FR")}</span>
                </div>
                <p className="text-white/40 text-[11px]">
                    Mise de {data.min_stake} à {data.max_stake.toLocaleString("fr-FR")}. Chaque bonne réponse multiplie le gain
                    par {data.multiplier.toLocaleString("fr-FR")} ({data.max_steps} au plus) ; une erreur fait tout perdre.
                </p>
                {err && <p className="text-red-400 text-xs">{err}</p>}
                <Button
                    variant="primary" className="w-full" loading={start.isPending}
                    disabled={stake < data.min_stake || stake > data.max_stake || stake > balance}
                    onClick={() => start.mutate()}
                >
                    Miser {stake.toLocaleString("fr-FR")} {unit(resourceId)}
                </Button>
            </div>
        );
    }

    const busy = guess.isPending || cashout.isPending;
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-white/50">
                <span>Mise {game.stake.toLocaleString("fr-FR")} {unit(game.resource_id)}</span>
                <span>Étape {game.step} / {game.max_steps}</span>
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
                    {OUTCOME_LABEL[last.outcome]} La carte précédente avait ⚡ {last.previous_card?.power?.toLocaleString("fr-FR")}.
                </p>
            )}
            {err && <p className="text-red-400 text-xs text-center">{err}</p>}
            <div className="grid grid-cols-2 gap-2">
                <Button variant="secondary" disabled={busy} onClick={() => guess.mutate({ id: game.id, g: "higher" })}>Plus ▲</Button>
                <Button variant="secondary" disabled={busy} onClick={() => guess.mutate({ id: game.id, g: "lower" })}>Moins ▼</Button>
            </div>
            <Button variant="gold" className="w-full" disabled={busy} loading={cashout.isPending} onClick={() => cashout.mutate(game.id)}>
                Encaisser {game.cashout_value.toLocaleString("fr-FR")} {unit(game.resource_id)}
            </Button>
            <p className="text-center text-white/40 text-[11px]">
                Prochaine bonne réponse : {game.next_value.toLocaleString("fr-FR")} {unit(game.resource_id)}
            </p>
        </div>
    );
}

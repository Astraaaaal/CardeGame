import { useState } from "react";
import { toast } from "@/stores/toastStore";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { activitiesApi, type WheelSpin } from "@/api/activities";
import { showRewards, type RewardItem } from "@/stores/rewardPopupStore";
import Button from "@/components/ui/Button";
import { errMsg } from "@/utils/errors";

const WHEEL_KEY = ["wheel"];

/** Teintes sourdes et proches les unes des autres : la roue doit sembler
 *  taillée dans une même matière, pas assemblée de huit couleurs criardes. */
const COLORS = ["#3c4a80", "#2f6270", "#4d4180", "#7a6533", "#33548f", "#5d3c7a", "#2f6b62", "#7a4242"];

const SIZE = 256;
const CENTER = SIZE / 2;
const RADIUS = CENTER - 10;
/** Durée du tour : une longue décélération se regarde, un arrêt sec se subit. */
const SPIN_SECONDS = 4.2;

/** Tranche de camembert, du centre vers l'extérieur. */
function slicePath(fromDeg: number, toDeg: number): string {
    const point = (deg: number) => {
        const rad = ((deg - 90) * Math.PI) / 180;
        return `${CENTER + RADIUS * Math.cos(rad)} ${CENTER + RADIUS * Math.sin(rad)}`;
    };
    const large = toDeg - fromDeg > 180 ? 1 : 0;
    return `M ${CENTER} ${CENTER} L ${point(fromDeg)} A ${RADIUS} ${RADIUS} 0 ${large} 1 ${point(toDeg)} Z`;
}

/** Roue de la fortune : un tour gratuit par jour, puis des tours payants. */
export default function FortuneWheel() {
    const qc = useQueryClient();
    const { data } = useQuery({ queryKey: WHEEL_KEY, queryFn: activitiesApi.wheel });
    const [rotation, setRotation] = useState(0);
    const [spinning, setSpinning] = useState(false);
    const setErr = (m: string | null) => { if (m) toast.error(m); };

    const spin = useMutation({
        mutationFn: activitiesApi.spinWheel,
        onSuccess: (res: WheelSpin) => {
            setErr("");
            const n = res.state.segments.length;
            const seg = 360 / n;
            // Case gagnante sous l'aiguille (en haut), après quelques tours complets.
            const target = 360 * 5 + (360 - (res.index * seg + seg / 2));
            setSpinning(true);
            setRotation((r) => r - (r % 360) + target);
            window.setTimeout(() => {
                setSpinning(false);
                qc.setQueryData(WHEEL_KEY, res.state);
                qc.invalidateQueries({ queryKey: ["player"] });
                qc.invalidateQueries({ queryKey: ["booster-inventory"] });
                qc.invalidateQueries({ queryKey: ["reroll-tokens"] });
                const r = res.reward;
                const items: RewardItem[] = r.kind === "resource" && r.resource_id
                    ? [{ kind: "resource", resourceId: r.resource_id, amount: r.amount }]
                    : r.kind === "booster" && r.booster_id
                        ? [{ kind: "booster", boosterId: r.booster_id, quantity: r.amount, name: r.booster_name }]
                        : [{ kind: "reroll_token", name: r.label, quantity: r.amount }];
                showRewards({ title: `Roue : ${r.label}`, items });
            }, SPIN_SECONDS * 1000 + 200);
        },
        onError: (e) => setErr(errMsg(e)),
    });

    if (!data) return null;
    const n = data.segments.length;
    const seg = 360 / n;
    const extraLeft = data.extra_spins_per_day - data.extra_spins_used;
    const canSpin = data.free_available || extraLeft > 0;

    return (
        <div className="space-y-5">
            <div className="relative mx-auto" style={{ width: SIZE, height: SIZE }}>
                {/* Halo doux sous la roue, pour la détacher du fond sans trait dur. */}
                <div className="absolute inset-0 rounded-full blur-2xl opacity-40 bg-accent/30" />

                {/* Aiguille : goutte arrondie plutôt qu'un triangle coupant. */}
                <svg className="absolute left-1/2 -translate-x-1/2 -top-1 z-10 drop-shadow-lg"
                    width="26" height="30" viewBox="0 0 26 30" aria-hidden>
                    <path d="M13 29 C6 18 3 13 3 9 A10 10 0 0 1 23 9 C23 13 20 18 13 29 Z" fill="#f5d67b" />
                    <circle cx="13" cy="9.5" r="3.4" fill="#2a2440" />
                </svg>

                {/* La rotation porte sur un conteneur HTML (un <svg> pivoterait
                    autour de son coin, pas de son centre) et passe par une
                    transition CSS : une seule propriété animée, aucun risque
                    qu un rendu intermédiaire la réinitialise. */}
                <div
                    className="relative drop-shadow-[0_8px_24px_rgba(0,0,0,0.45)]"
                    style={{
                        width: SIZE, height: SIZE,
                        transform: `rotate(${rotation}deg)`,
                        transition: `transform ${SPIN_SECONDS}s cubic-bezier(0.12, 0.72, 0.16, 1)`,
                    }}
                >
                <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
                    <defs>
                        {/* Lumière rasante : la roue paraît bombée, pas imprimée à plat. */}
                        <radialGradient id="wheel-sheen" cx="35%" cy="28%" r="75%">
                            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.22" />
                            <stop offset="55%" stopColor="#ffffff" stopOpacity="0.04" />
                            <stop offset="100%" stopColor="#000000" stopOpacity="0.28" />
                        </radialGradient>
                        <linearGradient id="wheel-rim" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.35" />
                            <stop offset="100%" stopColor="#ffffff" stopOpacity="0.08" />
                        </linearGradient>
                    </defs>

                    {data.segments.map((_, i) => (
                        <g key={i}>
                            <path d={slicePath(i * seg, (i + 1) * seg)} fill={COLORS[i % COLORS.length]} />
                            {/* Séparateur fin : lisible sans découper la roue au couteau. */}
                            <path d={slicePath(i * seg, (i + 1) * seg)} fill="none"
                                stroke="#ffffff" strokeOpacity="0.12" strokeWidth="1" />
                        </g>
                    ))}

                    {data.segments.map((s, i) => {
                        const middle = i * seg + seg / 2;
                        // Dans la moitié basse, on retourne le texte : sinon il
                        // se lit la tête en bas une fois la tranche en place.
                        const flipped = middle > 90 && middle < 270;
                        return (
                            <g key={`label-${i}`}
                                transform={`rotate(${flipped ? middle + 180 : middle} ${CENTER} ${CENTER})`}>
                                <text x={CENTER} y={CENTER + (flipped ? RADIUS * 0.62 : -RADIUS * 0.62)}
                                    textAnchor="middle" className="fill-white/95 font-bold" fontSize="10.5"
                                    style={{ paintOrder: "stroke", stroke: "rgba(0,0,0,0.45)", strokeWidth: 2.5 }}>
                                    {s.label.length > 14 ? `${s.label.slice(0, 13)}…` : s.label}
                                </text>
                            </g>
                        );
                    })}

                    <circle cx={CENTER} cy={CENTER} r={RADIUS} fill="url(#wheel-sheen)" />
                    <circle cx={CENTER} cy={CENTER} r={RADIUS} fill="none" stroke="url(#wheel-rim)" strokeWidth="6" />
                    {/* Moyeu : termine la roue et masque la convergence des tranches. */}
                    <circle cx={CENTER} cy={CENTER} r="26" fill="#221d38" stroke="#f5d67b" strokeOpacity="0.5" strokeWidth="2" />
                    <circle cx={CENTER} cy={CENTER} r="9" fill="#f5d67b" fillOpacity="0.85" />
                </svg>
                </div>
            </div>

            <Button
                variant="gold" className="w-full" disabled={!canSpin || spinning} loading={spin.isPending} success={spin.isSuccess}
                onClick={() => spin.mutate()}
            >
                {data.free_available
                    ? "Tour gratuit du jour"
                    : extraLeft > 0 ? `Tourner (${data.extra_spin_cost} pièces)` : "Plus de tours aujourd'hui"}
            </Button>
            <p className="text-center text-white/40 text-[11px]">
                Tours payants restants aujourd'hui : {extraLeft} / {data.extra_spins_per_day}
            </p>
        </div>
    );
}

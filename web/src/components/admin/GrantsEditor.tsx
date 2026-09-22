import { inputCls } from "@/components/ui/formStyles";
export type GrantKind = "resource" | "booster" | "cosmetic";

export interface GrantDraft {
    kind: GrantKind;
    id: string;
    amount: number;
}

export interface GrantOptions {
    resources: { id: string; name: string }[];
    boosters: { id: string; name: string }[];
    cosmetics: { id: string; name: string }[];
}


/** Contenu d'un lot : ressources (Éclats comprises), boosters, cosmétiques.
 * Partagé par les produits premium (euros) et les offres « lot » de la boutique. */
export default function GrantsEditor({ grants, options, onChange }: {
    grants: GrantDraft[];
    options: GrantOptions;
    onChange: (grants: GrantDraft[]) => void;
}) {
    const optionsFor = (kind: GrantKind) =>
        kind === "resource" ? options.resources : kind === "booster" ? options.boosters : options.cosmetics;
    const patch = (i: number, p: Partial<GrantDraft>) =>
        onChange(grants.map((g, j) => (j === i ? { ...g, ...p } : g)));

    return (
        <div className="space-y-2">
            {grants.map((g, i) => (
                <div key={i} className="flex gap-1.5">
                    <select
                        className={`${inputCls} w-28`}
                        value={g.kind}
                        onChange={(e) => {
                            const kind = e.target.value as GrantKind;
                            patch(i, { kind, id: optionsFor(kind)[0]?.id ?? "", amount: 1 });
                        }}
                    >
                        <option value="resource">Ressource</option>
                        <option value="booster">Booster</option>
                        <option value="cosmetic">Cosmétique</option>
                    </select>
                    <select className={inputCls} value={g.id} onChange={(e) => patch(i, { id: e.target.value })}>
                        {optionsFor(g.kind).map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
                    </select>
                    {g.kind !== "cosmetic" && (
                        <input
                            type="number" min="1" className={`${inputCls} w-24`} value={g.amount}
                            onChange={(e) => patch(i, { amount: Math.max(1, +e.target.value) })}
                        />
                    )}
                    <button
                        className="text-red-400/70 hover:text-red-400 px-1"
                        onClick={() => onChange(grants.filter((_, j) => j !== i))}
                    >
                        ×
                    </button>
                </div>
            ))}
            <button
                className="text-accent text-xs"
                onClick={() => onChange([...grants, { kind: "resource", id: options.resources[0]?.id ?? "coins", amount: 100 }])}
            >
                + Ajouter un élément
            </button>
        </div>
    );
}

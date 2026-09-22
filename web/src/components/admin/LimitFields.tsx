import { inputCls, labelCls } from "@/components/ui/formStyles";
import type { LimitPeriod } from "@/types/shop";
import { LIMIT_PERIOD_LABEL } from "@/utils/purchaseLimits";


const PERIODS: LimitPeriod[] = ["none", "day", "week", "month", "account"];

/** Limite d'achat : période + nombre autorisé (offres boutique et produits premium). */
export default function LimitFields({ period, count, onChange }: {
    period: LimitPeriod;
    count: number;
    onChange: (limit: { limit_period: LimitPeriod; limit_count: number }) => void;
}) {
    return (
        <div className="grid grid-cols-2 gap-2">
            <div>
                <label className={labelCls}>Limite d'achat</label>
                <select
                    className={inputCls}
                    value={period}
                    onChange={(e) => onChange({ limit_period: e.target.value as LimitPeriod, limit_count: count || 1 })}
                >
                    {PERIODS.map((p) => (
                        <option key={p} value={p}>{LIMIT_PERIOD_LABEL[p]}</option>
                    ))}
                </select>
            </div>
            {period !== "none" && (
                <div>
                    <label className={labelCls}>Nombre autorisé</label>
                    <input
                        type="number" min={1} className={inputCls} value={count}
                        onChange={(e) => onChange({ limit_period: period, limit_count: Math.max(1, +e.target.value) })}
                    />
                </div>
            )}
        </div>
    );
}

import type { LimitPeriod } from "@/types/shop";

/** Libellés des limites d'achat (cf. backend app/services/purchase_limits.py). */
export const LIMIT_PERIOD_LABEL: Record<LimitPeriod, string> = {
    none: "Aucune limite",
    day: "par jour",
    week: "par semaine",
    month: "par mois",
    account: "une fois pour toutes",
};

export const LIMIT_WHEN_LABEL: Record<LimitPeriod, string> = {
    none: "",
    day: "aujourd'hui",
    week: "cette semaine",
    month: "ce mois",
    account: "au total",
};

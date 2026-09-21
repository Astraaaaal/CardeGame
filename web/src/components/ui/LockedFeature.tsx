import { useUnlocks, type FeatureKey } from "@/hooks/useUnlocks";

/**
 * Affiche `children` si la fonctionnalité est débloquée, sinon un encart
 * « 🔒 Se débloque au niveau N » (la fonctionnalité reste visible).
 */
export default function LockedFeature({ feature, children, compact = false }: {
    feature: FeatureKey;
    children: React.ReactNode;
    compact?: boolean;
}) {
    const { isUnlocked, levelFor, labelFor, level } = useUnlocks();
    if (isUnlocked(feature)) return <>{children}</>;
    return (
        <div className={`bg-black/20 border border-white/10 rounded-2xl text-center ${compact ? "px-3 py-2.5" : "px-4 py-6"}`}>
            <p className={`text-white/70 font-semibold ${compact ? "text-sm" : ""}`}>🔒 {labelFor(feature)}</p>
            <p className="text-white/40 text-xs mt-1">
                Se débloque au niveau {levelFor(feature)} (tu es niveau {level}).
            </p>
        </div>
    );
}

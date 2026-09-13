import Modal from "@/components/ui/Modal";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { useProbabilities } from "@/hooks/useCollection";
import type { ProbabilityItem } from "@/api/collection";

function AxisTable({ title, items }: { title: string; items: ProbabilityItem[] }) {
    return (
        <div>
            <p className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-1.5">{title}</p>
            <div className="space-y-1">
                {items.map((it) => (
                    <div key={it.id} className="flex items-center justify-between text-sm">
                        <span className="text-white/80">{it.name}</span>
                        <span className="text-accent font-semibold tabular-nums">
                            {it.percentage.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} %
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default function ProbabilityModal({ open, onClose }: { open: boolean; onClose: () => void }) {
    const { data, isLoading } = useProbabilities(open);

    return (
        <Modal open={open} onClose={onClose} title="📊 Table des probabilités">
            <p className="text-white/40 text-xs mb-4">
                Chances de base par axe à l'ouverture d'un pack (les axes sont tirés indépendamment,
                la probabilité d'une carte précise est le produit des quatre). Certains boosters ou
                offres spéciales peuvent relever temporairement la rareté minimum.
            </p>
            {isLoading || !data ? (
                <LoadingSpinner text="Chargement..." />
            ) : (
                <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
                    <AxisTable title="Rareté" items={data.rarities} />
                    <AxisTable title="Qualité" items={data.qualities} />
                    <AxisTable title="Spécialité" items={data.specialties} />
                    <AxisTable title="Jewelry" items={data.jewelries} />
                </div>
            )}
        </Modal>
    );
}

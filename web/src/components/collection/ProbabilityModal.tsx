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

function HelpBlock({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="bg-black/20 border border-white/5 rounded-lg p-3">
            <p className="text-gold text-xs font-semibold uppercase tracking-wide mb-1.5">{title}</p>
            <p className="text-white/60 text-xs leading-relaxed">{children}</p>
        </div>
    );
}

export default function ProbabilityModal({ open, onClose }: { open: boolean; onClose: () => void }) {
    const { data, isLoading } = useProbabilities(open);

    return (
        <Modal open={open} onClose={onClose} title="Table des probabilités">
            <div className="space-y-2 mb-4 max-h-[35vh] overflow-y-auto pr-1">
                <HelpBlock title="Puissance">
                    Chaque carte reçoit une puissance tirée au hasard entre 1 et un maximum : plus sa
                    combinaison est rare, plus ce maximum est haut (l'inverse de sa probabilité de tirage).
                    Il est plafonné selon la <b>meilleure</b> caractéristique de la carte :
                    <span className="block mt-1 text-white/70">
                        5 000 : rien de mieux que commune, déchirée, normale, sans bijou · 10 000 : rare, argent,
                        rayée à usée · 15 000 : épique, or, correcte à préservée · 20 000 : légendaire ·
                        25 000 : diamant, full art, EX, excellente, gradée · 35 000 : prismatique, mint ·
                        50 000 : shiny, authentique.
                    </span>
                </HelpBlock>
                <HelpBlock title="Chance et garanties">
                    La chance (présence, guilde, machine) augmente tes chances d'atteindre le maximum d'une
                    carte, jamais de le dépasser. Un minimum garanti remonte le tirage s'il tombe en dessous :
                    les paliers au-dessus gardent leur chance normale. Le tri « Chance » combine puissance et
                    rareté pour trouver tes cartes les plus chanceuses.
                </HelpBlock>
                <HelpBlock title="Full art">
                    Seuls certains personnages existent en full art. Pour les autres, un tirage full art donne
                    une carte sans spécialité.
                </HelpBlock>
                <HelpBlock title="Recyclage">
                    Toute carte rapporte de la poussière (plus sa rareté est haute, plus la plage est grande),
                    et chaque palier ajoute sa ressource : fragments (rareté), minerais (bijou), encre, sceau ou
                    paillettes (spécialité), poussières fine à d'étoile (qualité). Plus la puissance est proche
                    du maximum de la carte, plus la quantité est haute, tirée au hasard dans une fourchette
                    affichée avant de confirmer.
                </HelpBlock>
                <HelpBlock title="Niveaux et prestige">
                    Ton niveau dépend de ta puissance totale. Après le dernier niveau de la route, les niveaux
                    de prestige continuent sans fin : chacun demande un peu plus de puissance et rapporte des
                    pièces et un fragment légendaire.
                </HelpBlock>
            </div>

            <p className="text-white/40 text-xs mb-4">
                Chances de base par axe à l'ouverture d'un pack (les axes sont tirés indépendamment,
                la probabilité d'une carte précise est le produit des quatre). Certains boosters ou
                offres spéciales peuvent relever temporairement la rareté minimum.
            </p>
            {isLoading || !data ? (
                <LoadingSpinner text="Chargement..." />
            ) : (
                <div className="space-y-4 max-h-[35vh] overflow-y-auto pr-1">
                    <AxisTable title="Rareté" items={data.rarities} />
                    <AxisTable title="Qualité" items={data.qualities} />
                    <AxisTable title="Spécialité" items={data.specialties} />
                    <AxisTable title="Jewelry" items={data.jewelries} />
                </div>
            )}
        </Modal>
    );
}

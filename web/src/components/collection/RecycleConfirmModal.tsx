import { useState } from "react";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import RecyclePreview from "./RecyclePreview";
import type { SelectionSummary } from "@/utils/recycleSelection";

interface RecycleConfirmModalProps {
    cardIds: string[];
    summary: SelectionSummary;
    pending: boolean;
    onConfirm: () => void;
    onClose: () => void;
}

/**
 * Confirmation avant recyclage : toujours le récap chiffré et la fourchette
 * de gains ; si la sélection contient un favori ou une carte d'une des
 * meilleures raretés, un avertissement rouge et une seconde validation.
 */
export default function RecycleConfirmModal({
    cardIds, summary, pending, onConfirm, onClose,
}: RecycleConfirmModalProps) {
    const risky = summary.favorites > 0 || summary.precious > 0;
    const [acknowledged, setAcknowledged] = useState(false);

    return (
        <Modal open onClose={onClose} title="Recycler ces cartes ?">
            <div className="space-y-3">
                <p className="text-white/70 text-sm">
                    <span className="text-white font-bold">{summary.count}</span>{" "}
                    {summary.count > 1 ? "exemplaires vont être détruits" : "exemplaire va être détruit"}.
                    C'est irréversible.
                </p>

                <RecyclePreview cardIds={cardIds} />

                {risky && (
                    <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 space-y-2">
                        <p className="text-red-300 text-xs font-semibold">Attention à cette sélection :</p>
                        <ul className="text-red-200/80 text-xs list-disc list-inside space-y-0.5">
                            {summary.precious > 0 && (
                                <li>{summary.precious} carte{summary.precious > 1 ? "s" : ""} d'une rareté élevée</li>
                            )}
                            {summary.favorites > 0 && (
                                <li>{summary.favorites} exemplaire{summary.favorites > 1 ? "s" : ""} rangé{summary.favorites > 1 ? "s" : ""} dans tes favoris</li>
                            )}
                        </ul>
                        <label className="flex items-center gap-2 text-red-200 text-xs">
                            <input type="checkbox" checked={acknowledged}
                                onChange={(e) => setAcknowledged(e.target.checked)} />
                            Oui, je veux quand même les recycler
                        </label>
                    </div>
                )}

                <div className="flex gap-2 pt-1">
                    <Button variant="secondary" className="flex-1" onClick={onClose}>Annuler</Button>
                    <Button variant="danger" className="flex-1" loading={pending}
                        disabled={risky && !acknowledged}
                        onClick={onConfirm}>
                        Recycler
                    </Button>
                </div>
            </div>
        </Modal>
    );
}

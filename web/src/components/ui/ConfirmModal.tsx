import type { ReactNode } from "react";
import Modal from "./Modal";
import Button from "./Button";

interface ConfirmModalProps {
    open: boolean;
    title: string;
    message: string;
    warning?: string; // ligne d'avertissement supplémentaire, mise en évidence
    children?: ReactNode; // contenu affiché sous le message (ex. aperçu de ce qu'on gagne)
    confirmLabel?: string;
    confirmVariant?: "primary" | "danger" | "gold";
    busy: boolean;
    onConfirm: () => void;
    onCancel: () => void;
}

/** Modale de confirmation générique (remplace window.confirm) pour toute action irréversible. */
export default function ConfirmModal({
    open, title, message, warning, children, confirmLabel = "Confirmer",
    confirmVariant = "danger", busy, onConfirm, onCancel,
}: ConfirmModalProps) {
    return (
        <Modal open={open} onClose={onCancel} title={title}>
            <p className="text-white/70 text-sm mb-2">{message}</p>
            {children}
            {warning && (
                <p className="text-gold text-sm font-semibold mb-4 bg-gold/10 border border-gold/30 rounded-lg px-3 py-2">
                    {warning}
                </p>
            )}
            <div className="flex gap-2 mt-2">
                <Button variant={confirmVariant} className="flex-1" loading={busy} onClick={onConfirm}>
                    {confirmLabel}
                </Button>
                <Button variant="secondary" onClick={onCancel}>Annuler</Button>
            </div>
        </Modal>
    );
}

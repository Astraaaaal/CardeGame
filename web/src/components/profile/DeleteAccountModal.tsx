import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { playerApi } from "@/api/player";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import { errMsg } from "@/utils/errors";

interface DeleteAccountModalProps {
    onClose: () => void;
    onDeleted: () => void;
}

export default function DeleteAccountModal({ onClose, onDeleted }: DeleteAccountModalProps) {
    const [password, setPassword] = useState("");
    const [err, setErr] = useState("");

    const del = useMutation({
        mutationFn: () => playerApi.deleteAccount(password),
        onSuccess: () => onDeleted(),
        onError: (e) => setErr(errMsg(e)),
    });

    return (
        <Modal open onClose={onClose} title="Supprimer mon compte">
            <div className="space-y-3">
                <p className="text-white/70 text-sm">
                    Cette action est définitive et irréversible : ta collection, tes ressources,
                    tes messages, tes amis et ton historique d'échanges seront supprimés sans
                    possibilité de récupération.
                </p>
                <p className="text-gold text-sm font-semibold bg-gold/10 border border-gold/30 rounded-lg px-3 py-2">
                    Confirme en saisissant ton mot de passe.
                </p>
                <input
                    type="password"
                    className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="Mot de passe"
                    value={password}
                    onChange={(e) => { setPassword(e.target.value); setErr(""); }}
                    onKeyDown={(e) => e.key === "Enter" && password && del.mutate()}
                    autoFocus
                />
                {err && <p className="text-red-400 text-xs">{err}</p>}
                <div className="flex gap-2 mt-2">
                    <Button
                        variant="danger"
                        className="flex-1"
                        disabled={!password}
                        loading={del.isPending}
                        onClick={() => del.mutate()}
                    >
                        Supprimer définitivement
                    </Button>
                    <Button variant="secondary" onClick={onClose}>Annuler</Button>
                </div>
            </div>
        </Modal>
    );
}

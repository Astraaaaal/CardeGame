import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { playerApi } from "@/api/player";
import { useAuthStore } from "@/stores/authStore";
import { useLogout } from "@/hooks/useAuth";
import Button from "@/components/ui/Button";
import PasswordInput from "@/components/ui/PasswordInput";
import { errMsg } from "@/utils/errors";
import EmailSettings from "@/components/profile/EmailSettings";

/** Adresse e-mail et newsletter, nom affiché, changement de mot de passe. */
export default function AccountEditor() {
    const navigate = useNavigate();
    const { user, setUser } = useAuthStore();
    const logout = useLogout();
    const qc = useQueryClient();

    const [displayName, setDisplayName] = useState(user?.display_name ?? "");
    const [nameMsg, setNameMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const [currentPwd, setCurrentPwd] = useState("");
    const [newPwd, setNewPwd] = useState("");
    const [confirmPwd, setConfirmPwd] = useState("");
    const [pwdMsg, setPwdMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const updateName = useMutation({
        mutationFn: () => playerApi.updateProfile(displayName.trim()),
        onSuccess: (player) => {
            setUser(player);
            qc.invalidateQueries({ queryKey: ["player"] });
            setNameMsg({ text: "Nom mis à jour.", ok: true });
        },
        onError: (e) => setNameMsg({ text: errMsg(e), ok: false }),
    });

    const changePwd = useMutation({
        mutationFn: () => playerApi.changePassword(currentPwd, newPwd),
        onSuccess: () => {
            setPwdMsg({ text: "Mot de passe changé. Reconnexion...", ok: true });
            setTimeout(() => {
                logout();
                navigate("/login");
            }, 1200);
        },
        onError: (e) => setPwdMsg({ text: errMsg(e), ok: false }),
    });

    const handlePwdSubmit = () => {
        setPwdMsg(null);
        if (newPwd.length < 4) {
            setPwdMsg({ text: "Le nouveau mot de passe doit faire au moins 4 caractères.", ok: false });
            return;
        }
        if (newPwd !== confirmPwd) {
            setPwdMsg({ text: "Les deux mots de passe ne correspondent pas.", ok: false });
            return;
        }
        changePwd.mutate();
    };

    return (
        <div className="space-y-6">
            <EmailSettings />

            <div className="bg-game-surface rounded-2xl border border-white/10 p-4">
                <h3 className="text-white font-bold text-sm mb-3">Nom affiché</h3>
                <div className="flex gap-2">
                    <input
                        className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                        value={displayName}
                        maxLength={20}
                        onChange={(e) => { setDisplayName(e.target.value); setNameMsg(null); }}
                    />
                    <Button
                        variant="primary" size="sm"
                        disabled={!displayName.trim() || displayName.trim() === user?.display_name}
                        loading={updateName.isPending} success={updateName.isSuccess}
                        onClick={() => updateName.mutate()}
                    >
                        Enregistrer
                    </Button>
                </div>
                {nameMsg && (
                    <p className={`text-xs mt-2 ${nameMsg.ok ? "text-green-400" : "text-red-400"}`}>
                        {nameMsg.text}
                    </p>
                )}
            </div>

            <div className="bg-game-surface rounded-2xl border border-white/10 p-4">
                <h3 className="text-white font-bold text-sm mb-3">Changer le mot de passe</h3>
                <div className="space-y-2">
                    <input
                        type="password"
                        className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                        placeholder="Mot de passe actuel"
                        value={currentPwd}
                        onChange={(e) => { setCurrentPwd(e.target.value); setPwdMsg(null); }}
                    />
                    <PasswordInput
                        className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                        placeholder="Nouveau mot de passe"
                        value={newPwd}
                        onChange={(e) => { setNewPwd(e.target.value); setPwdMsg(null); }}
                    />
                    <input
                        type="password"
                        className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                        placeholder="Confirmer le nouveau mot de passe"
                        value={confirmPwd}
                        onChange={(e) => { setConfirmPwd(e.target.value); setPwdMsg(null); }}
                    />
                    <Button
                        variant="primary" size="sm" className="w-full"
                        disabled={!currentPwd || !newPwd || !confirmPwd}
                        loading={changePwd.isPending} success={changePwd.isSuccess}
                        onClick={handlePwdSubmit}
                    >
                        Changer le mot de passe
                    </Button>
                </div>
                {pwdMsg && (
                    <p className={`text-xs mt-2 ${pwdMsg.ok ? "text-green-400" : "text-red-400"}`}>
                        {pwdMsg.text}
                    </p>
                )}
                <p className="text-white/30 text-xs mt-3">
                    Changer le mot de passe te déconnecte de toutes tes sessions — tu devras te reconnecter.
                </p>
            </div>
        </div>
    );
}

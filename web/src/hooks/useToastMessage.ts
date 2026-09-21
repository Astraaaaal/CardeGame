import { useCallback } from "react";
import { toast } from "@/stores/toastStore";

type Msg = { text: string; ok: boolean } | null;

/**
 * Remplaçant de `useState<{ text, ok }>` pour les messages de retour d'une
 * action : ils partent dans le bandeau (cf. Toaster) au lieu d'un texte dans
 * la page. La valeur lue vaut toujours null (plus rien à afficher sur place).
 */
export function useToastMessage(): [Msg, (m: Msg) => void] {
    const set = useCallback((m: Msg) => {
        if (!m) return;
        if (m.ok) toast.success(m.text);
        else toast.error(m.text);
    }, []);
    return [null, set];
}

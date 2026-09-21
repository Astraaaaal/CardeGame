/**
 * Extrait un message lisible d'une erreur axios.
 * Gère les deux formes de `detail` renvoyées par le backend FastAPI :
 * - une chaîne (HTTPException(status, "message") levée à la main) ;
 * - un tableau d'erreurs de validation Pydantic (422 automatique), chacune
 *   avec `loc` (chemin du champ fautif) et `msg` — sans ce cas, ces erreurs
 *   tombaient silencieusement sur un "Erreur." générique sans indice.
 */
export function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
        if (typeof detail === "string") return detail;
        // Jeu fermé : { code: "game_closed", message }
        if (detail && typeof detail === "object" && "message" in detail && typeof (detail as { message: unknown }).message === "string") {
            return (detail as { message: string }).message;
        }
        if (Array.isArray(detail) && detail.length > 0) {
            return detail
                .map((d) => {
                    const loc = Array.isArray(d?.loc) ? d.loc[d.loc.length - 1] : null;
                    const msg = typeof d?.msg === "string" ? d.msg : "valeur invalide";
                    return loc ? `${loc} : ${msg}` : msg;
                })
                .join(" — ");
        }
    }
    // Pas de réponse du serveur (réseau coupé, serveur qui redémarre…).
    if (e && typeof e === "object" && "request" in e && !(e as { response?: unknown }).response) {
        return "Impossible de joindre le serveur : vérifie ta connexion et réessaie.";
    }
    const status = (e as { response?: { status?: number } })?.response?.status;
    if (status && status >= 500) return "Le serveur a rencontré un problème. Réessaie dans un instant.";
    if (status === 429) return "Doucement ! Trop d'actions d'un coup, réessaie dans quelques secondes.";
    return "Une erreur inattendue est survenue.";
}

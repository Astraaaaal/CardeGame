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
    return "Erreur.";
}

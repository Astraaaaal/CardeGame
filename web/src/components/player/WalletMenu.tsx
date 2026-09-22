import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { shopApi } from "@/api/shop";
import { useAuthStore } from "@/stores/authStore";
import { getResourceBalance } from "@/utils/resources";
import ResourceIcon from "@/components/ui/ResourceIcon";
import { PREMIUM_RESOURCE_ID } from "@/components/shop/PremiumTab";

/** Solde d'Éclats (monnaie premium) ; au clic, menu avec les autres ressources et leur quantité. */
export default function WalletMenu() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);
    const { data: catalog } = useQuery({
        queryKey: ["resources-catalog"], queryFn: shopApi.resources, staleTime: 5 * 60 * 1000,
    });

    useEffect(() => {
        if (!open) return;
        const close = (e: PointerEvent) => {
            if (!ref.current?.contains(e.target as Node)) setOpen(false);
        };
        document.addEventListener("pointerdown", close);
        return () => document.removeEventListener("pointerdown", close);
    }, [open]);

    // Pièces et Éclats sont déjà affichés en haut du menu ; ressources possédées d'abord.
    const others = (catalog ?? [])
        .filter((r) => r.id !== "coins" && r.id !== PREMIUM_RESOURCE_ID)
        .sort((a, b) => Number(getResourceBalance(user, b.id) > 0) - Number(getResourceBalance(user, a.id) > 0));

    return (
        <div ref={ref} className="relative">
            <button
                className="flex items-center gap-1.5 bg-black/30 rounded-full px-3 py-1.5 hover:bg-black/50 transition-colors"
                title="Éclats — voir mes ressources"
                aria-expanded={open}
                onClick={() => setOpen((o) => !o)}
            >
                <span className="text-cyan-300 text-lg leading-none">✦</span>
                <span className="text-cyan-200 font-bold tabular-nums">
                    {getResourceBalance(user, PREMIUM_RESOURCE_ID).toLocaleString("fr-FR")}
                </span>
                <span className="text-white/40 text-xs">{open ? "▲" : "▼"}</span>
            </button>

            {open && (
                <div className="absolute left-0 top-full mt-2 z-40 w-60 max-h-[70vh] overflow-y-auto bg-game-surface border border-white/10 rounded-xl shadow-2xl p-2">
                    <p className="text-white/40 text-[11px] font-semibold uppercase tracking-wide px-2 pt-1 pb-2">Ressources</p>
                    {others.length === 0 ? (
                        <p className="text-white/40 text-xs px-2 pb-2">Aucune autre ressource.</p>
                    ) : (
                        others.map((r) => (
                            <div key={r.id} className={`flex items-center gap-2 px-2 py-1.5 text-sm ${getResourceBalance(user, r.id) ? "" : "opacity-40"}`}>
                                <ResourceIcon resourceId={r.id} />
                                <span className="flex-1 text-white/80">{r.name}</span>
                                <span className="text-white font-bold tabular-nums">
                                    {getResourceBalance(user, r.id).toLocaleString("fr-FR")}
                                </span>
                            </div>
                        ))
                    )}
                    <button
                        className="w-full text-accent text-xs font-semibold text-left px-2 pt-2 mt-1 border-t border-white/5"
                        onClick={() => navigate("/inventory")}
                    >
                        Voir l'inventaire →
                    </button>
                </div>
            )}
        </div>
    );
}

import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { tradeSessionsApi } from "@/api/tradeSessions";

/** Bandeau discret quand une session d'échange est en cours ailleurs — pour
 * pouvoir la retrouver si on a quitté la page (Warframe garde aussi la
 * fenêtre de trade accessible tant qu'elle n'est pas conclue). */
export default function ActiveTradeBanner() {
    const navigate = useNavigate();
    const { data } = useQuery({
        queryKey: ["trade-session-active"],
        queryFn: tradeSessionsApi.getActive,
        refetchInterval: 15_000,
    });

    return (
        <AnimatePresence>
            {data && (
                <motion.button
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="mx-4 mt-3 flex items-center justify-between gap-2 bg-accent/15 border border-accent/40
                               rounded-xl px-4 py-2.5 text-left"
                    onClick={() => navigate(`/trade/${data.id}`)}
                >
                    <span className="text-white text-sm">
                        Échange en cours avec <span className="font-semibold">{data.other_display_name}</span>
                    </span>
                    <span className="text-accent text-xs font-semibold shrink-0">Reprendre</span>
                </motion.button>
            )}
        </AnimatePresence>
    );
}

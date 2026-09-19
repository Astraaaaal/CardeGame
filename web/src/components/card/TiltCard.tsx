import { createContext, useContext, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

export const MAX_DEG = 14;

/** Inclinaison courante (degrés), pour les effets qui réagissent au mouvement. */
const TiltContext = createContext({ x: 0, y: 0 });
export const useTilt = () => useContext(TiltContext);
// Marge autour de la carte où l'inclinaison réagit encore : elle commence à
// suivre le curseur avant qu'il n'arrive sur la carte, et ne retombe pas dès
// qu'il en effleure le bord.
const MARGIN = 60;

/**
 * Inclinaison 3D d'une carte qui suit le doigt ou la souris, et revient
 * doucement droite quand il s'éloigne. Réservé aux endroits où UNE carte est
 * mise en avant (détail, révélation de booster) : dans une grille, des dizaines
 * de cartes animées en même temps font ramer les téléphones.
 */
export default function TiltCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
    const ref = useRef<HTMLDivElement>(null);
    const [tilt, setTilt] = useState({ x: 0, y: 0 });
    const [resting, setResting] = useState(true);

    // Écoute globale : le curseur peut sortir de la carte sans qu'un
    // « pointerleave » nous parvienne (superpositions, animations en cours).
    useEffect(() => {
        const onMove = (e: PointerEvent) => {
            const box = ref.current?.getBoundingClientRect();
            if (!box || !box.width) return;
            const px = (e.clientX - box.left) / box.width * 2 - 1;
            const py = (e.clientY - box.top) / box.height * 2 - 1;
            const outside = e.clientX < box.left - MARGIN || e.clientX > box.right + MARGIN
                || e.clientY < box.top - MARGIN || e.clientY > box.bottom + MARGIN;
            if (outside) {
                setResting(true);
                setTilt({ x: 0, y: 0 });
                return;
            }
            setResting(false);
            setTilt({ x: -py * MAX_DEG, y: px * MAX_DEG });
        };
        const onLeave = () => { setResting(true); setTilt({ x: 0, y: 0 }); };

        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onLeave);
        window.addEventListener("pointercancel", onLeave);
        return () => {
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", onLeave);
            window.removeEventListener("pointercancel", onLeave);
        };
    }, []);

    return (
        <motion.div
            ref={ref}
            className={className}
            style={{ perspective: 800 }}
            animate={{ rotateX: tilt.x, rotateY: tilt.y }}
            // Retour au repos bien plus lent que le suivi du curseur.
            transition={resting
                ? { type: "spring", stiffness: 40, damping: 15, mass: 1.3 }
                : { type: "spring", stiffness: 300, damping: 24 }}
        >
            <TiltContext.Provider value={tilt}>{children}</TiltContext.Provider>
        </motion.div>
    );
}

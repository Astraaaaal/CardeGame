import { createContext, useContext, useEffect, useRef, useState } from "react";
import { motion, useMotionValue, useSpring, type MotionValue } from "framer-motion";

export const MAX_DEG = 14;

/**
 * Inclinaison courante, en **valeurs animées** plutôt qu'en état React.
 *
 * Un `useState` mis à jour à chaque mouvement de souris redessinait toute la
 * carte et ses effets cent fois par seconde — d'où le rendu saccadé. Une
 * valeur animée se met à jour sans repasser par React : seul le style change,
 * et l'animation tourne côté compositeur.
 */
const TiltContext = createContext<{ x: MotionValue<number>; y: MotionValue<number> } | null>(null);

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
    // `resting` reste un état React : il ne change que deux fois par geste
    // (entrée, sortie), contre cent fois pour la position.
    const [resting, setResting] = useState(true);

    const rawX = useMotionValue(0);
    const rawY = useMotionValue(0);
    const spring = resting
        // Retour au repos bien plus lent que le suivi du curseur.
        ? { stiffness: 40, damping: 15, mass: 1.3 }
        : { stiffness: 300, damping: 24 };
    const x = useSpring(rawX, spring);
    const y = useSpring(rawY, spring);

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
                rawX.set(0);
                rawY.set(0);
                return;
            }
            setResting(false);
            rawX.set(-py * MAX_DEG);
            rawY.set(px * MAX_DEG);
        };
        const onLeave = () => { setResting(true); rawX.set(0); rawY.set(0); };

        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onLeave);
        window.addEventListener("pointercancel", onLeave);
        return () => {
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", onLeave);
            window.removeEventListener("pointercancel", onLeave);
        };
    }, [rawX, rawY]);

    return (
        <motion.div
            ref={ref}
            className={className}
            style={{ perspective: 800, rotateX: x, rotateY: y }}
        >
            <TiltContext.Provider value={{ x, y }}>{children}</TiltContext.Provider>
        </motion.div>
    );
}

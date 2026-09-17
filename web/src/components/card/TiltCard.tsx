import { useRef, useState } from "react";
import { motion } from "framer-motion";

const MAX_DEG = 12;

/**
 * Inclinaison 3D d'une carte qui suit le doigt ou la souris, et revient droite
 * quand on relâche. Réservé aux endroits où UNE carte est mise en avant
 * (détail, révélation de booster) : dans une grille, des dizaines de cartes
 * animées en même temps font ramer les téléphones et gênent la lecture.
 */
export default function TiltCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
    const ref = useRef<HTMLDivElement>(null);
    const [tilt, setTilt] = useState({ x: 0, y: 0 });

    const follow = (clientX: number, clientY: number) => {
        const box = ref.current?.getBoundingClientRect();
        if (!box) return;
        const px = (clientX - box.left) / box.width - 0.5;
        const py = (clientY - box.top) / box.height - 0.5;
        setTilt({ x: -py * 2 * MAX_DEG, y: px * 2 * MAX_DEG });
    };

    return (
        <motion.div
            ref={ref}
            className={className}
            style={{ perspective: 800, touchAction: "pan-y" }}
            animate={{ rotateX: tilt.x, rotateY: tilt.y }}
            transition={{ type: "spring", stiffness: 260, damping: 22 }}
            onPointerMove={(e) => follow(e.clientX, e.clientY)}
            onPointerLeave={() => setTilt({ x: 0, y: 0 })}
            onPointerUp={() => setTilt({ x: 0, y: 0 })}
            onPointerCancel={() => setTilt({ x: 0, y: 0 })}
        >
            {children}
        </motion.div>
    );
}

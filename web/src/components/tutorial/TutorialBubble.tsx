import { AnimatePresence, motion } from "framer-motion";
import { useAuthStore } from "@/stores/authStore";
import { useTutorialStore } from "@/stores/tutorialStore";
import TutorialSphere from "./TutorialSphere";

/**
 * La bulle du tutoriel, posée au-dessus de l'écran courant.
 *
 * Elle se place en bas, au-dessus de la barre d'onglets, et laisse le reste de
 * l'écran visible : on explique un écran en le montrant, pas en le cachant.
 */
export default function TutorialBubble() {
    const userId = useAuthStore((s) => s.user?.id);
    const { queue, index, next, skipAll, blocked } = useTutorialStore();
    const step = blocked ? undefined : queue[index];

    return (
        <AnimatePresence>
            {step && (
                <motion.div
                    key="tuto"
                    className="fixed inset-x-0 bottom-16 desktop:bottom-4 z-[60] px-3 pointer-events-none"
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 16 }}
                    transition={{ duration: 0.25 }}
                >
                    <div className="max-w-mobile mx-auto flex items-end gap-2.5 pointer-events-auto">
                        <TutorialSphere size={44} />

                        <div className="relative flex-1 bg-game-panel border border-accent/30 rounded-2xl px-4 py-3 shadow-xl shadow-black/40">
                            {/* Pointe vers la sphère : l'œil relie les deux sans y penser. */}
                            <span
                                className="absolute -left-1.5 bottom-4 w-3 h-3 bg-game-panel border-l border-b border-accent/30"
                                style={{ transform: "rotate(45deg)" }}
                                aria-hidden
                            />
                            {step.title && (
                                <p className="text-accent text-[11px] font-bold uppercase tracking-wide mb-0.5">
                                    {step.title}
                                </p>
                            )}
                            <p className="text-white text-sm leading-relaxed">{step.text}</p>

                            <div className="flex items-center justify-between mt-2.5">
                                {/* Dire combien il en reste : un tutoriel dont on ne voit
                                    pas la fin donne envie de le fuir. */}
                                <span className="text-white/35 text-[11px] tabular-nums">
                                    {queue.length > 1 ? `${index + 1} / ${queue.length}` : ""}
                                </span>
                                <div className="flex items-center gap-3">
                                    {queue.length > 1 && index + 1 < queue.length && (
                                        <button
                                            className="text-white/40 hover:text-white/70 text-xs"
                                            onClick={() => skipAll(userId)}
                                        >
                                            Passer
                                        </button>
                                    )}
                                    <button
                                        className="bg-gold text-game-bg text-xs font-bold rounded-full px-4 py-1.5 hover:brightness-110 transition"
                                        onClick={() => next(userId)}
                                    >
                                        {index + 1 >= queue.length ? "Compris" : "Suivant"}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

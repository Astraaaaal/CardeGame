import { AnimatePresence, motion } from "framer-motion";
import { useToastStore, type ToastKind } from "@/stores/toastStore";

const STYLE: Record<ToastKind, string> = {
    success: "bg-green-600/95 border-green-300/40",
    info: "bg-accent/95 border-white/30",
    error: "bg-red-600/95 border-red-300/40",
};
const ICON: Record<ToastKind, string> = { success: "✓", info: "i", error: "!" };

/** Bandeau animé en haut de l'écran (cf. stores/toastStore.ts). */
export default function Toaster() {
    const { toasts, dismiss } = useToastStore();
    return (
        <div className="fixed top-2 inset-x-0 z-[100] flex flex-col items-center gap-2 px-4 pointer-events-none">
            <AnimatePresence initial={false}>
                {toasts.map((t) => (
                    <motion.button
                        key={t.id}
                        layout
                        initial={{ y: -40, opacity: 0, scale: 0.95 }}
                        animate={{ y: 0, opacity: 1, scale: 1 }}
                        exit={{ y: -30, opacity: 0 }}
                        transition={{ type: "spring", stiffness: 420, damping: 30 }}
                        className={`pointer-events-auto max-w-sm w-full flex items-center gap-2.5 rounded-xl border px-3.5 py-2.5
                            text-white text-sm font-semibold shadow-xl shadow-black/40 text-left ${STYLE[t.kind]}`}
                        onClick={() => dismiss(t.id)}
                    >
                        <span className="w-5 h-5 shrink-0 rounded-full bg-white/25 flex items-center justify-center text-xs font-extrabold">
                            {ICON[t.kind]}
                        </span>
                        <span className="flex-1">{t.text}</span>
                    </motion.button>
                ))}
            </AnimatePresence>
        </div>
    );
}

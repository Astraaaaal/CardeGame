import { useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";

interface CollapsibleSectionProps {
    title: string;
    badge?: number;
    defaultOpen?: boolean;
    /** Icônes d'action (renommer, supprimer...) affichées avant la flèche. */
    actions?: ReactNode;
    children: ReactNode;
}

/** Section repliable façon "gestion d'amis" (flèche + titre, déroule au clic). */
export default function CollapsibleSection({
    title, badge, defaultOpen = false, actions, children,
}: CollapsibleSectionProps) {
    const [open, setOpen] = useState(defaultOpen);

    return (
        <div className="border border-white/5 rounded-lg overflow-hidden">
            <div className="w-full flex items-center bg-black/20 hover:bg-black/30 transition-colors">
                <button
                    className="flex-1 flex items-center gap-2 px-3 py-2 text-left"
                    onClick={() => setOpen((v) => !v)}
                >
                    <motion.span
                        className="text-white/40 text-xs shrink-0"
                        animate={{ rotate: open ? 90 : 0 }}
                        transition={{ duration: 0.15 }}
                    >
                        ▶
                    </motion.span>
                    <span className="text-white text-sm font-semibold flex-1">{title}</span>
                    {!!badge && (
                        <span className="inline-flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4 shrink-0">
                            {badge}
                        </span>
                    )}
                </button>
                {actions && <div className="flex items-center gap-2 pr-3 shrink-0">{actions}</div>}
            </div>
            <AnimatePresence initial={false}>
                {open && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <div className="p-3 space-y-2">{children}</div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

import { ButtonHTMLAttributes, ReactNode, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary" | "solid" | "danger" | "gold";
    size?: "sm" | "md" | "lg";
    loading?: boolean;
    /** Passe à vrai quand l'action a réussi (ex. `mutation.isSuccess`) : le
     * bouton affiche une coche animée un court instant. */
    success?: boolean;
    children: ReactNode;
}

const variants = {
    primary: "bg-accent hover:bg-accent/80 text-white",
    secondary: "bg-white/10 hover:bg-white/20 text-white border border-white/20",
    // Comme secondary mais opaque — pour les boutons flottants au-dessus du contenu.
    solid: "bg-game-panel hover:bg-[#34344C] text-white border border-white/20",
    danger: "bg-red-600 hover:bg-red-700 text-white",
    gold: "bg-gold hover:bg-gold/80 text-game-bg font-bold",
};

const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-5 py-2.5 text-base",
    lg: "px-8 py-3.5 text-lg",
};

export default function Button({
    variant = "primary",
    size = "md",
    loading = false,
    success = false,
    children,
    className = "",
    disabled,
    ...props
}: ButtonProps) {
    // Coche affichée ~1,2 s à chaque passage de `success` de faux à vrai.
    const [flash, setFlash] = useState(false);
    const prev = useRef(success);
    useEffect(() => {
        if (success && !prev.current) {
            setFlash(true);
            const t = setTimeout(() => setFlash(false), 1200);
            prev.current = success;
            return () => clearTimeout(t);
        }
        prev.current = success;
    }, [success]);

    return (
        <button
            className={`
        rounded-xl font-semibold transition-all duration-200
        active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]} ${sizes[size]} ${className}
      `}
            disabled={disabled || loading}
            {...props}
        >
            {loading ? (
                <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                        <circle
                            className="opacity-25"
                            cx="12" cy="12" r="10"
                            stroke="currentColor" strokeWidth="4" fill="none"
                        />
                        <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                        />
                    </svg>
                    Chargement...
                </span>
            ) : (
                <span className="relative flex w-full items-center justify-center">
                    <span className={`block w-full ${flash ? "opacity-0" : ""}`}>{children}</span>
                    <AnimatePresence>
                        {flash && (
                            <motion.span
                                className="absolute inset-0 flex items-center justify-center"
                                initial={{ scale: 0.3, opacity: 0 }}
                                animate={{ scale: [0.3, 1.25, 1], opacity: 1 }}
                                exit={{ opacity: 0 }}
                                transition={{ duration: 0.35 }}
                            >
                                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                    <motion.path d="M5 13l4 4L19 7" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.3, delay: 0.1 }} />
                                </svg>
                            </motion.span>
                        )}
                    </AnimatePresence>
                </span>
            )}
        </button>
    );
}

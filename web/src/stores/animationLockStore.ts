import { useEffect } from "react";
import { create } from "zustand";

/**
 * Verrou posé par les écrans dont l'animation ne doit pas être interrompue
 * (ouverture de booster, et d'autres à venir) : tant qu'il est tenu, pas
 * de popup ni d'entrée automatique dans un échange — ça attend la sortie
 * de l'écran. Compteur plutôt que booléen pour supporter plusieurs détenteurs.
 */
interface AnimationLockState {
    holders: number;
    acquire: () => void;
    release: () => void;
}

export const useAnimationLockStore = create<AnimationLockState>()((set) => ({
    holders: 0,
    acquire: () => set((s) => ({ holders: s.holders + 1 })),
    release: () => set((s) => ({ holders: Math.max(0, s.holders - 1) })),
}));

export const useIsAnimationLocked = () => useAnimationLockStore((s) => s.holders > 0);

/** À appeler dans le composant de l'animation : verrou tenu tant qu'il est monté. */
export function useHoldAnimationLock() {
    const acquire = useAnimationLockStore((s) => s.acquire);
    const release = useAnimationLockStore((s) => s.release);
    useEffect(() => {
        acquire();
        return release;
    }, [acquire, release]);
}

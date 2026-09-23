import { useEffect } from "react";
import { useAuthStore } from "@/stores/authStore";
import { useUnlocks, type FeatureKey } from "@/hooks/useUnlocks";
import { useTutorialStore, type TutorialStep } from "@/stores/tutorialStore";
import { unlockStep } from "./tutorialSteps";

/**
 * Annonce les fonctionnalités au moment où elles s'ouvrent.
 *
 * On ne parle que de ce qui vient de changer : à la première observation, on
 * enregistre l'état sans rien dire. Sans ça, un joueur déjà avancé (ou qui a
 * pris trois niveaux pendant son absence) recevrait dix bulles d'affilée —
 * exactement le tutoriel indigeste qu'on cherche à éviter.
 */
const knownKey = (userId: number | undefined) => `tuto-unlocks-${userId ?? "anon"}`;

function readKnown(userId: number | undefined): string[] | null {
    try {
        const raw = localStorage.getItem(knownKey(userId));
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
}

function writeKnown(userId: number | undefined, keys: string[]): void {
    try {
        localStorage.setItem(knownKey(userId), JSON.stringify(keys));
    } catch { /* stockage indisponible */ }
}

export function useUnlockAnnouncements(): void {
    const userId = useAuthStore((s) => s.user?.id);
    const { data } = useUnlocks();
    const enqueue = useTutorialStore((s) => s.enqueue);

    useEffect(() => {
        if (!data || !userId) return;
        const ouvertes = (Object.keys(data.features) as FeatureKey[])
            .filter((key) => data.features[key]?.unlocked);

        const connues = readKnown(userId);
        if (connues === null) {
            writeKnown(userId, ouvertes);
            return;
        }

        const dejaVues = new Set(connues);
        const nouvelles = ouvertes.filter((key) => !dejaVues.has(key));
        if (nouvelles.length) {
            const etapes = nouvelles.map(unlockStep).filter((s): s is TutorialStep => !!s);
            if (etapes.length) enqueue(userId, etapes);
            writeKnown(userId, ouvertes);
        }
    }, [data, userId, enqueue]);
}

/** Empile une étape ponctuelle (situation rencontrée) quand la condition est vraie. */
export function useSituationStep(step: TutorialStep, condition: boolean): void {
    const userId = useAuthStore((s) => s.user?.id);
    const enqueue = useTutorialStore((s) => s.enqueue);

    useEffect(() => {
        if (condition) enqueue(userId, [step]);
    }, [condition, enqueue, step, userId]);
}

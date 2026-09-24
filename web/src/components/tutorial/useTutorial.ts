import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { useUnlocks, type FeatureKey } from "@/hooks/useUnlocks";
import { useTutorialStore, type TutorialStep } from "@/stores/tutorialStore";
import { featuresForScreen } from "./featureScreens";
import { unlockStep } from "./tutorialSteps";

/**
 * Annonce les fonctionnalités **sur leur écran**, pas au moment du déblocage.
 *
 * Une bulle qui parle de la roue de la fortune pendant qu'on ouvre un booster
 * ne veut rien dire. On note donc ce qui vient de s'ouvrir, et on attend que
 * le joueur arrive sur l'écran concerné pour le lui expliquer.
 *
 * À la première observation, on enregistre l'état sans rien dire : sans ça, un
 * joueur déjà avancé recevrait dix bulles d'affilée — exactement le tutoriel
 * indigeste qu'on cherche à éviter.
 */
const knownKey = (userId: number | undefined) => `tuto-unlocks-${userId ?? "anon"}`;
const pendingKey = (userId: number | undefined) => `tuto-attente-${userId ?? "anon"}`;

function read(key: string): string[] | null {
    try {
        const raw = localStorage.getItem(key);
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
}

function write(key: string, values: string[]): void {
    try {
        localStorage.setItem(key, JSON.stringify(values));
    } catch { /* stockage indisponible */ }
}

export function useUnlockAnnouncements(): void {
    const userId = useAuthStore((s) => s.user?.id);
    const { data } = useUnlocks();
    const { pathname } = useLocation();
    const enqueue = useTutorialStore((s) => s.enqueue);

    // 1. Repérer ce qui vient de s'ouvrir, et le mettre en attente.
    useEffect(() => {
        if (!data || !userId) return;
        const ouvertes = (Object.keys(data.features) as FeatureKey[])
            .filter((key) => data.features[key]?.unlocked);

        const connues = read(knownKey(userId));
        if (connues === null) {
            write(knownKey(userId), ouvertes);
            return;
        }

        const dejaVues = new Set(connues);
        const nouvelles = ouvertes.filter((key) => !dejaVues.has(key));
        if (nouvelles.length) {
            const attente = new Set(read(pendingKey(userId)) ?? []);
            for (const key of nouvelles) attente.add(key);
            write(pendingKey(userId), [...attente]);
        }
        // On réécrit dès que la liste change, y compris quand elle rétrécit :
        // après une remise à zéro des comptes tout se reverrouille, et sans
        // cette mise à jour un joueur revenu ne reverrait plus jamais de bulle.
        if (nouvelles.length || ouvertes.length !== connues.length) {
            write(knownKey(userId), ouvertes);
        }
    }, [data, userId]);

    // 2. En arrivant sur un écran, dire ce qui l'attendait.
    useEffect(() => {
        if (!userId) return;
        const attente = read(pendingKey(userId));
        if (!attente?.length) return;

        const ici = featuresForScreen(pathname);
        const aDire = attente.filter((key) => ici.includes(key as FeatureKey));
        if (!aDire.length) return;

        const etapes = aDire.map((key) => unlockStep(key as FeatureKey))
            .filter((s): s is TutorialStep => !!s);
        if (etapes.length) enqueue(userId, etapes);
        write(pendingKey(userId), attente.filter((key) => !aDire.includes(key)));
    }, [pathname, userId, enqueue]);
}

/** Empile une étape ponctuelle (situation rencontrée) quand la condition est vraie. */
export function useSituationStep(step: TutorialStep, condition: boolean): void {
    const userId = useAuthStore((s) => s.user?.id);
    const enqueue = useTutorialStore((s) => s.enqueue);

    useEffect(() => {
        if (condition) enqueue(userId, [step]);
    }, [condition, enqueue, step, userId]);
}

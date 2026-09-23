import { create } from "zustand";

/**
 * Tutoriel : une file de bulles, et la mémoire de ce qui a déjà été dit.
 *
 * La mémoire vit dans le stockage local, par joueur (même convention que les
 * marqueurs « seen-level-<id> » déjà en place). Conséquence assumée : un
 * joueur qui change d'appareil revoit les bulles une fois. C'est le prix d'un
 * mécanisme sans table serveur — et revoir une explication coûte moins cher
 * que de ne jamais l'avoir eue.
 */

export interface TutorialStep {
    /** Identifiant mémorisé : une bulle vue ne revient jamais. */
    id: string;
    text: string;
    /** Titre court, affiché au-dessus du texte quand il apporte quelque chose. */
    title?: string;
}

interface TutorialState {
    queue: TutorialStep[];
    index: number;
    /** Une fenêtre occupe l'écran (récompense quotidienne…) : la bulle attend
     *  son tour plutôt que de parler par-dessus. */
    blocked: boolean;
    setBlocked: (value: boolean) => void;
    /** Empile les étapes pas encore vues par ce joueur. */
    enqueue: (userId: number | undefined, steps: TutorialStep[]) => void;
    next: (userId: number | undefined) => void;
    skipAll: (userId: number | undefined) => void;
}

const storageKey = (userId: number | undefined) => `tuto-seen-${userId ?? "anon"}`;

function seenSet(userId: number | undefined): Set<string> {
    try {
        return new Set<string>(JSON.parse(localStorage.getItem(storageKey(userId)) ?? "[]"));
    } catch {
        // Stockage indisponible (navigation privée, réglages stricts) : on
        // repart d'une mémoire vide plutôt que de casser l'écran.
        return new Set();
    }
}

function remember(userId: number | undefined, ids: string[]): void {
    try {
        const seen = seenSet(userId);
        for (const id of ids) seen.add(id);
        localStorage.setItem(storageKey(userId), JSON.stringify([...seen]));
    } catch { /* stockage indisponible */ }
}

export const hasSeen = (userId: number | undefined, id: string) => seenSet(userId).has(id);

export const useTutorialStore = create<TutorialState>((set, get) => ({
    queue: [],
    index: 0,
    blocked: false,

    setBlocked: (value) => set({ blocked: value }),

    enqueue: (userId, steps) => {
        const seen = seenSet(userId);
        const enFile = new Set(get().queue.map((s) => s.id));
        const nouvelles = steps.filter((s) => !seen.has(s.id) && !enFile.has(s.id));
        if (!nouvelles.length) return;
        set((state) => ({ queue: [...state.queue, ...nouvelles] }));
    },

    next: (userId) => {
        const { queue, index } = get();
        const courante = queue[index];
        if (courante) remember(userId, [courante.id]);
        if (index + 1 >= queue.length) {
            set({ queue: [], index: 0 });
        } else {
            set({ index: index + 1 });
        }
    },

    // « Passer » vaut pour la séquence en cours, pas pour tout le tutoriel :
    // les bulles des fonctionnalités à venir reviendront à leur déblocage.
    skipAll: (userId) => {
        const { queue } = get();
        remember(userId, queue.map((s) => s.id));
        set({ queue: [], index: 0 });
    },
}));

import { create } from "zustand";

/**
 * Bandeau de messages en haut de l'écran (réussite, info, erreur), partout
 * dans le jeu. Un même message répété dans la seconde n'est affiché qu'une
 * fois (ex. erreur signalée à la fois par la page et par le filet global).
 */
export type ToastKind = "success" | "info" | "error";

export interface Toast {
    id: number;
    kind: ToastKind;
    text: string;
}

interface ToastState {
    toasts: Toast[];
    show: (kind: ToastKind, text: string) => void;
    dismiss: (id: number) => void;
}

const DURATION: Record<ToastKind, number> = { success: 2500, info: 3500, error: 4500 };
let nextId = 1;
const recent = new Map<string, number>();

export const useToastStore = create<ToastState>()((set) => ({
    toasts: [],
    show: (kind, text) => {
        if (!text) return;
        const key = `${kind}:${text}`;
        const now = Date.now();
        if ((recent.get(key) ?? 0) > now - 1200) return;
        recent.set(key, now);
        const id = nextId++;
        set((s) => ({ toasts: [...s.toasts.slice(-2), { id, kind, text }] }));
        setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), DURATION[kind]);
    },
    dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

export const toast = {
    success: (text: string) => useToastStore.getState().show("success", text),
    info: (text: string) => useToastStore.getState().show("info", text),
    error: (text: string) => useToastStore.getState().show("error", text),
};

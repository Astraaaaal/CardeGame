import { create } from "zustand";
import { persist } from "zustand/middleware";

/** Réglages audio, propres à cet appareil (gardés dans le navigateur). */
interface AudioState {
    sfx: boolean;
    music: boolean;
    vibration: boolean;
    volume: number; // 0 → 1
    set: (patch: Partial<Omit<AudioState, "set">>) => void;
}

export const useAudioStore = create<AudioState>()(
    persist(
        (set) => ({
            sfx: true,
            music: false,      // la musique ne démarre que si le joueur l'allume
            vibration: true,
            volume: 0.6,
            set: (patch) => set(patch),
        }),
        { name: "audio-settings" },
    ),
);

/**
 * Sons du jeu, synthétisés par le navigateur (Web Audio) : aucun fichier à
 * charger, aucun droit d'auteur. La musique d'ambiance, elle, est un fichier
 * déposé dans web/public/audio/ambiance.mp3 (absent = rien ne joue).
 *
 * Les navigateurs interdisent de jouer un son avant une interaction : le
 * contexte audio n'est créé qu'au premier clic (cf. unlockAudio).
 */

import { useAudioStore } from "@/stores/audioStore";

const MUSIC_URL = "/audio/ambiance.mp3";

let ctx: AudioContext | null = null;
let music: HTMLAudioElement | null = null;

function context(): AudioContext | null {
    if (typeof window === "undefined") return null;
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    ctx ??= new Ctor();
    if (ctx.state === "suspended") void ctx.resume();
    return ctx;
}

/**
 * Une note : forme d'onde, fréquence (glissando possible), durée et volume.
 *
 * L'enveloppe monte sur un cinquième de la durée puis redescend lentement :
 * une attaque instantanée donnait un son de bouton d'ascenseur. Un passe-bas
 * coupe les harmoniques hautes, qui rendaient les sons agressifs au casque.
 */
function note(
    { type = "sine", from, to, start = 0, duration = 0.12, gain = 0.2, cutoff = 1800 }:
    { type?: OscillatorType; from: number; to?: number; start?: number; duration?: number;
      gain?: number; cutoff?: number },
    volume: number,
) {
    const audio = context();
    if (!audio) return;
    const at = audio.currentTime + start;
    const osc = audio.createOscillator();
    const amp = audio.createGain();
    const tone = audio.createBiquadFilter();
    tone.type = "lowpass";
    tone.frequency.setValueAtTime(cutoff, at);
    osc.type = type;
    osc.frequency.setValueAtTime(from, at);
    if (to) osc.frequency.exponentialRampToValueAtTime(to, at + duration);
    // Montée douce (20 % de la durée) puis longue extinction : rien ne claque.
    const peak = Math.max(0.0001, gain * volume);
    amp.gain.setValueAtTime(0.0001, at);
    amp.gain.exponentialRampToValueAtTime(peak, at + duration * 0.2);
    amp.gain.exponentialRampToValueAtTime(0.0001, at + duration);
    osc.connect(tone).connect(amp).connect(audio.destination);
    osc.start(at);
    osc.stop(at + duration + 0.05);
}

// Une octave plus bas qu'avant : les aigus perçaient, surtout au casque.
const C4 = 262, E4 = 330, G4 = 392, C5 = 523, E5 = 659, G5 = 784, C6 = 1046;

type Sfx = "click" | "success" | "fail" | "reward" | "levelUp"
    | "revealCommon" | "revealRare" | "revealEpic" | "revealLegendary";

const SOUNDS: Record<Sfx, (v: number) => void> = {
    // Clic : note grave et courte, presque un toc feutré.
    click: (v) => note({ from: 320, to: 260, duration: 0.09, gain: 0.09, cutoff: 900 }, v),
    success: (v) => {
        note({ from: G4, duration: 0.18, gain: 0.16, cutoff: 1400 }, v);
        note({ from: C5, start: 0.12, duration: 0.3, gain: 0.14, cutoff: 1600 }, v);
    },
    // Échec : descente douce, sans dent de scie.
    fail: (v) => note({ from: 260, to: 150, duration: 0.42, gain: 0.12, cutoff: 700 }, v),
    // Récompense : le dessin qui plaisait, juste adouci par l'enveloppe commune.
    reward: (v) => [C5, E5, G5].forEach((f, i) => note({ from: f, start: i * 0.07, duration: 0.16 }, v)),
    levelUp: (v) => [C4, E4, G4, C5].forEach((f, i) =>
        note({ from: f, start: i * 0.1, duration: 0.42, gain: 0.15, cutoff: 1600 }, v)),
    revealCommon: (v) => note({ from: 330, duration: 0.16, gain: 0.09, cutoff: 900 }, v),
    revealRare: (v) => {
        note({ from: G4, duration: 0.2, gain: 0.11, cutoff: 1200 }, v);
        note({ from: C5, start: 0.13, duration: 0.28, gain: 0.1, cutoff: 1400 }, v);
    },
    revealEpic: (v) => [E4, G4, C5].forEach((f, i) =>
        note({ from: f, start: i * 0.09, duration: 0.36, gain: 0.12, cutoff: 1600 }, v)),
    revealLegendary: (v) => {
        [C4, E4, G4, C5, E5].forEach((f, i) =>
            note({ from: f, start: i * 0.1, duration: 0.55, gain: 0.13, cutoff: 1800 }, v));
        // Nappe qui s'ouvre derrière l'arpège, au lieu du sifflement aigu.
        note({ from: G5, to: C6, start: 0.35, duration: 0.8, gain: 0.05, cutoff: 1500 }, v);
    },
};

const VIBRATIONS: Partial<Record<Sfx, number | number[]>> = {
    success: 25, fail: [12, 40, 12], levelUp: [20, 40, 40], reward: 20,
    revealEpic: 15, revealLegendary: [20, 30, 60],
};

/** Joue un son (et vibre sur mobile si l'effet le prévoit), selon les réglages. */
export function play(name: Sfx) {
    const { sfx, volume, vibration } = useAudioStore.getState();
    if (sfx) SOUNDS[name]?.(volume);
    const pattern = VIBRATIONS[name];
    if (vibration && pattern && typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(pattern);
}

/** Son de révélation d'une carte, selon sa rareté. */
export function playReveal(rarityId: string) {
    play(rarityId === "legendary" ? "revealLegendary"
        : rarityId === "epic" ? "revealEpic"
            : rarityId === "rare" ? "revealRare" : "revealCommon");
}

/** Musique d'ambiance : démarrée / arrêtée selon les réglages (silencieuse si le fichier manque). */
export function syncMusic() {
    const { music: on, volume } = useAudioStore.getState();
    if (!on) {
        music?.pause();
        return;
    }
    if (!music) {
        music = new Audio(MUSIC_URL);
        music.loop = true;
        music.addEventListener("error", () => { music = null; }); // pas de fichier : on n'insiste pas
    }
    music.volume = Math.min(1, volume * 0.5);
    void music.play().catch(() => undefined);  // refusé avant interaction : réessayé au premier clic
}

/** Premier clic de la page : débloque le son et lance la musique si elle est activée. */
export function unlockAudio() {
    context();
    syncMusic();
}

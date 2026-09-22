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

/** Une note : forme d'onde, fréquence (glissando possible), durée et volume. */
function note(
    { type = "sine", from, to, start = 0, duration = 0.12, gain = 0.2 }:
    { type?: OscillatorType; from: number; to?: number; start?: number; duration?: number; gain?: number },
    volume: number,
) {
    const audio = context();
    if (!audio) return;
    const at = audio.currentTime + start;
    const osc = audio.createOscillator();
    const amp = audio.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(from, at);
    if (to) osc.frequency.exponentialRampToValueAtTime(to, at + duration);
    // Attaque courte puis extinction : évite les clics désagréables.
    amp.gain.setValueAtTime(0.0001, at);
    amp.gain.exponentialRampToValueAtTime(Math.max(0.0001, gain * volume), at + 0.01);
    amp.gain.exponentialRampToValueAtTime(0.0001, at + duration);
    osc.connect(amp).connect(audio.destination);
    osc.start(at);
    osc.stop(at + duration + 0.02);
}

const C5 = 523, E5 = 659, G5 = 784, C6 = 1046, E6 = 1319;

type Sfx = "click" | "success" | "fail" | "reward" | "levelUp"
    | "revealCommon" | "revealRare" | "revealEpic" | "revealLegendary";

const SOUNDS: Record<Sfx, (v: number) => void> = {
    click: (v) => note({ type: "triangle", from: 660, duration: 0.05, gain: 0.12 }, v),
    success: (v) => { note({ from: C5, duration: 0.1 }, v); note({ from: G5, start: 0.09, duration: 0.16 }, v); },
    fail: (v) => note({ type: "sawtooth", from: 320, to: 120, duration: 0.28, gain: 0.14 }, v),
    reward: (v) => [C5, E5, G5].forEach((f, i) => note({ from: f, start: i * 0.07, duration: 0.16 }, v)),
    levelUp: (v) => [C5, E5, G5, C6].forEach((f, i) => note({ type: "triangle", from: f, start: i * 0.08, duration: 0.22 }, v)),
    revealCommon: (v) => note({ type: "triangle", from: 520, duration: 0.08, gain: 0.1 }, v),
    revealRare: (v) => { note({ from: 600, duration: 0.1 }, v); note({ from: 900, start: 0.08, duration: 0.14 }, v); },
    revealEpic: (v) => [G5, C6, E6].forEach((f, i) => note({ from: f, start: i * 0.06, duration: 0.2 }, v)),
    revealLegendary: (v) => {
        [C5, E5, G5, C6, E6].forEach((f, i) => note({ type: "triangle", from: f, start: i * 0.07, duration: 0.3 }, v));
        note({ type: "sine", from: 2000, to: 3500, start: 0.3, duration: 0.5, gain: 0.08 }, v);
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

/**
 * Emojis personnalisés du jeu : chaque image de src/assets/emojis devient un
 * emoji, son nom de fichier donnant le code (`dragon.png` → `:dragon:`).
 * Les graphistes n'ont qu'à déposer un fichier (cf. le LISEZMOI du dossier).
 */
const files = import.meta.glob("../assets/emojis/*.{png,gif,webp,svg}", {
    eager: true, query: "?url", import: "default",
}) as Record<string, string>;

export const EMOJIS: { name: string; url: string }[] = Object.entries(files)
    .map(([path, url]) => ({ name: path.split("/").pop()!.replace(/\.[^.]+$/, "").toLowerCase(), url }))
    .filter((e) => /^[a-z0-9_]+$/.test(e.name))
    .sort((a, b) => a.name.localeCompare(b.name));

export const EMOJI_URL: Record<string, string> = Object.fromEntries(EMOJIS.map((e) => [e.name, e.url]));

export const EMOJI_PATTERN = /:([a-z0-9_]+):/g;

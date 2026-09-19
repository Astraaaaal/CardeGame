import { useEffect, useRef, useState } from "react";
import { EMOJIS } from "@/utils/emojis";

type Field = HTMLInputElement | HTMLTextAreaElement;

/**
 * Bouton 🙂 qui ouvre la grille des emojis du jeu ; un clic insère `:nom:`
 * à la position du curseur dans le champ ciblé. Masqué s'il n'y a aucun emoji.
 */
export default function EmojiPicker({ target, value, onChange }: {
    target: React.RefObject<Field>;
    value: string;
    onChange: (next: string) => void;
}) {
    const [open, setOpen] = useState(false);
    const box = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!open) return;
        const close = (e: PointerEvent) => {
            if (!box.current?.contains(e.target as Node)) setOpen(false);
        };
        window.addEventListener("pointerdown", close);
        return () => window.removeEventListener("pointerdown", close);
    }, [open]);

    if (!EMOJIS.length) return null;

    const insert = (name: string) => {
        const field = target.current;
        const code = `:${name}:`;
        const start = field?.selectionStart ?? value.length;
        const end = field?.selectionEnd ?? value.length;
        const max = field?.maxLength && field.maxLength > 0 ? field.maxLength : Infinity;
        const next = value.slice(0, start) + code + value.slice(end);
        if (next.length > max) return;
        onChange(next);
        requestAnimationFrame(() => {
            field?.focus();
            field?.setSelectionRange(start + code.length, start + code.length);
        });
    };

    return (
        <div ref={box} className="relative shrink-0">
            <button type="button" title="Emojis"
                className="w-9 h-9 rounded-lg bg-white/10 hover:bg-white/20 text-lg flex items-center justify-center"
                onClick={() => setOpen((v) => !v)}>
                🙂
            </button>
            {open && (
                <div className="absolute bottom-full right-0 mb-2 z-40 w-56 max-h-48 overflow-y-auto grid grid-cols-6 gap-1 p-2
                    bg-game-panel border border-white/15 rounded-xl shadow-xl">
                    {EMOJIS.map((e) => (
                        <button key={e.name} type="button" title={`:${e.name}:`}
                            className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center"
                            onClick={() => insert(e.name)}>
                            <img src={e.url} alt={e.name} className="w-6 h-6" />
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

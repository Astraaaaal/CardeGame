import { Fragment } from "react";
import { EMOJI_PATTERN, EMOJI_URL } from "@/utils/emojis";

/** Texte où chaque code `:nom:` connu est remplacé par l'image de l'emoji. */
export default function EmojiText({ text }: { text: string }) {
    const parts: React.ReactNode[] = [];
    let last = 0;
    for (const match of text.matchAll(EMOJI_PATTERN)) {
        const url = EMOJI_URL[match[1]];
        if (!url) continue;  // code inconnu : laissé tel quel
        const start = match.index ?? 0;
        if (start > last) parts.push(text.slice(last, start));
        parts.push(
            <img key={start} src={url} alt={match[0]} title={match[0]}
                className="inline-block w-[1.4em] h-[1.4em] align-[-0.3em] mx-[0.05em]" />,
        );
        last = start + match[0].length;
    }
    if (last < text.length) parts.push(text.slice(last));
    return <>{parts.map((p, i) => <Fragment key={i}>{p}</Fragment>)}</>;
}

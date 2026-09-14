import CoinIcon from "./CoinIcon";

/** Icône d'une ressource — pièces (SVG, cf. CoinIcon) ou autre (✨, rend bien partout). */
export default function ResourceIcon({
    resourceId,
    className = "w-[1em] h-[1em] align-[-0.15em]",
}: {
    resourceId: string;
    className?: string;
}) {
    if (resourceId === "coins") return <CoinIcon className={className} />;
    return <span>✨</span>;
}

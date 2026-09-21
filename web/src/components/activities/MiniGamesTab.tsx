import HigherLowerGame from "./HigherLowerGame";
import LockedFeature from "@/components/ui/LockedFeature";
import FortuneWheel from "./FortuneWheel";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <section className="bg-game-surface rounded-2xl border border-white/10 p-4 space-y-3">
            <h2 className="text-white font-bold text-sm">{title}</h2>
            {children}
        </section>
    );
}

/** Mini-jeux : mises en pièces ou en poussière uniquement (jamais d'Éclats). */
export default function MiniGamesTab() {
    return (
        <div className="space-y-4">
            <Section title="Plus ou moins"><LockedFeature feature="higher_lower" compact><HigherLowerGame /></LockedFeature></Section>
            <Section title="Roue de la fortune"><FortuneWheel /></Section>
        </div>
    );
}

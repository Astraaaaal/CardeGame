import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import BottomNav from "@/components/layout/BottomNav";
import ExpeditionsTab, { EXPEDITION_PURPOSE } from "@/components/activities/ExpeditionsTab";
import WorkshopTab from "@/components/activities/WorkshopTab";

type Tab = "expeditions" | "workshop";

const TABS: { key: Tab; label: string }[] = [
    { key: "expeditions", label: "Expéditions" },
    { key: "workshop", label: "Atelier" },
];

/** Activités hors combat : expéditions, atelier, mini-jeux. */
export default function Activities() {
    const navigate = useNavigate();
    // Onglet mémorisé le temps de la session (retour de la Collection après le
    // choix d'une équipe d'expédition : on revient sur les expéditions).
    const [tab, setTab] = useState<Tab>(() => {
        if (useCardSelectionStore.getState().result?.context?.purpose === EXPEDITION_PURPOSE) return "expeditions";
        try {
            return (sessionStorage.getItem("activities-tab") as Tab | null) ?? "expeditions";
        } catch {
            return "expeditions";
        }
    });
    const selectTab = (t: Tab) => {
        setTab(t);
        try { sessionStorage.setItem("activities-tab", t); } catch { /* stockage indisponible */ }
    };

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate("/")}>
                    Retour
                </button>
                <h1 className="text-white font-bold">Activités</h1>
                <span className="w-14" />
            </header>

            <div className="flex border-b border-white/5">
                {TABS.map((t) => (
                    <button
                        key={t.key}
                        className={`flex-1 py-2.5 text-sm font-semibold transition-colors ${
                            tab === t.key ? "text-accent border-b-2 border-accent" : "text-white/40 hover:text-white/70"
                        }`}
                        onClick={() => selectTab(t.key)}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            <main className="flex-1 px-4 py-6 max-w-sm mx-auto w-full">
                {tab === "expeditions" && <ExpeditionsTab />}
                {tab === "workshop" && <WorkshopTab />}
            </main>

            <BottomNav />
        </div>
    );
}

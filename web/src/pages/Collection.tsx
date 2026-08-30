import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCollection } from "@/hooks/useCollection";
import type { CollectionParams } from "@/api/collection";
import CardGrid from "@/components/card/CardGrid";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

const SORT_OPTIONS = [
    { value: "rarity", label: "Rareté" },
    { value: "name", label: "Nom" },
    { value: "quality", label: "Qualité" },
    { value: "specialty", label: "Spécialité" },
    { value: "jewelry", label: "Bijou" },
    { value: "probability", label: "Rareté réelle" },
];

export default function Collection() {
    const navigate = useNavigate();
    const [filters, setFilters] = useState<CollectionParams>({ sort_by: "rarity" });
    const [reversed, setReversed] = useState(false);
    const [search, setSearch] = useState("");

    const { data, isLoading } = useCollection(filters);

    // Recherche + sens de tri appliqués côté client sur la liste déjà triée par l'API.
    const groups = useMemo(() => {
        let g = data?.groups ?? [];
        const q = search.trim().toLowerCase();
        if (q) {
            g = g.filter((x) => x.card.character_name.toLowerCase().includes(q));
        }
        if (reversed) g = [...g].reverse();
        return g;
    }, [data, search, reversed]);

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            {/* Header */}
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button
                    className="text-accent text-sm font-semibold"
                    onClick={() => navigate("/")}
                >
                    ← Retour
                </button>
                <h1 className="text-white font-bold">📚 Collection</h1>
                <div className="text-white/40 text-xs text-right">
                    {data ? (
                        <>
                            <p>{data.unique_cards} uniques</p>
                            <p>{data.total_cards} total</p>
                        </>
                    ) : (
                        <p>...</p>
                    )}
                </div>
            </header>

            {/* Recherche */}
            <div className="px-4 pt-3">
                <input
                    type="search"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Rechercher un personnage..."
                    className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-2 text-sm
                     text-white placeholder-white/30 focus:border-accent focus:outline-none transition-colors"
                />
            </div>

            {/* Tri + sens */}
            <div className="px-4 py-3 flex items-center gap-2 overflow-x-auto no-scrollbar">
                {SORT_OPTIONS.map((opt) => (
                    <button
                        key={opt.value}
                        className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-all
              ${filters.sort_by === opt.value
                                ? "bg-accent text-white"
                                : "bg-white/10 text-white/50 hover:bg-white/20"
                            }`}
                        onClick={() => setFilters((f) => ({ ...f, sort_by: opt.value }))}
                    >
                        {opt.label}
                    </button>
                ))}
                <button
                    className="shrink-0 ml-auto w-8 h-8 rounded-full bg-white/10 text-white/70
                     hover:bg-white/20 transition-all flex items-center justify-center"
                    title={reversed ? "Sens inversé" : "Sens normal"}
                    onClick={() => setReversed((r) => !r)}
                >
                    {reversed ? "↑" : "↓"}
                </button>
            </div>

            {/* Cards */}
            <main className="flex-1 overflow-y-auto py-4">
                {isLoading ? (
                    <LoadingSpinner text="Chargement de la collection..." />
                ) : groups.length > 0 ? (
                    <CardGrid groups={groups} />
                ) : (
                    <div className="flex flex-col items-center justify-center h-64 text-white/30">
                        <span className="text-4xl mb-3">{search ? "🔍" : "📭"}</span>
                        <p>
                            {search
                                ? "Aucun personnage ne correspond"
                                : "Aucune carte dans votre collection"}
                        </p>
                        {!search && (
                            <button
                                className="text-accent text-sm mt-2 hover:underline"
                                onClick={() => navigate("/shop")}
                            >
                                Ouvrir des packs →
                            </button>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}

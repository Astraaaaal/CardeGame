import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCollection } from "@/hooks/useCollection";
import type { CollectionParams } from "@/api/collection";
import CardGrid from "@/components/card/CardGrid";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import FilterModal from "@/components/collection/FilterModal";
import ProbabilityModal from "@/components/collection/ProbabilityModal";

const TIER_FILTER_KEYS = [
    "rarity_id", "rarity_op", "quality_id", "quality_op",
    "specialty_id", "specialty_op", "jewelry_id", "jewelry_op",
] as const;

function countActiveFilters(f: CollectionParams): number {
    return ["rarity_id", "quality_id", "specialty_id", "jewelry_id"].filter(
        (k) => !!f[k as keyof CollectionParams]
    ).length;
}

const SORT_OPTIONS = [
    { value: "rarity", label: "Rareté" },
    { value: "name", label: "Nom" },
    { value: "quality", label: "Qualité" },
    { value: "specialty", label: "Spécialité" },
    { value: "jewelry", label: "Bijou" },
    { value: "probability", label: "Rareté réelle" },
    { value: "obtained_at", label: "Date d'obtention" },
    { value: "power", label: "Puissance" },
    { value: "luck", label: "Chance" },
];

export default function Collection() {
    const navigate = useNavigate();
    const [filters, setFilters] = useState<CollectionParams>({ sort_by: "rarity" });
    const [reversed, setReversed] = useState(false);
    const [search, setSearch] = useState("");
    const [filterModalOpen, setFilterModalOpen] = useState(false);
    const [probModalOpen, setProbModalOpen] = useState(false);

    const patchFilters = (patch: Partial<CollectionParams>) =>
        setFilters((f) => ({ ...f, ...patch }));
    const resetTierFilters = () =>
        setFilters((f) => {
            const next = { ...f };
            for (const k of TIER_FILTER_KEYS) delete next[k];
            return next;
        });
    const activeFilterCount = countActiveFilters(filters);

    const { data, isLoading, isFetching } = useCollection(filters);

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
                <div className="flex items-center gap-3">
                    <button
                        className="text-white/50 hover:text-white text-lg"
                        title="Table des probabilités"
                        onClick={() => setProbModalOpen(true)}
                    >
                        📊
                    </button>
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
                    className={`shrink-0 relative px-3 py-1.5 rounded-full text-xs font-semibold transition-all ml-auto
                        ${activeFilterCount > 0 ? "bg-accent text-white" : "bg-white/10 text-white/50 hover:bg-white/20"}`}
                    onClick={() => setFilterModalOpen(true)}
                >
                    🔎 Filtres{activeFilterCount > 0 ? ` (${activeFilterCount})` : ""}
                </button>
                <button
                    className="shrink-0 w-8 h-8 rounded-full bg-white/10 text-white/70
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
                    <div className={isFetching ? "opacity-60 transition-opacity" : "transition-opacity"}>
                        <CardGrid groups={groups} />
                    </div>
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

            <FilterModal
                open={filterModalOpen}
                onClose={() => setFilterModalOpen(false)}
                filters={filters}
                onChange={patchFilters}
                onReset={resetTierFilters}
            />
            <ProbabilityModal open={probModalOpen} onClose={() => setProbModalOpen(false)} />
        </div>
    );
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCollection } from "@/hooks/useCollection";
import type { CollectionParams } from "@/api/collection";
import CardGrid from "@/components/card/CardGrid";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

const SORT_OPTIONS = [
    { value: "rarity", label: "Rareté" },
    { value: "quality", label: "Qualité" },
    { value: "specialty", label: "Spécialité" },
    { value: "jewelry", label: "Bijou" },
    { value: "recent", label: "Récent" },
];

export default function Collection() {
    const navigate = useNavigate();
    const [filters, setFilters] = useState<CollectionParams>({ sort_by: "rarity" });

    const { data, isLoading } = useCollection(filters);

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

            {/* Filters */}
            <div className="px-4 py-3 flex gap-2 overflow-x-auto no-scrollbar">
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
            </div>

            {/* Cards */}
            <main className="flex-1 overflow-y-auto py-4">
                {isLoading ? (
                    <LoadingSpinner text="Chargement de la collection..." />
                ) : data && data.groups.length > 0 ? (
                    <CardGrid groups={data.groups} />
                ) : (
                    <div className="flex flex-col items-center justify-center h-64 text-white/30">
                        <span className="text-4xl mb-3">📭</span>
                        <p>Aucune carte dans votre collection</p>
                        <button
                            className="text-accent text-sm mt-2 hover:underline"
                            onClick={() => navigate("/shop")}
                        >
                            Ouvrir des packs →
                        </button>
                    </div>
                )}
            </main>
        </div>
    );
}

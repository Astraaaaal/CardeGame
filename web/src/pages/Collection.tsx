import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCollection } from "@/hooks/useCollection";
import type { CollectionParams } from "@/api/collection";
import type { Card, CardGroup } from "@/types/card";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import CardGrid from "@/components/card/CardGrid";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import FilterModal from "@/components/collection/FilterModal";
import RecycleTools from "@/components/collection/RecycleTools";
import RecycleConfirmModal from "@/components/collection/RecycleConfirmModal";
import CopySelectModal from "@/components/collection/CopySelectModal";
import { copiesOfGroup, summarize } from "@/utils/recycleSelection";
import ProbabilityModal from "@/components/collection/ProbabilityModal";
import FavoritesManager, { FAVORITES_KEY } from "@/components/collection/FavoritesManager";
import { favoritesApi } from "@/api/favorites";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { collectionApi } from "@/api/collection";
import { useProbabilities } from "@/hooks/useCollection";
import { showRewards } from "@/stores/rewardPopupStore";
import { toast } from "@/stores/toastStore";
import SocialButton from "@/components/layout/SocialButton";
import { useSituationStep } from "@/components/tutorial/useTutorial";
import { SITUATION_STEPS } from "@/components/tutorial/tutorialSteps";

const TIER_FILTER_KEYS = [
    "rarity_id", "rarity_op", "quality_id", "quality_op",
    "specialty_id", "specialty_op", "jewelry_id", "jewelry_op", "type_names",
    "min_power", "max_power",
] as const;

function countActiveFilters(f: CollectionParams): number {
    const tierCount = ["rarity_id", "quality_id", "specialty_id", "jewelry_id"].filter(
        (k) => !!f[k as keyof CollectionParams]
    ).length;
    const powerCount = f.min_power != null || f.max_power != null ? 1 : 0;
    return tierCount + (f.type_names?.length ? 1 : 0) + powerCount;
}

const SORT_OPTIONS = [
    { value: "rarity", label: "Rareté" },
    { value: "name", label: "Nom" },
    { value: "type", label: "Type" },
    { value: "quality", label: "Qualité" },
    { value: "specialty", label: "Spécialité" },
    { value: "jewelry", label: "Bijou" },
    { value: "probability", label: "Rareté réelle" },
    { value: "obtained_at", label: "Date d'obtention" },
    { value: "power", label: "Puissance" },
    { value: "luck", label: "Chance" },
    { value: "favorite", label: "Favoris" },
];

/** Pastille flottante de la collection (outils à gauche, défilement à droite). */
const BUBBLE =
    "pointer-events-auto w-10 h-10 rounded-full bg-game-surface border border-white/15 text-white/80 " +
    "shadow-lg flex items-center justify-center text-lg hover:border-accent hover:text-white transition-colors";

export default function Collection() {
    const navigate = useNavigate();
    const [filters, setFilters] = useState<CollectionParams>({ sort_by: "rarity" });
    const [reversed, setReversed] = useState(false);
    const [search, setSearch] = useState("");
    const [filterModalOpen, setFilterModalOpen] = useState(false);
    const [probModalOpen, setProbModalOpen] = useState(false);
    const [favManagerOpen, setFavManagerOpen] = useState(false);
    // Mode recyclage : sélection d'exemplaires précis à travers toute la collection.
    const [recycleMode, setRecycleMode] = useState(false);
    const [recycleSelected, setRecycleSelected] = useState<Set<string>>(new Set());
    const [includeFavorites, setIncludeFavorites] = useState(false);
    const [copiesGroup, setCopiesGroup] = useState<CardGroup | null>(null);
    const [confirmOpen, setConfirmOpen] = useState(false);
    const { data: favCats } = useQuery({ queryKey: FAVORITES_KEY, queryFn: favoritesApi.list });
    const scrollRef = useRef<HTMLElement>(null);
    // Empêche un double-tap/double-clic sur "Valider" de déclencher deux
    // resolveSelection()/navigate() (ex: double-appel de confirmSelection).
    const confirmedRef = useRef(false);

    const selectionRequest = useCardSelectionStore((s) => s.request);
    const resolveSelection = useCardSelectionStore((s) => s.resolveSelection);
    const cancelSelection = useCardSelectionStore((s) => s.cancelSelection);
    const [picked, setPicked] = useState<Map<string, Card>>(new Map());

    const inSelectionMode = !!selectionRequest;

    const toggleSelection = (cardId: string, preview: Card) => {
        setPicked((prev) => {
            const next = new Map(prev);
            if (next.has(cardId)) {
                next.delete(cardId);
                return next;
            }
            if (selectionRequest && next.size >= selectionRequest.max) {
                if (selectionRequest.max === 1) {
                    next.clear();
                } else {
                    return prev;
                }
            }
            next.set(cardId, preview);
            return next;
        });
    };

    const confirmSelection = () => {
        if (confirmedRef.current) return;
        confirmedRef.current = true;
        resolveSelection(Array.from(picked, ([id, preview]) => ({ id, preview })));
        const to = selectionRequest?.returnTo ?? "/";
        setPicked(new Map());
        navigate(to);
    };

    const cancelAndLeave = () => {
        cancelSelection();
        const to = selectionRequest?.returnTo ?? "/";
        setPicked(new Map());
        navigate(to);
    };

    const addToSelection = (ids: string[]) =>
        setRecycleSelected((prev) => new Set([...prev, ...ids]));

    const toggleCopy = (id: string) =>
        setRecycleSelected((prev) => {
            const next = new Set(prev);
            if (!next.delete(id)) next.add(id);
            return next;
        });

    /** Appui sur une carte : prend (ou rend) tous ses exemplaires non verrouillés.
     *  Un favori se laisse prendre ainsi — c'est un geste volontaire, contrairement
     *  aux outils de sélection rapide qui l'épargnent. */
    const toggleGroup = (group: CardGroup) => {
        const ids = copiesOfGroup(group).map((c) => c.id);
        if (!ids.length) {
            toast.error("Exemplaires verrouillés : retire le verrou pour les recycler.");
            return;
        }
        setRecycleSelected((prev) => {
            const next = new Set(prev);
            const allPicked = ids.every((id) => next.has(id));
            for (const id of ids) {
                if (allPicked) next.delete(id);
                else next.add(id);
            }
            return next;
        });
    };

    const leaveRecycleMode = () => {
        setRecycleMode(false);
        setRecycleSelected(new Set());
        setConfirmOpen(false);
        setCopiesGroup(null);
    };

    // Selon la hauteur du contenu, c'est la fenêtre ou <main> qui défile : on pilote les deux.
    const scrollPage = (to: "top" | "bottom") => {
        const main = scrollRef.current;
        window.scrollTo({ top: to === "top" ? 0 : document.documentElement.scrollHeight, behavior: "smooth" });
        main?.scrollTo({ top: to === "top" ? 0 : main.scrollHeight, behavior: "smooth" });
    };

    const patchFilters = (patch: Partial<CollectionParams>) =>
        setFilters((f) => ({ ...f, ...patch }));
    const resetTierFilters = () =>
        setFilters((f) => {
            const next = { ...f };
            for (const k of TIER_FILTER_KEYS) delete next[k];
            return next;
        });
    const activeFilterCount = countActiveFilters(filters);

    const { data, isLoading, isFetching } = useCollection(
        recycleMode ? { ...filters, with_copies: true } : filters,
    );

    // Recherche + sens de tri appliqués côté client sur la liste déjà triée par l'API.
    // Le premier doublon est le moment où le recyclage devient une question.
    useSituationStep(SITUATION_STEPS.premierDoublon, (data?.groups ?? []).some((g) => g.quantity > 1));
    // Le verrou ne s'explique bien qu'au moment où on s'apprête à recycler.
    useSituationStep(SITUATION_STEPS.carteRare, recycleMode);

    const groups = useMemo(() => {
        let g = data?.groups ?? [];
        const q = search.trim().toLowerCase();
        if (q) {
            g = g.filter((x) => x.card.character_name.toLowerCase().includes(q));
        }
        if (reversed) g = [...g].reverse();
        return g;
    }, [data, search, reversed]);

    const qc = useQueryClient();
    const { data: probabilities } = useProbabilities(recycleMode);
    const recycleIds = useMemo(() => Array.from(recycleSelected), [recycleSelected]);
    // « Rareté élevée » = les deux meilleurs paliers du référentiel (épique et
    // légendaire aujourd'hui) : ils déclenchent l'avertissement de confirmation.
    const preciousRarityIds = (probabilities?.rarities ?? []).slice(0, 2).map((r) => r.id);
    const summary = useMemo(
        () => summarize(groups, recycleSelected, preciousRarityIds),
        [groups, recycleSelected, preciousRarityIds],
    );

    const recycle = useMutation({
        mutationFn: () => collectionApi.recycle({ card_ids: recycleIds }),
        onSuccess: (res) => {
            showRewards({
                title: `Recyclage ×${res.recycled_count}`,
                items: res.gains.map((g) => ({
                    kind: "resource" as const, resourceId: g.resource_id, amount: g.amount, name: g.name,
                })),
            });
            leaveRecycleMode();
            qc.invalidateQueries({ queryKey: ["collection"] });
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["card-copies"] });
        },
        onError: () => {
            toast.error("Recyclage impossible : recharge la collection et réessaie.");
            setConfirmOpen(false);
        },
    });

    return (
        <div className="min-h-screen bg-game-bg flex flex-col relative pb-14 desktop:pb-0">
            {/* Header */}
            <header className="relative flex items-center justify-between pl-4 pr-14 py-3 bg-game-surface/50 border-b border-white/5">
                <button
                    className="text-accent text-sm font-semibold"
                    onClick={() => inSelectionMode ? cancelAndLeave() : recycleMode ? leaveRecycleMode() : navigate("/")}
                >
                    {inSelectionMode || recycleMode ? "× Annuler" : "Retour"}
                </button>
                <h1 className="absolute left-1/2 -translate-x-1/2 max-w-[55%] truncate text-white font-bold pointer-events-none">
                    {inSelectionMode ? selectionRequest!.title : recycleMode ? "Recyclage" : "Collection"}
                </h1>
                {/* À droite, seulement ce qui appartient au mode en cours. Le
                    décompte de la collection vit dans les statistiques du profil,
                    et les outils sont passés en pastilles flottantes : le titre
                    peut enfin tenir au centre. */}
                <div className="w-14 text-white/40 text-xs text-right">
                    {inSelectionMode ? (
                        <p>{picked.size} / {selectionRequest!.max}</p>
                    ) : recycleMode ? (
                        <p>{recycleSelected.size} choisi{recycleSelected.size > 1 ? "s" : ""}</p>
                    ) : null}
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

            {inSelectionMode && (
                <p className="px-4 pt-2 text-white/40 text-[11px]">Toucher pour choisir · appui long pour voir le détail</p>
            )}

            {recycleMode && (
                <>
                    <p className="px-4 pt-2 text-white/40 text-[11px]">
                        Toucher une carte pour prendre tous ses exemplaires · appui long pour en choisir certains
                    </p>
                    <RecycleTools
                        groups={groups}
                        includeFavorites={includeFavorites}
                        onIncludeFavorites={setIncludeFavorites}
                        onSelect={addToSelection}
                        onClear={() => setRecycleSelected(new Set())}
                    />
                </>
            )}

            {/* Favoris : filtre par catégorie + gestion */}
            <div className="px-4 pt-3 flex items-center gap-2 overflow-x-auto no-scrollbar fade-right">
                <span className="shrink-0 text-white/40 text-xs">★</span>
                {[{ id: undefined as number | undefined, name: "Toutes", color: "" }, ...(favCats ?? [])].map((c) => (
                    <button key={c.id ?? "all"}
                        className={`shrink-0 flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                            filters.favorite_id === c.id ? "bg-accent text-white" : "bg-white/10 text-white/50 hover:bg-white/20"}`}
                        onClick={() => setFilters((f) => ({ ...f, favorite_id: c.id }))}>
                        {c.color && <span className="w-2.5 h-2.5 rounded-full" style={{ background: c.color }} />}
                        {c.name}
                    </button>
                ))}
                <button className="shrink-0 px-2.5 py-1 rounded-full text-xs bg-white/10 text-white/60 hover:bg-white/20"
                    onClick={() => setFavManagerOpen(true)}>
                    {favCats?.length ? "Gérer" : "+ Créer des favoris"}
                </button>
            </div>

            {/* Tri + sens */}
            <div className="px-4 py-3 flex items-center gap-2 overflow-x-auto no-scrollbar fade-right">
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
                    Filtres{activeFilterCount > 0 ? ` (${activeFilterCount})` : ""}
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
            <main
                ref={scrollRef}
                className={`flex-1 overflow-y-auto py-4 ${inSelectionMode || recycleMode ? "pb-24" : ""}`}
            >
                {isLoading ? (
                    <LoadingSpinner text="Chargement de la collection..." />
                ) : groups.length > 0 ? (
                    <div className={isFetching ? "opacity-60 transition-opacity" : "transition-opacity"}>
                        <CardGrid
                            groups={groups}
                            selectionMode={inSelectionMode}
                            excludeIds={selectionRequest ? new Set(selectionRequest.excludeIds) : undefined}
                            selectedIds={inSelectionMode ? new Set(picked.keys()) : undefined}
                            onToggle={toggleSelection}
                            recycleMode={recycleMode}
                            recycleSelected={recycleSelected}
                            onRecycleToggleGroup={toggleGroup}
                            onRecycleOpenCopies={setCopiesGroup}
                        />
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center h-64 text-white/30">
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
                                Ouvrir des packs
                            </button>
                        )}
                    </div>
                )}
            </main>

            {!inSelectionMode && <SocialButton />}

            {/* Une seule rangée flottante : outils à gauche, bouton de validation
                au centre, flèches de défilement à droite. Le bouton vivait
                auparavant collé en bas de l'écran, donc SOUS la barre d'onglets,
                et sur toute la largeur, donc par-dessus les pastilles. */}
            <div className="floating-bottom-row fixed inset-x-0 z-30 pointer-events-none">
                <div className="max-w-mobile mx-auto px-4 flex items-end justify-between gap-3">
                    {/* Outils de la collection, en miroir des flèches de défilement. */}
                    <div className="flex flex-col items-start gap-2">
                        {!inSelectionMode && !recycleMode && (
                            <>
                                <button
                                    className={BUBBLE}
                                    title="Recycler plusieurs cartes"
                                    aria-label="Recycler plusieurs cartes"
                                    onClick={() => setRecycleMode(true)}
                                >
                                    ♻️
                                </button>
                                <button
                                    className={BUBBLE}
                                    title="Table des probabilités"
                                    aria-label="Table des probabilités"
                                    onClick={() => setProbModalOpen(true)}
                                >
                                    📊
                                </button>
                            </>
                        )}
                    </div>

                    {(inSelectionMode || recycleMode) && (
                        <div className="flex-1 min-w-0 pb-1 [&>*]:pointer-events-auto">
                            {inSelectionMode ? (
                                <Button
                                    variant="gold"
                                    className="w-full"
                                    disabled={picked.size === 0}
                                    onClick={confirmSelection}
                                >
                                    Valider ({picked.size})
                                </Button>
                            ) : (
                                <Button
                                    variant="danger"
                                    className="w-full"
                                    disabled={recycleSelected.size === 0}
                                    onClick={() => setConfirmOpen(true)}
                                >
                                    Recycler ({recycleSelected.size})
                                </Button>
                            )}
                        </div>
                    )}

                    <div className="flex flex-col items-end gap-2">
                        {([["top", "↑", "Tout en haut"], ["bottom", "↓", "Tout en bas"]] as const).map(([to, icon, label]) => (
                            <button
                                key={to}
                                className={BUBBLE}
                                title={label}
                                aria-label={label}
                                onClick={() => scrollPage(to)}
                            >
                                {icon}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            <FilterModal
                open={filterModalOpen}
                onClose={() => setFilterModalOpen(false)}
                filters={filters}
                onChange={patchFilters}
                onReset={resetTierFilters}
            />
            {copiesGroup && (
                <CopySelectModal
                    group={copiesGroup}
                    selectedIds={recycleSelected}
                    onToggle={toggleCopy}
                    onClose={() => setCopiesGroup(null)}
                />
            )}
            {confirmOpen && (
                <RecycleConfirmModal
                    cardIds={recycleIds}
                    summary={summary}
                    pending={recycle.isPending}
                    onConfirm={() => recycle.mutate()}
                    onClose={() => setConfirmOpen(false)}
                />
            )}
            <ProbabilityModal open={probModalOpen} onClose={() => setProbModalOpen(false)} />
            <FavoritesManager open={favManagerOpen} onClose={() => setFavManagerOpen(false)} />
        </div>
    );
}

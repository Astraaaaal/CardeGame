import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useGameStore } from "@/stores/gameStore";
import CardReveal from "@/components/card/CardReveal";
import CardImage from "@/components/card/CardImage";
import Button from "@/components/ui/Button";

export default function PackOpening() {
  const navigate = useNavigate();
  const {
    currentPacks,
    currentPackIndex,
    currentCardIndex,
    isRevealing,
    nextCard,
    nextPack,
    skipToEnd,
    resetPackState,
  } = useGameStore();

  // Quitter l'écran : on navigue, puis on purge l'état d'ouverture (macrotask,
  // pour ne pas re-rendre ce composant pendant la transition).
  const leave = (to: string) => {
    navigate(to);
    setTimeout(resetPackState, 0);
  };

  const hasPacks = !!currentPacks && currentPacks.length > 0;

  // Accès direct à /opening sans rien à ouvrir → écran de repli (pas de
  // redirection automatique : ça créait une course avec la navigation de sortie).
  if (!hasPacks) {
    return (
      <div className="min-h-screen bg-game-bg flex flex-col items-center justify-center gap-4 px-4">
        <p className="text-white/50">Aucun pack à ouvrir.</p>
        <Button variant="primary" onClick={() => navigate("/shop")}>
          Aller à la boutique
        </Button>
      </div>
    );
  }

  const packs = currentPacks!;
  const pack = packs[currentPackIndex];
  const card = pack?.[currentCardIndex];
  const totalCards = packs.reduce((s, p) => s + p.length, 0);
  const revealedSoFar =
    packs.slice(0, currentPackIndex).reduce((s, p) => s + p.length, 0) +
    currentCardIndex +
    1;

  const handleNext = () => {
    if (!nextCard()) nextPack();
  };

  // Résumé final (après « Tout révéler » ou fin naturelle)
  if (!isRevealing) {
    const allCards = packs.flat();

    return (
      <div className="min-h-screen bg-game-bg flex flex-col items-center justify-center px-4 py-8">
        <motion.div
          className="w-full max-w-sm text-center"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <h2 className="text-2xl font-bold text-white mb-6">
            🎉 {allCards.length} cartes obtenues !
          </h2>

          <div className="grid grid-cols-3 gap-3 mb-6">
            {allCards.map((c, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.03 }}
              >
                <CardImage card={c} size="sm" />
              </motion.div>
            ))}
          </div>

          <div className="space-y-2">
            <Button
              variant="primary"
              size="lg"
              className="w-full"
              onClick={() => leave("/collection")}
            >
              Voir ma collection
            </Button>
            <Button
              variant="secondary"
              size="md"
              className="w-full"
              onClick={() => leave("/shop")}
            >
              Retour à la boutique
            </Button>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-game-bg flex flex-col">
      {/* Progress */}
      <header className="flex items-center justify-between px-4 py-3">
        <p className="text-white/50 text-sm">
          Pack {currentPackIndex + 1}/{packs.length}
        </p>
        <p className="text-white/50 text-sm">
          {revealedSoFar}/{totalCards}
        </p>
        <button className="text-accent text-sm font-semibold" onClick={skipToEnd}>
          Tout révéler
        </button>
      </header>

      {/* Card reveal */}
      <main className="flex-1 flex items-center justify-center px-4">
        {card && <CardReveal card={card} onNext={handleNext} />}
      </main>
    </div>
  );
}

import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useGameStore } from "@/stores/gameStore";
import CardReveal from "@/components/card/CardReveal";
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

  // Rien à ouvrir → retour boutique
  if (!currentPacks || currentPacks.length === 0) {
    navigate("/shop");
    return null;
  }

  const pack = currentPacks[currentPackIndex];
  const card = pack?.[currentCardIndex];
  const totalCards = currentPacks.reduce((s, p) => s + p.length, 0);
  const revealedSoFar =
    currentPacks.slice(0, currentPackIndex).reduce((s, p) => s + p.length, 0) +
    currentCardIndex +
    1;

  const handleNext = () => {
    if (!nextCard()) {
      // Plus de cartes dans ce pack
      if (!nextPack()) {
        // Plus de packs
        // isRevealing sera mis à false par nextPack
      }
    }
  };

  const handleFinish = () => {
    resetPackState();
    navigate("/shop");
  };

  // Résumé final (après skip ou fin naturelle)
  if (!isRevealing) {
    const allCards = currentPacks.flat();

    return (
      <div className="min-h-screen bg-game-bg flex flex-col items-center justify-center px-4">
        <motion.div
          className="w-full max-w-sm text-center"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <h2 className="text-2xl font-bold text-white mb-6">
            🎉 {allCards.length} cartes obtenues !
          </h2>

          <div className="grid grid-cols-4 gap-2 mb-6">
            {allCards.map((c, i) => (
              <motion.div
                key={i}
                className="aspect-[9/16] rounded-lg overflow-hidden border border-white/10"
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.03 }}
              >
                {c.rendered_url ? (
                  <img
                    src={c.rendered_url}
                    alt={c.character_name}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div
                    className="w-full h-full flex items-center justify-center text-[8px] text-white/40"
                    style={{
                      backgroundColor: `rgb(${c.rarity_color.join(",")})20`,
                    }}
                  >
                    {c.character_name}
                  </div>
                )}
              </motion.div>
            ))}
          </div>

          <div className="space-y-2">
            <Button variant="primary" size="lg" className="w-full" onClick={handleFinish}>
              Retour à la boutique
            </Button>
            <Button
              variant="secondary"
              size="md"
              className="w-full"
              onClick={() => { resetPackState(); navigate("/collection"); }}
            >
              Voir ma collection
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
          Pack {currentPackIndex + 1}/{currentPacks.length}
        </p>
        <p className="text-white/50 text-sm">
          {revealedSoFar}/{totalCards}
        </p>
        <button
          className="text-accent text-sm font-semibold"
          onClick={skipToEnd}
        >
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

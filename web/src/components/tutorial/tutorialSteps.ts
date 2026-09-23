import type { FeatureKey } from "@/hooks/useUnlocks";
import type { TutorialStep } from "@/stores/tutorialStore";

/**
 * Ce que le tutoriel explique, et quand.
 *
 * Règle de découpage : à la première connexion, le strict minimum pour ne pas
 * être perdu ; tout le reste attend le moment où la fonctionnalité s'ouvre.
 * Expliquer les expéditions à quelqu'un qui n'a pas encore ouvert un booster,
 * c'est parler dans le vide.
 */

/** Première connexion : cinq bulles, pas une de plus. */
export const WELCOME_STEPS: TutorialStep[] = [
    {
        id: "welcome-but",
        title: "Le but",
        text: "Tu collectionnes des cartes. Chaque carte a une puissance ; la somme de toutes tes cartes fait ton niveau.",
    },
    {
        id: "welcome-booster",
        title: "Ton premier booster",
        text: "Ouvre ton booster : cinq cartes, avec une rareté, une qualité, une spécialité et un bijou tirés au sort.",
    },
    {
        id: "welcome-pieces",
        title: "Les pièces",
        text: "Les pièces s'obtiennent en jouant. Elles servent à acheter des boosters à la boutique.",
    },
    {
        id: "welcome-niveau",
        title: "Le niveau ouvre le jeu",
        text: "Tout n'est pas disponible tout de suite. Plus ta collection gagne en puissance, plus le jeu s'ouvre.",
    },
    {
        id: "welcome-quotidien",
        title: "Reviens demain",
        text: "Une récompense t'attend chaque jour, et elle grossit tant que tu ne manques pas un jour.",
    },
];

/** Une bulle par fonctionnalité, dite le jour où elle s'ouvre. */
export const UNLOCK_STEPS: Partial<Record<FeatureKey, Omit<TutorialStep, "id">>> = {
    presence_luck: {
        title: "Chance de présence",
        text: "Rester sur l'appli augmente peu à peu tes gains, jusqu'à ×2,5 après 5 h.",
    },
    resource_shop: {
        title: "Boutique Ressources",
        text: "Tes ressources s'échangent ici contre des boosters et des bonus.",
    },
    workshop: {
        title: "Atelier",
        text: "Transforme tes ressources en cartes et en améliorations.",
    },
    wheel: {
        title: "Roue de la fortune",
        text: "Un tour gratuit par jour ; les suivants coûtent des pièces.",
    },
    higher_lower: {
        title: "Plus ou moins",
        text: "Mise des pièces ou de la poussière. Encaisse dès la manche 3 : une erreur fait tout perdre.",
    },
    expeditions: {
        title: "Expéditions",
        text: "Envoie une équipe de cartes en mission ; elles reviennent avec du butin après un temps choisi.",
    },
    absence_chest: {
        title: "Coffre d'absence",
        text: "Ce que le jeu t'a mis de côté pendant que tu n'étais pas là.",
    },
    leaderboard: {
        title: "Classement",
        text: "Ton rang général, calculé sur la puissance de ta collection.",
    },
    rerolls: {
        title: "Rerolls",
        text: "Relance un axe d'une carte (rareté, qualité, puissance…) pour tenter mieux.",
    },
    machine: {
        title: "Machine d'amélioration",
        text: "Améliore les chances des relances sur les axes que tu choisis.",
    },
    converter: {
        title: "Convertisseur",
        text: "Échange une ressource contre une autre.",
    },
    gifts: {
        title: "Cadeaux",
        text: "Envoie une carte ou des ressources à un ami. Une taxe s'applique à la réception.",
    },
    trades: {
        title: "Échanges",
        text: "Propose un échange carte contre carte. Les deux doivent accepter.",
    },
    showcase: {
        title: "Ta vitrine",
        text: "Ton profil est une vitrine : choisis trois cartes à exposer. Les autres joueurs les voient.",
    },
    listings: {
        title: "Annonces « à échanger »",
        text: "Affiche les cartes que tu cherches à échanger : les autres viennent à toi au lieu que tu ailles les chercher.",
    },
    guild_join: {
        title: "Guildes",
        text: "À plusieurs, vos contributions ouvrent des bonus pour tout le monde.",
    },
    guild_create: {
        title: "Fonder une guilde",
        text: "Crée la tienne, choisis son tag et sa couleur.",
    },
};

export const unlockStep = (key: FeatureKey): TutorialStep | null => {
    const step = UNLOCK_STEPS[key];
    return step ? { id: `unlock-${key}`, ...step } : null;
};

/** Déclenchées par la situation, pas par le niveau. */
export const SITUATION_STEPS = {
    premierDoublon: {
        id: "situation-doublon",
        title: "Un doublon",
        text: "Tu as deux fois la même carte. Le recyclage la transforme en ressources — le bouton ♻️ de la collection en traite plusieurs d'un coup.",
    },
    carteRare: {
        id: "situation-verrou",
        title: "Une belle carte",
        text: "Verrouille tes cartes précieuses : une carte verrouillée ne part jamais au recyclage, même par erreur.",
    },
    defiMensuel: {
        id: "situation-mensuel",
        title: "Le défi du mois",
        text: "Le défi mensuel repart à zéro chaque mois. Les premiers gagnent un titre affiché sur leur profil.",
    },
    puissance: {
        id: "situation-puissance",
        title: "D'où vient ta puissance",
        text: "La puissance d'une carte dépend de sa rareté, de sa qualité, de sa spécialité et de son bijou. Additionne toutes tes cartes et tu obtiens la puissance qui fait ton niveau.",
    },
} satisfies Record<string, TutorialStep>;

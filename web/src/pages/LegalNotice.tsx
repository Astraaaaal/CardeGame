import { useNavigate } from "react-router-dom";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="bg-game-surface rounded-2xl border border-white/10 p-4 space-y-2">
            <h2 className="text-white font-bold text-sm">{title}</h2>
            <div className="text-white/60 text-xs leading-relaxed space-y-1.5">{children}</div>
        </div>
    );
}

// Reste à compléter : le médiateur de la consommation, le jour où la boutique
// premium ouvre au public.
const CONTACT_EMAIL = "contact@a2n.site";

export default function LegalNotice() {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate(-1)}>
                    Retour
                </button>
                <h1 className="text-white font-bold">Mentions légales</h1>
                <span className="w-14" />
            </header>

            <main className="flex-1 px-4 py-6 max-w-sm mx-auto w-full space-y-4">
                <Section title="Éditeur du site">
                    <p>CardeGame est édité sous le nom A2N par Swann Patissier, particulier.</p>
                    <p>Adresse : 11 rue de l'Indre, 44100 Nantes, France.</p>
                    <p>Contact : {CONTACT_EMAIL}</p>
                </Section>

                <Section title="Directeur de publication">
                    <p>Swann Patissier.</p>
                </Section>

                <Section title="Hébergement">
                    <p>
                        Application (site et serveur de jeu) : Render Services, Inc.,
                        525 Brannan Street, Suite 300, San Francisco, CA 94107, États-Unis.
                    </p>
                    <p>
                        Base de données : Neon Inc., 2261 Market Street, Suite 22601,
                        San Francisco, CA 94114, États-Unis.
                    </p>
                </Section>

                <Section title="Propriété intellectuelle">
                    <p>
                        L'ensemble des contenus de CardeGame (textes, images, éléments graphiques,
                        logo) est protégé. Toute reproduction sans autorisation est interdite.
                    </p>
                </Section>

                <Section title="Données personnelles">
                    <p>
                        CardeGame collecte un pseudo, une adresse e-mail, un mot de passe (chiffré)
                        et les données de jeu nécessaires au fonctionnement du service (collection,
                        échanges, messages). Aucune donnée n'est vendue à des tiers.
                    </p>
                    <p>
                        L'adresse e-mail sert à confirmer le compte, à récupérer le mot de passe et,
                        uniquement si tu l'as accepté, à recevoir la newsletter (désinscription à tout
                        moment depuis les réglages ou le lien présent dans chaque e-mail). Les e-mails
                        sont envoyés via Brevo (Sendinblue SAS, France).
                    </p>
                    <p>
                        Les paiements sont traités par Stripe : CardeGame ne reçoit ni ne stocke tes
                        coordonnées bancaires. L'historique des commandes est conservé pour les
                        obligations comptables, même après suppression du compte.
                    </p>
                    <p>
                        Conformément au RGPD, tu peux supprimer ton compte et l'ensemble de tes
                        données à tout moment depuis l'onglet Paramètres de ton profil, ou en écrivant
                        à {CONTACT_EMAIL}. Tu disposes également d'un droit d'accès, de rectification
                        et d'opposition, et peux saisir la CNIL en cas de désaccord.
                    </p>
                </Section>

                <Section title="Conditions de vente (boutique premium)">
                    <p>
                        Vendeur : Swann Patissier, particulier, 11 rue de l'Indre, 44100 Nantes,
                        France — {CONTACT_EMAIL}. TVA non applicable, article 293 B du Code général
                        des impôts.
                    </p>
                    <p>
                        Produits : contenus numériques (monnaie virtuelle « Éclats », lots, éléments
                        cosmétiques), sans valeur monétaire hors du jeu et non convertibles en argent.
                        Les Éclats sont liés au compte et ne s'échangent pas entre joueurs.
                    </p>
                    <p>
                        Prix : indiqués en euros toutes taxes comprises avant l'achat. Le paiement est
                        traité par Stripe ; un reçu est envoyé par e-mail.
                    </p>
                    <p>
                        Livraison : immédiate après confirmation du paiement. En validant l'achat, tu
                        demandes l'exécution immédiate du contrat et renonces à ton droit de
                        rétractation (article L221-28 du Code de la consommation).
                    </p>
                    <p>
                        Remboursements : le contenu étant livré immédiatement, les achats ne sont pas
                        remboursables. En cas de problème technique ayant empêché la livraison, écris à
                        {" "}{CONTACT_EMAIL} : le contenu sera crédité, ou remboursé à titre commercial.
                    </p>
                    <p>
                        Âge : les achats sont réservés aux personnes de 15 ans ou plus. En dessous,
                        l'accord d'un parent ou du représentant légal est nécessaire.
                    </p>
                    <p>
                        Médiation de la consommation : le service de médiation compétent sera indiqué
                        ici à l'ouverture de la boutique au public. En attendant, toute réclamation
                        peut être adressée à {CONTACT_EMAIL}.
                    </p>
                    <p>
                        Droit applicable : droit français. En cas de litige, une solution amiable sera
                        recherchée avant toute action judiciaire.
                    </p>
                </Section>

                <Section title="Cookies">
                    <p>
                        CardeGame utilise uniquement le stockage local nécessaire au
                        fonctionnement du service (session de connexion). Aucun cookie publicitaire
                        ou de tracking tiers n'est utilisé.
                    </p>
                </Section>

                <Section title="Contact">
                    <p>Pour toute question, signalement de bug ou demande : {CONTACT_EMAIL}</p>
                </Section>
            </main>
        </div>
    );
}

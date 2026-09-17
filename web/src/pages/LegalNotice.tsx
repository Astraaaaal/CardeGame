import { useNavigate } from "react-router-dom";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="bg-game-surface rounded-2xl border border-white/10 p-4 space-y-2">
            <h2 className="text-white font-bold text-sm">{title}</h2>
            <div className="text-white/60 text-xs leading-relaxed space-y-1.5">{children}</div>
        </div>
    );
}

const PLACEHOLDER = "[À COMPLÉTER]";

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
                    <p>Nom / raison sociale : {PLACEHOLDER}</p>
                    <p>Statut : {PLACEHOLDER} (particulier, auto-entrepreneur...)</p>
                    <p>Adresse : {PLACEHOLDER}</p>
                    <p>Contact : {PLACEHOLDER}</p>
                </Section>

                <Section title="Directeur de publication">
                    <p>{PLACEHOLDER}</p>
                </Section>

                <Section title="Hébergement">
                    <p>Application (frontend + backend) : Render, Inc.</p>
                    <p>Base de données : Neon (Neon, Inc.)</p>
                    <p>Adresse de l'hébergeur : {PLACEHOLDER}</p>
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
                        données à tout moment depuis l'onglet Paramètres de ton profil.
                    </p>
                    <p>Pour toute question relative à tes données : {PLACEHOLDER}</p>
                </Section>

                <Section title="Conditions de vente (boutique premium)">
                    <p>Vendeur : {PLACEHOLDER} (nom, statut, SIRET, adresse).</p>
                    <p>
                        Produits : contenus numériques (monnaie virtuelle « Éclats », lots, éléments
                        cosmétiques), sans valeur monétaire hors du jeu, non échangeables entre
                        joueurs et non convertibles en argent.
                    </p>
                    <p>Prix : indiqués en euros TTC avant l'achat. TVA : {PLACEHOLDER}.</p>
                    <p>
                        Livraison : immédiate après confirmation du paiement. En validant l'achat, tu
                        demandes l'exécution immédiate du contrat et renonces à ton droit de
                        rétractation (article L221-28 du Code de la consommation).
                    </p>
                    <p>Remboursements et réclamations : {PLACEHOLDER}.</p>
                    <p>Mineurs : {PLACEHOLDER} (accord parental requis).</p>
                    <p>Médiateur de la consommation : {PLACEHOLDER}.</p>
                </Section>

                <Section title="Cookies">
                    <p>
                        CardeGame utilise uniquement le stockage local nécessaire au
                        fonctionnement du service (session de connexion). Aucun cookie publicitaire
                        ou de tracking tiers n'est utilisé.
                    </p>
                </Section>

                <Section title="Contact">
                    <p>Pour toute question, signalement de bug ou demande : {PLACEHOLDER}</p>
                </Section>
            </main>
        </div>
    );
}

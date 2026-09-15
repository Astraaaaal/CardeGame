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
                        CardeGame collecte un pseudo, un mot de passe (chiffré) et les données de
                        jeu nécessaires au fonctionnement du service (collection, échanges,
                        messages). Aucune donnée n'est cédée à des tiers.
                    </p>
                    <p>
                        Conformément au RGPD, tu peux supprimer ton compte et l'ensemble de tes
                        données à tout moment depuis l'onglet Paramètres de ton profil.
                    </p>
                    <p>Pour toute question relative à tes données : {PLACEHOLDER}</p>
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

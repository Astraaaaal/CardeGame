import { unlockAudio } from "@/utils/sound";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { toast } from "@/stores/toastStore";
import { errMsg } from "@/utils/errors";
import App from "./App";
import "./styles/globals.css";
import "./styles/card.css";

// Ancien cache des données API du service worker (retiré) : on le vide sur
// les appareils où il existe encore, pour ne plus rien resservir de périmé.
if ("caches" in window) {
    caches.delete("api-data").catch(() => {});
}

const queryClient = new QueryClient({
    // Filet global : toute action qui échoue affiche son erreur dans le bandeau
    // (sauf l'admin et les formulaires de connexion, qui gardent leurs messages).
    mutationCache: new MutationCache({
        onError: (error, _vars, _ctx, mutation) => {
            if (mutation.meta?.silentError || window.location.pathname.startsWith("/admin")) return;
            toast.error(errMsg(error));
        },
    }),
    defaultOptions: {
        queries: {
            retry: 1,
            refetchOnWindowFocus: false,
        },
    },
});

// Les navigateurs n'autorisent le son qu'après une interaction : on débloque
// le contexte audio (et la musique) au premier clic ou à la première touche.
for (const event of ["pointerdown", "keydown"]) {
    window.addEventListener(event, () => unlockAudio(), { once: true });
}

// Nouvelle version déployée : le service worker s'installe et prend la main
// (skipWaiting + clientsClaim), mais la page déjà ouverte continue d'afficher
// l'ancien code jusqu'à un rechargement. On le fait donc nous-mêmes, une seule
// fois — sans ça, un joueur reste sur l'interface précédente sans le savoir.
// Première installation (aucun service worker avant) : rien à recharger.
if ("serviceWorker" in navigator && navigator.serviceWorker.controller) {
    let reloading = false;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
        if (reloading) return;
        reloading = true;
        window.location.reload();
    });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
        <QueryClientProvider client={queryClient}>
            <BrowserRouter
                // v7_startTransition désactivé : navigate() passait alors par
                // React.startTransition, ce qui pouvait faire recommencer le
                // rendu de la page de destination après qu'un effet y ait déjà
                // consommé un état ponctuel (ex: cardSelectionStore pour un
                // cadeau) — le 2e rendu la retrouvait vide et perdait l'état
                // restauré par le 1er (le compositeur de cadeau se rouvrait
                // puis disparaissait aussitôt).
                future={{ v7_startTransition: false, v7_relativeSplatPath: true }}
            >
                <App />
            </BrowserRouter>
        </QueryClientProvider>
    </React.StrictMode>
);

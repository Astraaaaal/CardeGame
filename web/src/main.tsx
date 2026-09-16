import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./styles/globals.css";
import "./styles/card.css";

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: 1,
            refetchOnWindowFocus: false,
        },
    },
});

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

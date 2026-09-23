import { useEffect, useState } from "react";

/**
 * Largeur à partir de laquelle on sert la disposition « ordinateur » : menu
 * complet en tuiles. En dessous, la navigation téléphone prend le relais
 * (onglets en bas + glissement entre écrans).
 */
export const DESKTOP_MIN_WIDTH = 900;

const QUERY = `(min-width: ${DESKTOP_MIN_WIDTH}px)`;

export function useIsDesktop(): boolean {
    const [isDesktop, setIsDesktop] = useState(
        () => typeof window !== "undefined" && window.matchMedia(QUERY).matches,
    );

    useEffect(() => {
        const media = window.matchMedia(QUERY);
        const update = () => setIsDesktop(media.matches);
        update();  // la largeur a pu changer avant l'abonnement (rotation, ouverture)
        media.addEventListener("change", update);
        return () => media.removeEventListener("change", update);
    }, []);

    return isDesktop;
}

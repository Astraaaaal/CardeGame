import { useQuery } from "@tanstack/react-query";
import axios from "axios";

export interface TypeDef {
    id: string;
    name: string;
    color: number[];
    in_use?: number;
}

const API_URL = import.meta.env.VITE_API_URL || "";

/**
 * Types de personnage (nom + couleur), gérés depuis le panneau admin.
 * Route publique — nécessaire au rendu des cartes pour tout client.
 */
export function useTypes() {
    return useQuery({
        queryKey: ["types"],
        queryFn: () =>
            axios.get<TypeDef[]>(`${API_URL}/api/types/`).then((r) => r.data),
        staleTime: 5 * 60_000,
    });
}

const FALLBACK_RGB = [106, 106, 128];

function findColor(types: TypeDef[] | undefined, name: string): number[] {
    return types?.find((t) => t.name === name)?.color ?? FALLBACK_RGB;
}

export function typeColor(types: TypeDef[] | undefined, name: string): string {
    const [r, g, b] = findColor(types, name);
    return `rgb(${r}, ${g}, ${b})`;
}

export function typeColorAlpha(
    types: TypeDef[] | undefined,
    name: string,
    alpha: number
): string {
    const [r, g, b] = findColor(types, name);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

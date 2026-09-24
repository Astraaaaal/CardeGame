#!/usr/bin/env python3
"""
Prépare les illustrations de cartes aux deux formats du jeu.

    python tools/preparer_illustrations.py <dossier> [--appliquer]

Deux formats, parce que le jeu a deux mises en page :
- **full art** : 900 × 1260 (5:7), l'illustration occupe toute la carte ;
- **normale**  : 800 × 600 (4:3), l'illustration tient dans sa fenêtre.

Le script **rogne** au centre plutôt que de déformer, et il ne retaille que ce
qui en a besoin : une image déjà au bon rapport et pas plus grande que la
cible est laissée telle quelle. Rogner plutôt que redimensionner évite
d'embarquer des pixels que personne ne verra jamais — sur un jeu qui se joue
au téléphone, chaque mégaoctet se paie en données mobiles.

Sans `--appliquer`, rien n'est écrit : le script dit seulement ce qu'il ferait.
"""

import argparse
import pathlib
import sys

try:
    from PIL import Image
except ImportError:  # pragma: no cover - dépend de l'environnement
    sys.exit("Pillow est nécessaire : pip install Pillow")

FORMATS = {
    "full": (900, 1260),    # 5:7, illustration pleine carte
    "normale": (800, 600),  # 4:3, fenêtre d'illustration
}
# Tolérance sur le rapport : 1 % d'écart ne se voit pas et ne mérite pas un
# nouvel encodage, qui ne ferait que dégrader l'image.
TOLERANCE = 0.01
QUALITE_JPEG = 86
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def rogner_au_centre(image: Image.Image, ratio_cible: float) -> Image.Image:
    """Garde la plus grande zone centrée qui respecte le rapport demandé."""
    largeur, hauteur = image.size
    if largeur / hauteur > ratio_cible:
        # Trop large : on coupe les côtés.
        neuve = int(round(hauteur * ratio_cible))
        gauche = (largeur - neuve) // 2
        return image.crop((gauche, 0, gauche + neuve, hauteur))
    # Trop haute : on coupe le haut et le bas.
    neuve = int(round(largeur / ratio_cible))
    haut = (hauteur - neuve) // 2
    return image.crop((0, haut, largeur, haut + neuve))


def deja_bonne(image: Image.Image, cible: tuple[int, int]) -> bool:
    """Vrai si l'image a le bon rapport et ne dépasse pas la taille cible."""
    largeur, hauteur = image.size
    ratio_cible = cible[0] / cible[1]
    bon_ratio = abs(largeur / hauteur - ratio_cible) <= TOLERANCE * ratio_cible
    return bon_ratio and largeur <= cible[0] and hauteur <= cible[1]


def traiter(chemin: pathlib.Path, format_nom: str, appliquer: bool) -> str:
    cible = FORMATS[format_nom]
    with Image.open(chemin) as image:
        image = image.convert("RGB")
        avant_ko = chemin.stat().st_size // 1024

        if deja_bonne(image, cible):
            return f"  inchangée  {chemin.name} ({image.size[0]}×{image.size[1]}, {avant_ko} Ko)"

        rognee = rogner_au_centre(image, cible[0] / cible[1])
        # On n'agrandit jamais : une image plus petite que la cible garde sa
        # définition, l'agrandir n'inventerait que du flou.
        finale = rognee if rognee.size <= cible else rognee.resize(cible, Image.LANCZOS)

        if not appliquer:
            return (f"  à traiter  {chemin.name} : {image.size[0]}×{image.size[1]}"
                    f" -> {finale.size[0]}×{finale.size[1]} ({avant_ko} Ko)")

        destination = chemin.with_suffix(".jpg")
        finale.save(destination, "JPEG", quality=QUALITE_JPEG, optimize=True)
        if destination != chemin:
            chemin.unlink()
        apres_ko = destination.stat().st_size // 1024
        return (f"  traitée    {destination.name} : {image.size[0]}×{image.size[1]}"
                f" -> {finale.size[0]}×{finale.size[1]} ({avant_ko} -> {apres_ko} Ko)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dossier", type=pathlib.Path, help="dossier contenant les illustrations")
    parser.add_argument("--format", choices=sorted(FORMATS), default="full",
                        help="format visé (défaut : full)")
    parser.add_argument("--appliquer", action="store_true",
                        help="écrire les fichiers ; sans cette option, rien n'est modifié")
    args = parser.parse_args()

    if not args.dossier.is_dir():
        sys.exit(f"Dossier introuvable : {args.dossier}")

    fichiers = sorted(f for f in args.dossier.iterdir()
                      if f.is_file() and f.suffix.lower() in EXTENSIONS)
    if not fichiers:
        sys.exit(f"Aucune image dans {args.dossier}")

    cible = FORMATS[args.format]
    mode = "ÉCRITURE" if args.appliquer else "SIMULATION (rien n'est modifié)"
    print(f"{len(fichiers)} image(s) — format « {args.format} » {cible[0]}×{cible[1]} — {mode}\n")
    for fichier in fichiers:
        try:
            print(traiter(fichier, args.format, args.appliquer))
        except Exception as erreur:  # noqa: BLE001 - un fichier illisible ne doit pas tout arrêter
            print(f"  ÉCHEC      {fichier.name} : {erreur}")

    if not args.appliquer:
        print("\nRelance avec --appliquer pour écrire les fichiers.")


if __name__ == "__main__":
    main()

# CardeGame — consignes de travail pour Claude

Ce fichier est lu automatiquement au début de chaque conversation Claude Code
dans ce dépôt. Il fixe la façon de travailler attendue sur le projet.

## Avant d'implémenter une demande

- **Poser beaucoup de questions de précision avant de coder** toute
  fonctionnalité non triviale : comportement attendu, interface, règles métier,
  cas limites, ce qui doit ou ne doit pas changer. Ne pas deviner quand un
  point est ambigu.
  - Utiliser l'outil de questions (choix multiples), en mettant l'option
    recommandée en premier avec « (Recommandé) » et un aperçu quand ça aide.
  - Plusieurs séries de questions si nécessaire ; mieux vaut une série de trop
    qu'une fonctionnalité à refaire.
  - Exceptions : correction de bug évidente, retouche mécanique déjà précisée.
- Traiter **toutes** les demandes d'un même message avant de faire le point,
  sans s'arrêter pour demander s'il faut continuer.
- Lister ce dont on a besoin de la part de l'utilisateur (comptes, clés,
  décisions) dès qu'une demande dépend d'un service externe.

## Commits

- Ne committer / pousser que sur demande.
- Un commit par fonctionnalité, avec un **titre en français clair** qui dit ce
  qui a été fait (ex. « Statut en ligne : hors ligne après 30 s d'inactivité »)
  et un corps en liste à puces — l'historique sert à la traçabilité.

## Vérifications

- Backend : `cd backend && PYTHONPATH=. .venv/Scripts/python.exe -m pytest -q`
- Frontend : `cd web && npx tsc --noEmit -p .`
- Tester en conditions réelles (serveur + navigateur) avant d'annoncer qu'une
  fonctionnalité marche ; dire clairement ce qui n'a pas pu être vérifié.
- Serveur local : `uvicorn` lancé depuis `backend/.venv`, sans rechargement
  automatique → le redémarrer après une modification backend, et vérifier le
  port 8000 (`netstat -ano`) pour ne pas tester un ancien processus.
- La base locale est la branche Neon « dev » : supprimer les comptes et
  données de test créés pendant la vérification.

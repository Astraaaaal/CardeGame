# Reprise automatique du travail

Ce fichier est la **consigne** lue par la routine planifiée « reprise » (agent
Claude dans le cloud). Il sert quand une limite d'usage a interrompu le travail
et que personne n'est là au moment où elle se réinitialise.

Garde-le court : l'agent démarre sans aucun contexte de la conversation.

## Ce que l'agent doit faire

1. Lire `CLAUDE.md` (façon de travailler attendue sur ce dépôt).
2. Reprendre **la tâche décrite ci-dessous**, et elle seule.
3. Vérifier : `cd backend && PYTHONPATH=. python -m pytest -q` et
   `cd web && npx tsc --noEmit -p .`
4. Travailler sur une **branche**, committer dessus, ouvrir une **pull request**.
   Ne jamais pousser sur `main`.
5. Si la tâche est ambiguë ou demande une décision de produit : ne pas deviner,
   décrire le choix à faire dans la description de la pull request.

## Ce que l'agent ne peut pas faire

Il tourne dans le cloud, pas sur la machine de Swann : pas de serveur local,
pas de navigateur, pas d'accès à la base Neon ni aux clés. Donc **aucune
vérification en conditions réelles** — il s'arrête à ce que les tests et le
typage peuvent prouver, et le dit dans la pull request.

## Tâche en cours

> Remplacer ce bloc avant d'armer la routine. S'il est resté vide, l'agent doit
> se contenter de lancer les vérifications et de signaler qu'aucune tâche
> n'était définie.

_(aucune tâche définie pour l'instant)_

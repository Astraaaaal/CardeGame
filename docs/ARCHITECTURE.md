# Architecture CardeGame

## Cible

Jeu de collection de cartes jouable **dans le navigateur** (PC + mobile), installable en PWA,
sans passer par un store.

```
┌─────────────┐      HTTPS/JSON      ┌──────────────────┐     asyncpg     ┌─────────────┐
│  web/  (PWA) │ ──────────────────► │  backend/ (API)  │ ──────────────► │  PostgreSQL  │
│  React + TS  │ ◄────────────────── │  FastAPI         │ ◄────────────── │  (Neon)      │
└─────────────┘                     └──────────────────┘                 └─────────────┘
```

Le serveur est **autorité** : RNG des packs, économie (coins), collection. Le client
n'affiche que ce que l'API renvoie — impossible de tricher en modifiant le client.

## Dossiers

| Dossier | Rôle | Statut |
|---------|------|--------|
| `backend/` | API FastAPI + SQLModel + JWT. Toute la logique de jeu. | ~90 %, opérationnel |
| `web/` | Client React (Vite, TanStack Query, Zustand, Framer Motion). PWA. **Client principal.** | scaffoldé, à finir |
| `prototype/` | Ancien client desktop pygame. Gardé comme référence de gameplay / rendu. **Plus modifié.** | figé |
| `assets/data/` | Données de jeu (sets, raretés, qualités, spécialités, jewelries, personnages, boosters) en JSON. Source du seed. | — |
| `assets/img/` | Images sources (personnages, overlays qualité/spécialité/jewelry). | — |
| `docs/` | Cette doc + le plan de migration. | — |
| `saves/` | Anciennes sauvegardes locales du prototype. Gitignoré. Non utilisé par le backend. | obsolète |

## Backend — endpoints

| Méthode | Route | Rôle |
|---------|-------|------|
| POST | `/api/auth/register` | Créer un compte (bcrypt) |
| POST | `/api/auth/login` | Login → access + refresh JWT |
| POST | `/api/auth/refresh` | Rotation des tokens |
| GET  | `/api/player/me` | Profil : coins, streak, stats |
| POST | `/api/player/daily-reward` | Récompense journalière (streak) |
| GET  | `/api/boosters/` | Liste des boosters |
| POST | `/api/boosters/open` | Ouvrir 1/5/10 packs — **génération + économie côté serveur** |
| GET  | `/api/collection/` | Collection groupée, triée, filtrée |
| GET  | `/api/collection/{id}` | Détail d'une carte |
| POST | `/api/admin/seed` | Charger les données de référence depuis `assets/data/*.json` |
| POST | `/api/admin/migrate-players` | Importer les anciennes sauvegardes du prototype |
| GET  | `/api/health` | Healthcheck |

## Modèle de données

- `users` — compte, `password_hash` (bcrypt), `coins`, `packs_opened`, `total_cards`, `login_streak`, `last_daily_claim`
- `user_cards` — une ligne par carte possédée : FK vers `characters`, `sets`, `rarities`, `qualities`, `specialties`, `jewelries` + `drop_probability`, `rendered_url`, `obtained_at`
- `refresh_tokens` — hash + expiration, rotation à chaque refresh
- Tables de référence (ex-JSON) : `sets`, `rarities`, `qualities`, `specialties`, `jewelries`, `characters`, `character_sets` (liaison + poids par set), `boosters`

## Génération d'une carte

Personnage (pondéré par set) × rareté × qualité × spécialité × jewelry, chaque tirage
pondéré par un `weight`. La probabilité combinée exacte est calculée et stockée sur la carte.

- **rareté** : common 95 · rare 3 · epic 1.5 · legendary 0.5
- **qualité** : 14 paliers d'usure (`authentic` … `destroyed`)
- **spécialité** : normal · full_art · ex · shiny
- **jewelry** (finition de bordure) : none · silver · gold · diamond · prismatic

## Environnements

| | Dev (maintenant) | Prod (plus tard) |
|---|---|---|
| BDD | Postgres Neon distant (Frankfurt) | Postgres Render OU Neon |
| Backend | `uvicorn` local, pointe sur Neon | Docker sur Render |
| Web | `npm run dev` (Vite, proxy `/api` → localhost:8000) | site statique Render |

« Poussable en prod » = la seule différence est l'URL de l'API (`VITE_API_URL`) et le `DATABASE_URL`.

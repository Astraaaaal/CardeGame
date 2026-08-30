# Plan de migration — prototype pygame → web

## Décisions prises

1. **Client = web (React PWA)**, pas pygame, pas d'app native. Une base de code
   pour PC + mobile, installable, sans store.
2. **Backend en Python (FastAPI)** conservé — bon choix pour une API, aucun intérêt à réécrire.
3. **BDD distante dès le dev** : Postgres Neon (région Frankfurt / `eu-central-1`).
4. Le prototype pygame est **figé** dans `prototype/`, gardé pour référence (gameplay, rendu de carte).
5. Restructuration du dépôt : `src/`→`prototype/src/`, `frontend/`→`web/`.

## Étapes

### Étape 1 — Infra ✅ (28/08/2026)

- [x] Restructurer les dossiers
- [x] `.gitignore`, `render.yaml`, docs
- [x] Projet Postgres Neon créé (`square-firefly-06488881`, région `eu-central-1` / Frankfurt) → `DATABASE_URL`
- [x] `backend/.env` rempli (`DATABASE_URL`, `JWT_SECRET` généré)
- [x] venv `backend/.venv` (Python 3.11) + `pip install -r backend/requirements.txt`
- [x] `uvicorn app.main:app` → 11 tables créées sur Neon au démarrage
- [x] `POST /api/admin/seed` → 4 sets, 4 raretés, 14 qualités, 4 spécialités, 5 jewelries, 1 personnage, 4 boosters
- [x] Smoke test complet OK (auth, profil, daily, ouverture de packs, collection)
- [ ] (option) importer les anciennes sauvegardes : `POST /api/admin/migrate-players`

**Fin d'étape 1** : la BDD Neon contient les données de référence, l'API tourne en local et répond.

#### Contrainte réseau découverte

Le **réseau d'entreprise bloque les connexions Postgres sortantes** (le TCP passe, le
protocole PG est filtré). Neon n'est joignable que hors de ce réseau (partage de connexion,
maison, VPN perso). **Décision en attente** : installer un PostgreSQL local pour le dev
quotidien (le `DATABASE_URL` reste la seule différence dev/prod), ou travailler contre Neon
uniquement depuis un réseau non filtré.

#### Corrections backend faites au passage (commit `1346a8e`)

- `passlib` (abandonné, casse avec `bcrypt>=5`) remplacé par la lib `bcrypt` directe
- `auth_service` : `expires_at` recevait un `int` au lieu d'un `datetime` → 500 au login
- `main.py` : stdout/stderr forcés en UTF-8 (sinon un `print` non-cp1252 plante la requête sous Windows)

> **Découverte (28/08/2026)** : `web/` n'est pas un squelette mais une implémentation
> quasi complète du cœur de boucle. `tsc --noEmit` = 0 erreur. Les étapes 2 et 3 sont
> déjà fonctionnelles ; les étapes 4 et 5 sont codées mais pas encore testées en
> navigateur visible.

### Étape 2 — Auth bout en bout (web) ✅

- [x] Écran login/register branché sur `/api/auth/*` ([LoginPage.tsx](../web/src/pages/LoginPage.tsx))
- [x] Tokens en `localStorage` + intercepteur axios avec refresh auto ([api/client.ts](../web/src/api/client.ts))
- [x] Routes protégées → redirection `/login` ([App.tsx](../web/src/App.tsx))
- [x] Testé navigateur : register → auto-login → MainMenu, compte créé sur Neon

### Étape 3 — Profil & récompense journalière ✅

- [x] MainMenu affiche coins / streak réels (`/api/player/me`)
- [x] Popup daily reward auto-réclamée au login (`+500`, persisté sur Neon)
- [ ] Bug env de test : la modale daily reward ne se ferme pas quand l'onglet est
      caché (animation Framer Motion en pause). À revérifier en navigateur visible.

### Étape 4 — Boutique & ouverture de packs — codé, à vérifier

- [x] Composants présents : [BoosterShop.tsx](../web/src/pages/BoosterShop.tsx),
      [PackOpening.tsx](../web/src/pages/PackOpening.tsx), [CardReveal.tsx](../web/src/components/card/CardReveal.tsx)
- [x] API vérifiée par smoke test : ouverture 1/5/10, réductions, erreur 400 « pas assez de pièces »
- [ ] Passe de test en navigateur visible + correction des bugs

### Étape 5 — Collection — codé, à vérifier

- [x] Composants présents : [Collection.tsx](../web/src/pages/Collection.tsx),
      [CardGrid.tsx](../web/src/components/card/CardGrid.tsx), [CardDetail.tsx](../web/src/components/card/CardDetail.tsx)
- [x] API vérifiée : grille groupée, tri, filtres, détail
- [ ] Passe de test en navigateur visible

### Étape 6 — Rendu des cartes (vrai reste à faire)

`web/src/components/card/CardImage.tsx` a déjà un **fallback** : sans `rendered_url`
(cas actuel, pas de Cloudinary), il affiche un placeholder avec le nom + bordure
couleur rareté. Rien ne casse — c'est juste basique visuellement.

**Choix fait : rendu client (option A).** `web/src/components/card/CardImage.tsx` compose
la carte en CSS/DOM à partir des métadonnées : art du personnage en fond, cadre
rareté/jewelry + glow, badge type, chip rareté, nom + spécialité, description, gen/set,
effet d'usure par qualité (filtres CSS), sheen shiny, aura ex. Unités `cqi` → mise à
l'échelle propre. `CardReveal` et `CardDetail` réutilisent ce composant. Premier jet
solide ; passe visuelle plus poussée (typo, holo, dos de carte) à prévoir.

### Passe de dette rapide ✅ (30/08/2026)

- [x] Warnings React Router → `future` flags dans `<BrowserRouter>`
- [x] `regex=` → `pattern=` dans `collection.py` (déprécié)
- [x] `drop_probability` : vrai calcul (poids / somme des poids, produit des axes),
      plus de fudge `*1000`. Affiché « 1 sur N ». 110 lignes recalculées sur Neon.
- [x] Portrait perso 5,47 Mo → 297 Ko (resize 600px, PNG optimisé)
- [x] Collection : barre de recherche par nom + bouton sens de tri (↑/↓),
      option de tri « Récent » (cassée, 422) remplacée par « Nom » + « Rareté réelle »

### Étape 7 — Durcissement avant prod  (30/08/2026)

- [x] `/api/admin/*` protégé par en-tête `X-Admin-Key` (= `ADMIN_KEY`, vide → refusé)
- [x] Renderer serveur court-circuité si Cloudinary non configuré (renvoie `None`)
- [x] Seed embarqué : `assets/data/*.json` copiés dans `backend/app/seed/data/`
      (repli sur `assets/` en dev). `/admin/seed` marche donc dans l'image Docker.
- [x] `POST /api/auth/logout` (révoque le refresh token) + câblé côté web
- [x] Rate limiting maison (en mémoire, par IP) sur `/auth/*` et `/boosters/open`
- [x] Icônes PWA + favicon générées (`web/public/icons/`, `web/public/favicon.ico`)
- [x] `backend/.dockerignore` (n'embarque pas `.env` ni `.venv`)
- [x] Dockerfile : bind sur `$PORT`, `--proxy-headers` (vraie IP client)
- [x] `render.yaml` : plus de Postgres Render (on garde Neon) ; `DATABASE_URL` en secret,
      `ADMIN_KEY` auto-généré ; guide dans [DEPLOY.md](DEPLOY.md)
- [ ] Alembic (repoussé — `create_all` est idempotent et suffit tant qu'on n'*altère*
      pas de colonnes ; à faire à la 1ʳᵉ vraie migration de schéma)
- [ ] Déploiement Render effectif (à faire par l'utilisateur, cf. DEPLOY.md)

## Dette connue (non bloquante)

- `python-jose` (JWT backend) vieillissant → migrer vers `pyjwt` un jour.
- Contenu : **1 seul personnage**, seul le set A1 a des personnages. Les boosters
  A2 / A2bis / A2.5 renvoient un pack vide (`generate_pack` → `[]`).
- Portrait perso servi en PNG 297 Ko ; si beaucoup de persos un jour, prévoir un
  pipeline d'images au build (WebP).
- `prototype/` : `card_generator.py` local est mort (le serveur génère). Le renderer
  du prototype compare aussi `quality_id` en CamelCase (IDs réels en minuscules).

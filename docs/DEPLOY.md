# Déploiement sur Render

Architecture cible : **API Docker** + **site statique PWA** sur Render, **Postgres Neon** externe.

## Prérequis

- Compte [Render](https://render.com) (gratuit, connexion via GitHub)
- Le repo `Astraaaaal/CardeGame` à jour sur `main`
- L'URL de connexion Neon (projet `square-firefly-06488881`, version **directe**, pas `-pooler`)

## 1. Créer les services (Blueprint)

1. Render → **New +** → **Blueprint**
2. Connecter le repo `Astraaaaal/CardeGame`, brancher sur `main`
3. Render lit [`render.yaml`](../render.yaml) et propose 2 services :
   - `cardegame-api` (web, Docker, région Frankfurt)
   - `cardegame` (site statique)
4. **Apply**

## 2. Renseigner les secrets de l'API

Sur le service `cardegame-api` → onglet **Environment** :

| Variable | Valeur |
|----------|--------|
| `DATABASE_URL` | l'URL Neon directe (elle peut commencer par `postgresql://` et finir par `?sslmode=require`, le backend s'en accommode) |
| `JWT_SECRET` | *auto-généré, ne pas toucher* |
| `ADMIN_KEY` | *auto-généré — **copier la valeur**, elle sert au seed* |
| `BETA_INVITE_CODE` | optionnel — vide = inscription libre ; sinon requis pour créer un compte |
| `CLOUDINARY_*` | laisser vide (rendu des cartes côté client) |
| `PUBLIC_APP_URL` | URL du jeu, utilisée dans les liens des e-mails et le retour de paiement |
| `BREVO_API_KEY` | clé API Brevo (SMTP & API → Clés API) — vide = e-mails écrits dans les logs |
| `BREVO_NEWSLETTER_LIST_ID` | numéro de la liste Brevo des abonnés newsletter — vide/0 = pas de synchro |
| `EMAIL_SENDER_ADDRESS` | adresse d'expédition **validée dans Brevo** (domaine authentifié) |
| `STRIPE_SECRET_KEY` | clé Stripe — de préférence une **clé restreinte** (`rk_test_…` pour tester, `rk_live_…` en réel) avec la seule permission *Checkout Sessions : écriture* ; une clé secrète `sk_…` marche aussi — vide = achats refusés |
| `STRIPE_WEBHOOK_SECRET` | secret du webhook Stripe (`whsec_…`), voir ci-dessous — vide = achats refusés |

La boutique premium reste **fermée** tant qu'elle n'est pas activée dans le panel admin (onglet Premium) ;
seuls les pseudos listés comme testeurs la voient avant.

### Webhook Stripe

Dashboard Stripe → **Développeurs → Webhooks → Ajouter une destination** (en mode test, puis à refaire en mode live) :

- URL : `https://cardegame-api.onrender.com/api/premium/stripe-webhook`
- Événements : `checkout.session.completed`, `checkout.session.async_payment_succeeded`,
  `checkout.session.async_payment_failed`, `checkout.session.expired`, `charge.refunded`
- Copier le **secret de signature** (`whsec_…`) dans `STRIPE_WEBHOOK_SECRET`.

Une commande n'est créditée qu'à la réception de `checkout.session.completed` (montant et devise vérifiés) ;
une page de paiement expire au bout de 30 min et la commande passe alors en « Échouée ».
Un remboursement fait depuis Stripe passe la commande en « Remboursée » sans retirer le contenu crédité.

En local : installer la [CLI Stripe](https://docs.stripe.com/stripe-cli), `stripe login`, puis
`stripe listen --forward-to localhost:8000/api/premium/stripe-webhook` — le `whsec_…` affiché va dans `backend/.env`.
Carte de test : `4242 4242 4242 4242`, date future, CVC quelconque.

Save → l'API redéploie.

## 3. Vérifier l'API

```
https://cardegame-api.onrender.com/api/health   →   {"status":"ok","version":"1.0.0"}
```

(Premier accès après inactivité : ~50 s de réveil, c'est le free tier.)

## 4. Seed de la base de prod

Une seule fois (idempotent — si la base Neon contient déjà les données de réf., il répond « déjà présentes ») :

```bash
curl -X POST https://cardegame-api.onrender.com/api/admin/seed \
  -H "X-Admin-Key: LA_VALEUR_DE_ADMIN_KEY"
```

## 5. Recaler les URLs si Render a renommé un service

Render ajoute parfois un suffixe si le nom est pris (`cardegame-api-x7k2`). Si c'est le cas :

- service `cardegame` → **Environment** → `VITE_API_URL` = l'URL réelle de l'API → redéployer
- service `cardegame-api` → **Environment** → `CORS_ORIGINS` = `["https://URL-REELLE-DU-SITE"]` → redéployer

## 6. Tester

Ouvrir `https://cardegame.onrender.com` : créer un compte, ouvrir un pack, collection.
Sur mobile : menu du navigateur → **Ajouter à l'écran d'accueil** (PWA).

## Après

- **Redéploiement auto** à chaque `push` sur `main` (Render surveille le repo).
- **Cold start** : l'API free s'endort après ~15 min d'inactivité ; le premier appel suivant met ~50 s.

## Bases séparées dev / prod

Le local pointe sur une branche Neon `dev` (copie de `production`, `backend/.env` →
`DATABASE_URL`), Render reste sur `production`. Si `dev` devient trop sale à force de
tests, elle peut être réinitialisée depuis Neon (reset from parent) sans toucher à la prod.

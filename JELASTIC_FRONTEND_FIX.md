# Fix Frontend API URLs - Déploiement Manuel Jelastic

## Problème
Le frontend fait des appels API à `localhost:8000` au lieu de l'URL Jelastic.

## Solution Rapide

### Étape 1: Se connecter au node frontend
Depuis la console Jelastic, ouvre un terminal SSH sur le node **frontend**.

### Étape 2: Reconstruire le frontend
```bash
# Aller dans /tmp et nettoyer
cd /tmp
rm -rf brawlgpt

# Cloner le repo
git clone https://github.com/san2stic/BrawlGPT.git

# Aller dans le dossier frontend
cd brawlgpt/frontend

# Installer les dépendances
npm ci

# Construire avec URL relative (important!)
VITE_API_URL='' npm run build

# Déployer la nouvelle build
rm -rf /usr/share/nginx/html/*
cp -r dist/* /usr/share/nginx/html/

# Recharger nginx
nginx -s reload

# Nettoyer
cd /tmp
rm -rf brawlgpt
```

### Étape 3: Vider le cache du navigateur
1. Ouvre la console DevTools (F12)
2. Fais un clic droit sur le bouton refresh
3. Sélectionne "Vider le cache et effectuer une actualisation forcée"

## Pourquoi VITE_API_URL='' ?

Avec une URL vide, le frontend fera des appels API **relatifs** (ex: `/api/player/...`).
Le nginx reverse proxy s'occupera de router ces requêtes vers le backend.

## URL Correcte d'Accès

**✅ CORRECT:** `https://brawlgpt.icloud-ver.jpe.lk-server.com`  
**❌ INCORRECT:** `https://brawlgpt.icloud-ver.jpe.lk-server.com:3000`

Le port 3000 bypasse le nginx reverse proxy !

## Vérification

Après le rebuild, vérifie dans la console du navigateur :
- Les appels API doivent être vers `/api/...` (URL relative)
- Plus d'erreurs `ERR_CONNECTION_REFUSED`

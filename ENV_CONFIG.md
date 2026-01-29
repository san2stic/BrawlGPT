# =============================================================================
# BrawlGPT - Configuration Centralisée
# =============================================================================

## Vue d'ensemble

Toutes les variables d'environnement sont maintenant centralisées dans **un seul fichier** :

```
/Users/bastienjavaux/kDrive2/BrawlGPT/.env
```

## Structure du fichier .env

Le fichier est organisé en sections claires :

### 📍 DEPLOYMENT CONFIGURATION
- `ENVIRONMENT` - Type d'environnement (local/jelastic/production)
- `VITE_API_URL` - URL de l'API backend (pour le frontend)
- `ALLOWED_ORIGINS` - URLs autorisées pour CORS

### 🔐 API KEYS & SECRETS
- `SECRET_KEY` - Clé JWT pour l'authentification
- `BRAWL_API_KEY` - Clé API Brawl Stars
- `OPENROUTER_API_KEY` - Clé API OpenRouter/AI

### 🗄️ DATABASE CONFIGURATION
- `DATABASE_URL` - URL de connexion PostgreSQL
- `POSTGRES_USER/PASSWORD/DB` - Credentials PostgreSQL

### 💾 REDIS CACHE
- `REDIS_URL` - URL de connexion Redis
- `REDIS_ENABLED` - Active/désactive le cache

### 🛡️ SECURITY & RATE LIMITING
- `RATE_LIMIT_*` - Limites de requêtes par endpoint

### 📊 LOGGING
- `LOG_LEVEL` - Niveau de logs (INFO, DEBUG, etc.)
- `LOG_FORMAT` - Format des logs (json, text)

### 🤖 AI CONFIGURATION
- `AI_MODEL` - Modèle IA à utiliser
- `AI_MAX_TOKENS` - Tokens maximum
- `AI_TEMPERATURE` - Température du modèle

### 🚀 FEATURE FLAGS
- `ENABLE_META_CRAWLER` - Active le crawler meta
- `ENABLE_PROGRESSION_TRACKING` - Active le suivi de progression
- etc.

## Comment utiliser

### 1. Local Development

Pour développer en local, modifie dans `.env` :
```bash
ENVIRONMENT=local
VITE_API_URL=http://localhost:8000
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 2. Jelastic Deployment

Pour déployer sur Jelastic, modifie dans `.env` :
```bash
ENVIRONMENT=jelastic
VITE_API_URL=http://brawlgpt.jcloud-ver-jpe.ik-server.com:8000
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://brawlgpt.jcloud-ver-jpe.ik-server.com:3000
```

### 3. Rebuilder après modifications

Après toute modification du `.env` :
```bash
# Rebuild et redémarre tout
docker-compose down
docker-compose build
docker-compose up -d

# Ou juste rebuild un service
docker-compose build backend
docker-compose up -d backend
```

## Fichiers supprimés/dépréciés

Les fichiers suivants ne sont **plus utilisés** (ils peuvent être supprimés) :
- ❌ `frontend/.env` - Remplacé par `.env` racine
- ❌ `backend/.env` - Remplacé par `.env` racine  
- ❌ `frontend/.env.production` - Remplacé par `.env` racine

## Migration effectuée

✅ **docker-compose.yml** mis à jour :
- Backend utilise `.env` racine
- Frontend utilise `${VITE_API_URL}` du `.env` racine
- Postgres utilise `${POSTGRES_*}` du `.env` racine

✅ **Un seul fichier à maintenir** : `.env` à la racine

✅ **Plus simple à gérer** : Change juste 2-3 lignes pour switcher entre local/production

## Avantages

✨ **Simplicité** - Un seul fichier de config au lieu de 3
✨ **Cohérence** - Toutes les valeurs au même endroit
✨ **Documentation** - Sections claires et commentées
✨ **Flexibilité** - Facile de switcher entre environnements

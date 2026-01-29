# Environment Configuration Guide

## 🔑 API Keys Required

### 1. Brawl Stars API Key

**⚠️ IMPORTANT: Générez une nouvelle clé SANS restriction IP**

1. Allez sur [https://developer.brawlstars.com/](https://developer.brawlstars.com/)
2. Connectez-vous avec votre compte Supercell
3. Créez une nouvelle clé API
4. **IMPORTANT**: Laissez le champ IP vide ou mettez `0.0.0.0/0` pour permettre toutes les IPs
5. Copiez la clé générée

**Pourquoi?** Votre clé actuelle est restreinte à l'IP `104.28.208.115` ce qui cause les erreurs "Load failed" quand vous vous connectez depuis une autre IP ou via Jelastic.

### 2. OpenRouter API Key

1. Allez sur [https://openrouter.ai/](https://openrouter.ai/)
2. Créez un compte / connectez-vous
3. Allez dans "Keys" et créez une nouvelle clé
4. Copiez la clé (commence par `sk-or-v1-`)

### 3. JWT Secret

Un secret aléatoire pour signer les tokens JWT (minimum 32 caractères).
Vous pouvez en générer un avec:
```bash
openssl rand -hex 32
```

## 📝 Configuration des fichiers

### Backend (.env)

Créez ou modifiez `backend/.env`:

```env
# Security Configuration
SECRET_KEY=your-jwt-secret-here-min-32-chars

# Brawl Stars API Configuration (NOUVELLE CLÉ SANS RESTRICTION IP)
BRAWL_API_KEY=your-new-unrestricted-api-key-here

# OpenRouter API Key
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# CORS Allowed Origins (ajoutez votre domaine Jelastic)
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,https://your-jelastic-domain.com

# Database (sera configuré automatiquement par Docker)
DATABASE_URL=postgresql+asyncpg://brawl_user:brawl_password@postgres:5432/brawlgpt_db

# Redis (sera configuré automatiquement par Docker)
REDIS_URL=redis://redis:6379/0

# Logging
LOG_LEVEL=INFO
DEBUG=false
```

### Frontend (.env)

Créez ou modifiez `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

## 🚀 Déploiement Local (Docker)

```bash
# Copier le fichier .env
cp backend/.env.example backend/.env
# Éditer avec vos clés
nano backend/.env

# Lancer l'application
docker compose up -d

# Vérifier les logs
docker compose logs -f backend
```

## ☁️ Déploiement Jelastic

Lors de l'installation via Jelastic:

1. **Brawl Stars API Key**: Utilisez votre NOUVELLE clé sans restriction IP
2. **OpenRouter API Key**: Votre clé OpenRouter
3. **JWT Secret**: Laissez le défaut auto-généré ou utilisez le vôtre

Le manifest Jelastic configurera automatiquement:
- PostgreSQL avec credentials sécurisés
- Redis pour le cache
- Nginx comme reverse proxy
- SSL automatique

## 🔧 Vérification

Après déploiement, testez:

```bash
# Health check simple
curl https://your-domain.com/health

# Health check détaillé
curl https://your-domain.com/health/detailed
```

## ⚠️ Sécurité

**CE QUI A ÉTÉ RETIRÉ:**
- ✅ Aucune restriction IP dans le backend
- ✅ Pas de middleware IP whitelist
- ✅ Pas de validation d'IP dans les routes

**CE QUI RESTE POUR LA SÉCURITÉ:**
- ✅ JWT pour l'authentification utilisateur
- ✅ Rate limiting sur les endpoints API
- ✅ CORS configuré pour limiter les origines
- ✅ Passwords hachés avec Argon2
- ✅ Validation des tokens JWT

**IMPORTANT**: La restriction IP était dans votre BRAWL_API_KEY elle-même. En générant une nouvelle clé sans restriction IP, vous résolvez le problème "Load failed".

## 🐛 Dépannage

### "Load failed" lors du login

**Cause**: Votre ancienne clé API Brawl Stars est restreinte à l'IP `104.28.208.115`

**Solution**: 
1. Générez une NOUVELLE clé API sur developer.brawlstars.com
2. Laissez le champ IP vide ou mettez `0.0.0.0/0`
3. Mettez à jour `BRAWL_API_KEY` dans votre `.env`
4. Redémarrez: `docker compose restart backend`

### Erreurs CORS

Ajoutez votre domaine Jelastic dans `ALLOWED_ORIGINS`:
```env
ALLOWED_ORIGINS=http://localhost:5173,https://env-1234567.jelastic.infomaniak.com
```

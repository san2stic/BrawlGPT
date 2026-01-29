# 🔧 Résolution du Problème "Load Failed" avec IP Fixe sur Jelastic

## 🎯 Problème

Lors du déploiement sur Jelastic avec une **IP publique fixe**, vous obtenez l'erreur **"Load failed"**.

## 🔍 Causes Principales

### 1. Configuration CORS Incorrecte
L'application backend rejette les requêtes venant de l'IP fixe car elle n'est pas dans `ALLOWED_ORIGINS`.

### 2. URL Frontend Mal Configurée
Le frontend essaie de contacter le backend via une mauvaise URL.

### 3. Services Non Démarrés
Les containers Docker ne sont pas complètement démarrés après le déploiement.

## ✅ Solutions

### Solution 1: Utiliser le Nouveau Manifest (RECOMMANDÉ)

J'ai créé `manifest-compose-fixed-ip.jps` qui configure automatiquement tout :

```bash
# Déployer avec :
1. Dans Jelastic → Import
2. Sélectionner manifest-compose-fixed-ip.jps
3. Entrer vos clés API
4. Installer
```

**Ce que fait ce manifest :**
- ✅ Active automatiquement l'IP fixe (`extip: true`)
- ✅ Configure `ALLOWED_ORIGINS` avec l'IP fixe
- ✅ Configure `VITE_API_URL` pour pointer vers l'IP fixe
- ✅ Attend suffisamment longtemps pour que tous les services démarrent

### Solution 2: Corriger Manuellement le Déploiement Existant

Si vous avez déjà déployé et que vous voulez corriger :

#### Étape 1: Vérifier l'IP Fixe
```bash
# Dans Jelastic Web SSH
curl ifconfig.me
# Note cette IP, par exemple: 193.121.201.205
```

#### Étape 2: Mettre à Jour backend/.env
```bash
cd /root/BrawlGPT/backend
nano .env
```

Modifiez la ligne `ALLOWED_ORIGINS` :
```bash
ALLOWED_ORIGINS=http://VOTRE_IP:3000,http://localhost:3000,http://frontend
```

Remplacez `VOTRE_IP` par votre IP fixe (ex: 193.121.201.205).

#### Étape 3: Créer docker-compose.override.yml
```bash
cd /root/BrawlGPT
nano docker-compose.override.yml
```

Ajoutez :
```yaml
services:
  backend:
    environment:
      - ALLOWED_ORIGINS=http://VOTRE_IP:3000,http://localhost:3000,http://frontend
  
  frontend:
    build:
      args:
        - VITE_API_URL=http://VOTRE_IP:8000
```

#### Étape 4: Redéployer
```bash
cd /root/BrawlGPT
docker compose down
docker compose up -d --build
```

#### Étape 5: Attendre et Vérifier
```bash
# Attendre 2-3 minutes puis :
docker compose ps

# Vérifier les logs
docker compose logs backend --tail 20
docker compose logs frontend --tail 20

# Tester le backend
curl http://localhost:8000/health
```

### Solution 3: Configuration Firewall Jelastic

Assurez-vous que les ports sont ouverts :

1. Dans Jelastic Dashboard
2. Sélectionnez votre environnement
3. Allez dans **Settings** → **Firewall**
4. Ajoutez ces règles :

| Port | Protocol | Source | Action |
|------|----------|--------|--------|
| 3000 | TCP | 0.0.0.0/0 | Allow |
| 8000 | TCP | 0.0.0.0/0 | Allow |

## 🧪 Tests de Diagnostic

### Test 1: Services Docker
```bash
docker compose ps
```
**Attendu :** Tous les services doivent être "Up (healthy)"

### Test 2: Backend Health
```bash
curl http://localhost:8000/health
```
**Attendu :**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

### Test 3: Frontend
```bash
curl -I http://localhost:80
```
**Attendu :** `HTTP/1.1 200 OK`

### Test 4: Accès Externe
Depuis votre ordinateur :
```bash
curl http://VOTRE_IP:8000/health
```

## 📝 Checklist de Vérification

- [ ] IP fixe activée dans Jelastic (`extip: true`)
- [ ] `ALLOWED_ORIGINS` contient l'IP fixe
- [ ] `VITE_API_URL` pointe vers l'IP fixe
- [ ] Firewall autorise ports 3000 et 8000
- [ ] Services Docker tous "healthy"
- [ ] Backend répond sur `/health`
- [ ] Frontend accessible depuis navigateur

## 🚨 Erreurs Courantes

### Erreur: "CORS policy blocked"
**Cause :** `ALLOWED_ORIGINS` mal configuré

**Solution :**
```bash
cd /root/BrawlGPT/backend
# Vérifier .env
cat .env | grep ALLOWED_ORIGINS

# Si incorrect, corriger et redémarrer
docker compose restart backend
```

### Erreur: "Failed to fetch"
**Cause :** Frontend essaie de contacter mauvaise URL

**Solution :**
```bash
# Vérifier la configuration compilée dans le frontend
docker compose exec frontend cat /usr/share/nginx/html/assets/*.js | grep -o 'http://[^"]*8000'

# Si incorrect, rebuild le frontend
docker compose up -d --build frontend
```

### Erreur: "Connection refused"
**Cause :** Services pas encore démarrés

**Solution :**
```bash
# Attendre et vérifier
sleep 60
docker compose ps
docker compose logs backend
```

## 🎯 Accès Final

Une fois tout configuré, vous devriez pouvoir accéder à :

- **Frontend :** `http://VOTRE_IP:3000`
- **Backend API :** `http://VOTRE_IP:8000`
- **API Docs :** `http://VOTRE_IP:8000/docs`

## 📞 Besoin d'Aide ?

Si le problème persiste :

1. **Collectez les logs :**
```bash
cd /root/BrawlGPT
docker compose logs > /tmp/all-logs.txt
```

2. **Vérifiez la configuration :**
```bash
# Backend .env
cat backend/.env

# Docker override
cat docker-compose.override.yml

# IP publique
curl ifconfig.me
```

3. **Partagez ces informations** dans une issue GitHub

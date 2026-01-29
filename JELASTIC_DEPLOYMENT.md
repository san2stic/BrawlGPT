# 🚀 Déploiement BrawlGPT sur Jelastic Infomaniak

Guide complet pour déployer BrawlGPT sur la plateforme Jelastic d'Infomaniak.

## 📋 Prérequis

Avant de commencer, assurez-vous d'avoir:

1. **Compte Jelastic Infomaniak**
   - Créez un compte sur [https://jelastic.infomaniak.com](https://jelastic.infomaniak.com)
   - Vérifiez que vous avez suffisamment de cloudlets disponibles (minimum recommandé: 16 cloudlets flexibles)

2. **Clés API requises**
   - **Brawl Stars API Key**: Obtenez-la sur [https://developer.brawlstars.com](https://developer.brawlstars.com)
   - **OpenRouter API Key**: Obtenez-la sur [https://openrouter.ai](https://openrouter.ai)
   
3. **Fichier de déploiement**
   - Le fichier `manifest.jps` de ce dépôt

## 🎯 Déploiement en Un Clic

### Méthode 1: Import Direct du Manifest

1. **Connectez-vous à Jelastic**
   - Accédez à [https://jelastic.infomaniak.com](https://jelastic.infomaniak.com)
   - Connectez-vous avec votre compte

2. **Importer le Manifest**
   - Cliquez sur "Import" en haut à droite
   - Sélectionnez l'onglet "Local file" ou "URL"
   - Si URL: collez le lien vers votre `manifest.jps` (exemple: `https://raw.githubusercontent.com/san2stic/BrawlGPT/main/manifest.jps`)
   - Si fichier local: uploadez le fichier `manifest.jps`

> [!NOTE]
> Le déploiement clone automatiquement le dépôt GitHub et build les applications. Cela peut prendre 5-10 minutes.

3. **Configuration**
   Remplissez le formulaire avec vos informations:
   
   ```
   Brawl Stars API Key: [Votre clé API]
   OpenRouter API Key: [Votre clé API]
   JWT Secret Key: [Généré automatiquement ou personnalisé]
   Custom Domain (optionnel): brawlgpt.votredomaine.com
   ```

4. **Lancer le déploiement**
   - Cliquez sur "Install"
   - Attendez 5-10 minutes pendant que Jelastic:
     1. Provisionne les nœuds
     2. Clone le dépôt GitHub
     3. Installe les dépendances backend (pip)
     4. Build le frontend (npm)
     5. Configure et démarre les services
   - Une fois terminé, vous recevrez l'URL d'accès

### Méthode 2: Déploiement Manuel via Docker Compose

Si vous préférez un contrôle plus granulaire:

1. **Créer un nouvel environnement**
   - Cliquez sur "New Environment"
   - Sélectionnez "Docker" comme technologie
   - Configurez les nœuds:
     - 1x Docker Engine pour Backend (flexCloudlets: 8)
     - 1x Docker Engine pour Frontend (flexCloudlets: 4)
     - 1x PostgreSQL 15
     - 1x Redis 7
     - 1x Nginx

2. **Déployer le code**
   ```bash
   # Cloner le dépôt via le gestionnaire de fichiers Jelastic
   # ou utiliser le deployment center
   ```

3. **Configurer les variables d'environnement**
   Dans chaque nœud, ajoutez les variables nécessaires (voir section Configuration ci-dessous)

## ⚙️ Configuration Post-Déploiement

### Variables d'Environnement Backend

Dans le nœud Backend, configurez:

```bash
BRAWL_API_KEY=votre_cle_brawl_stars
OPENROUTER_API_KEY=votre_cle_openrouter
SECRET_KEY=votre_secret_jwt_32_chars_minimum
DATABASE_URL=postgresql+asyncpg://brawl_user:PASSWORD@postgres-node:5432/brawlgpt_db
REDIS_URL=redis://redis-node:6379/0
ALLOWED_ORIGINS=https://votredomaine.com
LOG_LEVEL=INFO
DEBUG=false
```

### Configuration du Domaine Personnalisé

1. **Configuration DNS**
   - Dans votre gestionnaire DNS, créez un enregistrement CNAME:
     ```
     brawlgpt.votredomaine.com → env-XXXXX.jelastic.infomaniak.com
     ```
   - Ou un enregistrement A pointant vers l'IP de votre environnement Jelastic

2. **SSL/TLS**
   - Jelastic génère automatiquement un certificat Let's Encrypt
   - Pour un certificat personnalisé:
     - Allez dans "Settings" → "Custom SSL"
     - Uploadez votre certificat et votre clé privée

3. **Lier le domaine**
   - Dans Jelastic, allez dans "Settings" → "Custom Domains"
   - Ajoutez votre domaine: `brawlgpt.votredomaine.com`
   - Activez SSL

## 🔍 Vérification du Déploiement

### Health Checks

Une fois déployé, vérifiez que tous les services fonctionnent:

1. **API Backend**
   ```bash
   curl https://votredomaine.com/health
   ```
   Devrait retourner:
   ```json
   {
     "status": "healthy",
     "database": "connected",
     "redis": "connected"
   }
   ```

2. **Frontend**
   - Accédez à `https://votredomaine.com`
   - L'interface React devrait se charger

3. **Documentation API**
   - Accédez à `https://votredomaine.com/docs`
   - La documentation Swagger devrait être accessible

### Tests Fonctionnels

1. **Test de recherche de joueur**
   - Dans l'interface, recherchez un joueur avec son tag (ex: `#2PP`)
   - Vérifiez que les statistiques s'affichent

2. **Test de l'AI Coach**
   - Ouvrez le chat AI
   - Envoyez un message
   - Vérifiez que l'IA répond

## 📊 Monitoring et Logs

### Accès aux Logs

Dans Jelastic:
1. Sélectionnez le nœud (Backend, Frontend, etc.)
2. Cliquez sur "Log" en haut
3. Les logs en temps réel s'affichent

### Logs Backend (FastAPI)
```bash
# Dans le nœud Backend
cat /app/logs/brawlgpt.log
```

### Logs PostgreSQL
```bash
# Dans le nœud PostgreSQL
tail -f /var/lib/postgresql/data/log/postgresql-*.log
```

### Métriques de Performance

Jelastic fournit des métriques automatiques:
- CPU Usage
- RAM Usage
- Network Traffic
- Disk I/O

Accédez-y via: "Statistics" dans votre environnement

## 🔧 Maintenance

### Mise à Jour de l'Application

#### Mise à jour du Backend

1. **Via Git**
   ```bash
   # Dans le gestionnaire de fichiers Jelastic
   cd /app
   git pull origin main
   ```

2. **Redémarrage**
   - Dans Jelastic, cliquez sur "Restart" pour le nœud Backend

#### Mise à jour du Frontend

1. **Rebuild**
   ```bash
   cd /app
   npm ci
   npm run build
   ```

2. **Redémarrage**
   - Redémarrez le nœud Frontend

### Sauvegarde de la Base de Données

#### Sauvegarde Manuelle

```bash
# Connectez-vous au nœud PostgreSQL via SSH
pg_dump -U brawl_user brawlgpt_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Sauvegarde Automatique

Créez un cron job dans Jelastic:

1. Allez dans "Settings" → "Cron"
2. Ajoutez:
   ```cron
   # Sauvegarde quotidienne à 3h du matin
   0 3 * * * pg_dump -U brawl_user brawlgpt_db > /backup/brawlgpt_$(date +\%Y\%m\%d).sql
   ```

#### Restauration

```bash
# Restaurer depuis une sauvegarde
psql -U brawl_user brawlgpt_db < backup_20260129.sql
```

### Mise à l'Échelle

#### Scaling Horizontal

Pour gérer plus de trafic:

1. **Backend**
   - Dans Jelastic, augmentez le nombre de nœuds Backend à 2 ou plus
   - Jelastic configure automatiquement le load balancing

2. **Frontend**
   - Peut être scalé de la même manière si nécessaire

#### Scaling Vertical

Pour augmenter les ressources d'un nœud:

1. Sélectionnez le nœud
2. Cliquez sur "Change Environment Topology"
3. Ajustez les cloudlets (1 cloudlet = 128 MB RAM + proportionnel CPU)

**Recommandations:**
- Backend: 1-8 flexCloudlets (128 MB - 1 GB)
- Frontend: 1-4 flexCloudlets (128 MB - 512 MB)
- PostgreSQL: 1-4 fixedCloudlets + 4 flexCloudlets
- Redis: 1-2 flexCloudlets

## 🛡️ Sécurité

### Bonnes Pratiques

1. **Changez le JWT Secret**
   - Ne gardez pas le secret par défaut
   - Utilisez un générateur sécurisé:
     ```bash
     openssl rand -base64 32
     ```

2. **Protégez les Clés API**
   - Ne commitez jamais les clés dans Git
   - Utilisez uniquement les variables d'environnement Jelastic

3. **CORS**
   - Configurez `ALLOWED_ORIGINS` pour n'autoriser que votre domaine

4. **Rate Limiting**
   - Déjà configuré dans le backend
   - Ajustez si nécessaire dans `config.py`

5. **Firewall**
   - Dans Jelastic, configurez les règles de firewall
   - Restreignez l'accès PostgreSQL et Redis aux nœuds internes uniquement

### SSL/TLS

- Jelastic active SSL automatiquement via Let's Encrypt
- Renouvelé automatiquement tous les 90 jours
- Pour forcer HTTPS, ajoutez dans Nginx:
  ```nginx
  if ($scheme != "https") {
      return 301 https://$server_name$request_uri;
  }
  ```

## 🔍 Dépannage

### Problème: Backend ne démarre pas

**Symptômes:** Erreur 502 Bad Gateway

**Solutions:**
1. Vérifiez les logs du Backend
2. Vérifiez que les clés API sont correctes
3. Vérifiez la connexion à PostgreSQL:
   ```bash
   psql -U brawl_user -h postgres-node -d brawlgpt_db
   ```

### Problème: Frontend affiche une page blanche

**Solutions:**
1. Vérifiez les logs Nginx
2. Vérifiez que `VITE_API_URL` pointe vers le bon domaine
3. Rebuild le frontend:
   ```bash
   cd /app && npm run build
   ```

### Problème: L'IA ne répond pas

**Solutions:**
1. Vérifiez la clé OpenRouter API
2. Vérifiez les logs Backend pour voir les erreurs API
3. Testez la connexion à OpenRouter:
   ```bash
   curl -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/models
   ```

### Problème: Base de données lente

**Solutions:**
1. Vérifiez l'utilisation des ressources de PostgreSQL
2. Augmentez les cloudlets si nécessaire
3. Optimisez les index:
   ```sql
   ANALYZE;
   VACUUM;
   ```

### Problème: Redis ne fonctionne pas

**Solutions:**
1. Vérifiez que Redis est démarré:
   ```bash
   redis-cli ping
   ```
2. Le backend peut fonctionner sans Redis (fallback en mémoire)
3. Redémarrez le nœud Redis

## 💰 Coûts Estimés

Sur Jelastic Infomaniak (estimation):

| Configuration | Cloudlets | Coût Mensuel Estimé |
|---------------|-----------|---------------------|
| **Minimal** | 10-12 | ~15-20 CHF/mois |
| Backend (2 flex) + Frontend (2 flex) + PostgreSQL (2 fixed + 2 flex) + Redis (1 flex) + Nginx (1 flex) | | |
| **Recommandé** | 16-20 | ~25-35 CHF/mois |
| Backend (4 flex) + Frontend (2 flex) + PostgreSQL (2 fixed + 4 flex) + Redis (2 flex) + Nginx (2 flex) | | |
| **Production** | 25-35 | ~45-60 CHF/mois |
| Backend (8 flex) x2 + Frontend (4 flex) + PostgreSQL (4 fixed + 8 flex) + Redis (4 flex) + Nginx (4 flex) | | |

*Note: Les coûts varient selon l'utilisation réelle*

## 📚 Ressources Supplémentaires

- [Documentation Jelastic](https://docs.jelastic.com/)
- [Support Infomaniak](https://www.infomaniak.com/fr/support)
- [BrawlGPT GitHub](https://github.com/votreusername/BrawlGPT)
- [API Brawl Stars](https://developer.brawlstars.com/api)
- [OpenRouter Documentation](https://openrouter.ai/docs)

## ❓ Support

En cas de problème:

1. **Documentation BrawlGPT**: Consultez le README.md
2. **Issues GitHub**: Ouvrez une issue sur le dépôt
3. **Support Jelastic**: Contactez l'équipe Infomaniak
4. **Communauté**: Rejoignez les discussions GitHub

---

**Bon déploiement! 🚀**

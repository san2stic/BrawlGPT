# Configuration Nginx sur Jelastic

## Problème
Le frontend est exposé directement sur le port 3000, mais on veut utiliser nginx comme reverse proxy sur le port 80.

## Solution : Exposer le service nginx

### Étape 1 : Vérifier les ports exposés

Sur Jelastic, connecte-toi en SSH et vérifie :

```bash
docker ps
```

Tu devrais voir :
- `brawlgpt-nginx` : nginx sur port 80
- `brawlgpt-frontend` : frontend (pas de port externe)
- `brawlgpt-backend` : backend (pas de port externe)

### Étape 2 : Modifier les endpoints Jelastic

Dans le panneau Jelastic :

1. **Ouvre ton environnement** BrawlGPT
2. **Clique sur "Settings"** (⚙️) pour ton node "dockerengine"
3. **Endpoints** → Modifie le mapping :
   - **Avant** : Port 80 → `frontend:3000`
   - **Après** : Port 80 → `nginx:80`

### Étape 3 : Restart nginx

```bash
docker-compose restart nginx
```

### Étape 4 : Tester

Accède à : `http://brawlgpt.jcloud-ver-jpe.ik-server.com`

**Sans `:3000` à la fin !**

## Architecture finale

```
Internet
    ↓
Jelastic (port 80)
    ↓
nginx:80
    ├── / → frontend:80 (React app)
    └── /api/ → backend:8000 (FastAPI)
```

## Alternative rapide : Modifier uniquement docker-compose

Si tu ne peux pas modifier les endpoints Jelastic, change le port nginx dans `docker-compose.yml` :

```yaml
nginx:
  ports:
    - "3000:80"  # Expose nginx sur le port 3000 au lieu de 80
```

Puis rebuild :
```bash
docker-compose down
docker-compose up -d
```

Maintenant `http://brawlgpt.jcloud-ver-jpe.ik-server.com:3000` pointe vers nginx qui route correctement !

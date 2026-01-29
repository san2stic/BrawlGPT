# Fix Frontend Healthcheck

Le frontend était unhealthy car le healthcheck utilisait `wget` qui n'est pas disponible dans `nginx:alpine`.

## Changements

✅ **docker-compose.yml** - Healthchecks mis à jour :
- Frontend : `wget` → `curl -f http://localhost:80/`
- Nginx : `wget` → `curl -f http://localhost:80/health`

## Pour redéployer

```bash
# Sur Jelastic
cd ~/BrawlGPT
docker-compose down
docker-compose up -d

# Vérifier le statut
docker ps
docker-compose ps
```

## Test du healthcheck

```bash
# Test manuel du healthcheck frontend
docker exec brawlgpt-frontend curl -f http://localhost:80/

# Test manuel du healthcheck nginx  
docker exec brawlgpt-nginx curl -f http://localhost:80/health
```

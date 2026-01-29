# Fix Applied - Hardcoded localhost URLs

## Problème Identifié ✅

Tu avais raison ! Le problème était bien **hardcodé** dans le code source.

Le frontend avait 3 fichiers avec des URLs hardcodées en fallback :

1. **`frontend/src/services/clubApi.ts`** (ligne 6)
2. **`frontend/src/hooks/useWebSocket.ts`** (ligne 26)  
3. **`frontend/src/components/GlobalMetaDashboard.tsx`** (ligne 45)

Tous utilisaient le pattern :
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

## Correctifs Appliqués ✅

### 1. clubApi.ts
```typescript
// AVANT
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// APRÈS
const API_BASE_URL = import.meta.env.VITE_API_URL || '';
```

### 2. GlobalMetaDashboard.tsx
```typescript
// AVANT
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// APRÈS
const API_BASE_URL = import.meta.env.VITE_API_URL || '';
```

### 3. useWebSocket.ts
```typescript
// AVANT
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

// APRÈS
const getWebSocketURL = () => {
    if (import.meta.env.VITE_WS_URL) {
        return import.meta.env.VITE_WS_URL;
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}`;
};
const WS_URL = getWebSocketURL();
```

## Prochaines Étapes

### Pour Déploiement Local
Tu peux continuer à utiliser `VITE_API_URL=http://localhost:8000` dans ton `.env` local.

### Pour Jelastic (déploiement manuel)

1. **Commit et push ces changements**:
   ```bash
   cd /Users/bastienjavaux/kDrive2/BrawlGPT
   git add .
   git commit -m "fix: remove hardcoded localhost URLs from frontend"
   git push
   ```

2. **SSH sur ton node frontend Jelastic** et rebuild :
   ```bash
   cd /tmp
   rm -rf brawlgpt
   git clone https://github.com/san2stic/BrawlGPT.git
   cd brawlgpt/frontend
   npm ci
   npm run build
   rm -rf /usr/share/nginx/html/*
   cp -r dist/* /usr/share/nginx/html/
   nginx -s reload
   cd /tmp
   rm -rf brawlgpt
   ```

3. **Vider le cache du navigateur** et recharger la page

4. **Accède via l'URL correcte** : `https://brawlgpt.icloud-ver.jpe.lk-server.com` (sans `:3000`)

## Résultat Attendu

- ✅ URLs API : `/api/player/...` (relative)
- ✅ URLs Meta : `/api/meta/global` (relative)  
- ✅ WebSocket : `wss://brawlgpt.icloud-ver.jpe.lk-server.com/ws/...`
- ✅ Plus d'erreurs `ERR_CONNECTION_REFUSED`

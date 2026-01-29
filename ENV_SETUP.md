# Environment Variables Configuration

## Required Variables

### SECRET_KEY (CRITICAL)
**Type:** String (minimum 32 characters)  
**Required:** YES  
**Purpose:** JWT token signing for authentication

> [!CAUTION]
> The application will **NOT start** without this variable. There is no default value for security reasons.

**How to generate:**
```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL
openssl rand -base64 32
```

### BRAWL_API_KEY
**Type:** String  
**Required:** YES  
**Purpose:** Brawl Stars API authentication

Get your API key from: https://developer.brawlstars.com

### OPENROUTER_API_KEY
**Type:** String  
**Required:** YES  
**Purpose:** AI model access via OpenRouter

Get your API key from: https://openrouter.ai/keys

## Database Configuration

### DATABASE_URL
**Type:** Connection String  
**Required:** YES  
**Default:** `postgresql+asyncpg://postgres:postgres@localhost:5432/brawlgpt_db`  
**Purpose:** PostgreSQL database connection

**Format:**
```
postgresql+asyncpg://user:password@host:port/database
```

## Redis Configuration

### REDIS_URL
**Type:** Connection String  
**Required:** NO  
**Default:** `redis://localhost:6379/0`  
**Purpose:** Distributed caching

### REDIS_ENABLED
**Type:**Boolean  
**Required:** NO  
**Default:** `true`  
**Purpose:** Enable/disable Redis caching (falls back to in-memory if disabled)

## Example .env File

```bash
# ===== REQUIRED VARIABLES =====

# Secret for JWT (GENERATE A SECURE VALUE!)
SECRET_KEY=your-secure-32-char-secret-key-here-change-this

# Brawl Stars API
BRAWL_API_KEY=your_brawl_stars_api_key_here

# OpenRouter AI
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/brawlgpt_db

# ===== OPTIONAL VARIABLES =====

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_ENABLED=true

# CORS Origins (comma-separated)
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Rate Limiting
RATE_LIMIT_PLAYER=30/minute
RATE_LIMIT_CHAT=10/minute

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# AI Configuration
AI_MODEL=anthropic/claude-sonnet-4.5
AI_MAX_TOKENS=2000
AI_TEMPERATURE=0.7

# Feature Flags
ENABLE_META_CRAWLER=true
ENABLE_PROGRESSION_TRACKING=true
ENABLE_AGENT_TOOLS=true
```

## Docker Setup

When using Docker Compose, create a `.env` file in the project root with the variables above. The docker-compose.yml file will automatically load them.

## Production Deployment

> [!IMPORTANT]
> **Never commit your `.env` file to version control!**

For production:
1. Generate a strong SECRET_KEY (different from development)
2. Use production database credentials
3. Set appropriate CORS origins
4. Consider setting LOG_FORMAT=json for better monitoring

## Verification

To verify your environment is configured correctly:

```bash
# Backend health check
curl http://localhost:8000/health/detailed

# Should return:
{
  "status": "healthy",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "brawl_stars_api": "configured"
  }
}
```

#!/bin/bash
set -e

echo "🔧 Rebuilding Frontend with Production Configuration..."
echo ""

# Navigate to project root
cd "$(dirname "$0")"

# Navigate to frontend directory
cd frontend

echo "📦 Building frontend with production API URL..."
echo "   API URL: http://brawlgpt.jcloud-ver-jpe.ik-server.com:8000"
echo ""

# Build with production environment
VITE_API_URL=http://brawlgpt.jcloud-ver-jpe.ik-server.com:8000 npm run build

echo ""
echo "✅ Frontend build complete!"
echo ""
echo "Next steps:"
echo "  1. Rebuild Docker images:  docker-compose build frontend"
echo "  2. Redeploy to Jelastic:    ./deploy-jelastic.sh"
echo ""

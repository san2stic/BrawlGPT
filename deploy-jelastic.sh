#!/bin/bash

# BrawlGPT Jelastic Deployment Helper Script
# This script helps you prepare and validate your deployment

set -e

echo "🎮 BrawlGPT Jelastic Deployment Helper"
echo "======================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists for local reference
check_env_file() {
    echo -n "Checking for backend/.env file... "
    if [ -f "backend/.env" ]; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} Not found (optional for Jelastic)"
        return 1
    fi
}

# Validate API keys format (basic check)
validate_api_keys() {
    echo ""
    echo "📋 API Keys Validation"
    echo "---------------------"
    
    if [ -f "backend/.env" ]; then
        source backend/.env 2>/dev/null || true
        
        # Check Brawl Stars API Key
        echo -n "Brawl Stars API Key: "
        if [ -n "$BRAWL_API_KEY" ] && [ "$BRAWL_API_KEY" != "your_brawl_stars_api_key_here" ]; then
            echo -e "${GREEN}✓${NC} Configured"
        else
            echo -e "${RED}✗${NC} Missing or default value"
            echo "   → Get your key at: https://developer.brawlstars.com"
        fi
        
        # Check OpenRouter API Key
        echo -n "OpenRouter API Key: "
        if [ -n "$OPENROUTER_API_KEY" ] && [ "$OPENROUTER_API_KEY" != "your_openrouter_api_key_here" ]; then
            echo -e "${GREEN}✓${NC} Configured"
        else
            echo -e "${RED}✗${NC} Missing or default value"
            echo "   → Get your key at: https://openrouter.ai"
        fi
    else
        echo -e "${YELLOW}⚠${NC} No .env file found. You'll need to configure API keys in Jelastic."
    fi
}

# Check if manifest.jps exists
check_manifest() {
    echo ""
    echo -n "Checking for manifest.jps... "
    if [ -f "manifest.jps" ]; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        echo "   → Error: manifest.jps not found!"
        return 1
    fi
}

# Validate manifest.jps syntax (basic YAML check)
validate_manifest() {
    echo -n "Validating manifest.jps syntax... "
    
    # Check if yq or python is available for YAML validation
    if command -v python3 &> /dev/null; then
        if python3 -c "import yaml; yaml.safe_load(open('manifest.jps'))" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
            return 0
        else
            echo -e "${RED}✗${NC}"
            echo "   → YAML syntax error in manifest.jps"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠${NC} Cannot validate (python3 not found)"
        return 0
    fi
}

# Check Docker images accessibility
check_docker_images() {
    echo ""
    echo "🐳 Docker Images Check"
    echo "---------------------"
    
    if command -v docker &> /dev/null; then
        images=("postgres:15-alpine" "redis:7-alpine" "python:3.12-slim" "node:20-alpine")
        
        for image in "${images[@]}"; do
            echo -n "Checking $image... "
            if docker pull $image --quiet &> /dev/null; then
                echo -e "${GREEN}✓${NC}"
            else
                echo -e "${YELLOW}⚠${NC} Could not pull (Jelastic will handle this)"
            fi
        done
    else
        echo -e "${YELLOW}⚠${NC} Docker not installed locally (not required for Jelastic)"
    fi
}

# Generate deployment checklist
generate_checklist() {
    echo ""
    echo "📝 Deployment Checklist"
    echo "======================="
    cat << EOF

Before deploying to Jelastic, ensure you have:

 ☐ Jelastic Infomaniak account (https://jelastic.infomaniak.com)
 ☐ Brawl Stars API Key (https://developer.brawlstars.com)
 ☐ OpenRouter API Key (https://openrouter.ai)
 ☐ manifest.jps file ready
 ☐ (Optional) Custom domain name configured in DNS

Deployment Steps:
 1. Log in to Jelastic Infomaniak
 2. Click "Import" → "Local file" or "URL"
 3. Upload or link to manifest.jps
 4. Fill in the configuration form with your API keys
 5. Click "Install" and wait for deployment
 6. Access your application at the provided URL
 7. Test the application:
    - Visit the homepage
    - Search for a Brawl Stars player
    - Test the AI chat feature

For detailed instructions, see: JELASTIC_DEPLOYMENT.md

EOF
}

# Estimate resource requirements
estimate_resources() {
    echo ""
    echo "💰 Resource Estimation"
    echo "====================="
    cat << EOF

Recommended Jelastic Configuration:

Node            | Fixed Cloudlets | Flex Cloudlets | Description
----------------|-----------------|----------------|------------------
Backend         | 0               | 4-8            | FastAPI application
Frontend        | 0               | 2-4            | React + Nginx
PostgreSQL      | 2               | 4              | Database
Redis           | 0               | 2              | Cache
Nginx           | 0               | 2              | Reverse proxy
----------------|-----------------|----------------|------------------
TOTAL           | 2               | 14-20          | 

Estimated Monthly Cost: 25-35 CHF (depending on usage)

Note: Cloudlets scale automatically based on usage
      1 cloudlet = 128 MB RAM + proportional CPU

EOF
}

# Main execution
main() {
    check_env_file
    validate_api_keys
    
    if ! check_manifest; then
        echo ""
        echo -e "${RED}ERROR: manifest.jps file is missing!${NC}"
        exit 1
    fi
    
    validate_manifest
    check_docker_images
    estimate_resources
    generate_checklist
    
    echo ""
    echo -e "${GREEN}✅ Pre-deployment checks complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review JELASTIC_DEPLOYMENT.md for detailed instructions"
    echo "  2. Prepare your API keys"
    echo "  3. Deploy to Jelastic: https://jelastic.infomaniak.com"
    echo ""
    echo "Good luck with your deployment! 🚀"
}

# Run main function
main

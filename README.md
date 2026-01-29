# BrawlGPT 🎮

AI-powered coaching and statistics for Brawl Stars players.

## Features

- 🔍 **Player Search**: Look up any player by their tag
- 📊 **Detailed Statistics**: View trophies, victories, and brawler data
- 🤖 **AI Coach**: Get personalized tips and insights from an AI coach
- ⚡ **Fast Performance**: Built-in caching for quick responses
- 🔒 **Secure**: Rate limiting and input validation

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **OpenRouter** - AI model access (Gemini 2.0 Flash)
- **Pydantic** - Data validation
- **SlowAPI** - Rate limiting
- **Cachetools** - In-memory caching

### Frontend
- **React 19** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **TailwindCSS** - Styling

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Brawl Stars API key ([Get one here](https://developer.brawlstars.com))
- OpenRouter API key ([Get one here](https://openrouter.ai))

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Run development server
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Run development server
npm run dev
```

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Access the app at http://localhost:3000
```

## Jelastic Deployment (Infomaniak)

### One-Click Deploy

Deploy BrawlGPT to Jelastic Infomaniak with one click:

[![Deploy to Jelastic](https://jelastic.com/wp-content/themes/salient/assets/img/deploy-to-jelastic.png)](https://jelastic.infomaniak.com?manifest=https://raw.githubusercontent.com/yourusername/BrawlGPT/main/manifest.jps)

### Requirements

- Jelastic Infomaniak account ([Sign up here](https://jelastic.infomaniak.com))
- Brawl Stars API Key ([Get one here](https://developer.brawlstars.com))
- OpenRouter API Key ([Get one here](https://openrouter.ai))

### Detailed Instructions

For complete deployment instructions, configuration, and troubleshooting, see [JELASTIC_DEPLOYMENT.md](./JELASTIC_DEPLOYMENT.md).


## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Detailed health status |
| `/api/player/{tag}` | GET | Get player stats and AI insights |
| `/api/v1/player/{tag}` | GET | API v1 endpoint |
| `/api/cache/stats` | GET | Cache statistics |
| `/api/cache/{tag}` | DELETE | Clear player cache |

## Environment Variables

### Backend
| Variable | Description | Required |
|----------|-------------|----------|
| `BRAWL_API_KEY` | Brawl Stars API key | Yes |
| `OPENROUTER_API_KEY` | OpenRouter API key | Yes |
| `ALLOWED_ORIGINS` | CORS allowed origins | No |

### Frontend
| Variable | Description | Required |
|----------|-------------|----------|
| `VITE_API_URL` | Backend API URL | No (defaults to localhost:8000) |

## Development

### Running Tests

```bash
# Backend tests
cd backend
pip install -r requirements-dev.txt
pytest

# With coverage
pytest --cov=. --cov-report=html
```

### Code Quality

```bash
# Backend
ruff check .       # Linting
black .            # Formatting
mypy .             # Type checking

# Frontend
npm run lint       # ESLint
npm run type-check # TypeScript
```

## Project Structure

```
BrawlGPT/
├── backend/
│   ├── main.py           # FastAPI application
│   ├── agent.py          # AI coaching agent
│   ├── brawlstars.py     # Brawl Stars API client
│   ├── cache.py          # Caching layer
│   ├── exceptions.py     # Custom exceptions
│   ├── models.py         # Pydantic models
│   ├── tests/            # Backend tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom hooks
│   │   ├── services/     # API services
│   │   ├── types/        # TypeScript types
│   │   ├── App.tsx       # Main app
│   │   └── main.tsx      # Entry point
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml
└── README.md
```

## License

MIT

## Disclaimer

This project is not affiliated with, endorsed by, or in any way officially connected to Supercell or Brawl Stars.

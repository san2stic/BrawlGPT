"""
BrawlGPT Backend API.
FastAPI application providing player stats, AI coaching insights, and meta analysis.
"""

import os
import time
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Any, Callable, Optional

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime

# Configuration and Logging
from config import settings
from logging_config import (
    setup_logging, 
    get_request_logger, 
    LogContext,
    request_id_ctx
)

# Services and Clients
from database import init_db, get_db, AsyncSessionLocal
from brawlstars import BrawlStarsClient
from agent import AIAgent
from cache_redis import redis_cache
from services.meta_collector import MetaCollectorService
from services.global_meta_aggregator import GlobalMetaAggregatorService
from services.synergy_analyzer import SynergyAnalyzerService
from services.trend_detector import TrendDetectorService
from analyzer import PlayerAnalyzer
from ai_analyst import MetaAnalyst

# Routers
from routers import users, crawler, scheduler
# derived exceptions
from exceptions import BrawlGPTError, InvalidTagError
from models import ChatRequest

# Initialize logging FIRST
setup_logging(
    level=settings().log_level,
    format_type=settings().log_format,
    extra_fields={"app": settings().app_name, "env": "production"}
)
logger = logging.getLogger(__name__)
request_logger = get_request_logger()

# Global Clients
brawl_client = BrawlStarsClient(settings().brawl_api_key)
ai_agent = AIAgent(settings().openrouter_api_key)
meta_analyst = MetaAnalyst(settings().openrouter_api_key)

# Meta Collection Services
meta_collector = MetaCollectorService(
    brawl_client=brawl_client,
    interval_hours=settings().meta_collection_interval_hours,
    max_players_per_range=settings().meta_max_players_per_range
)

# Global Meta Intelligence Services
global_meta_aggregator = GlobalMetaAggregatorService(
    ai_analyst=meta_analyst,
    interval_minutes=settings().global_meta_interval_minutes
)

synergy_analyzer = SynergyAnalyzerService(
    interval_hours=settings().synergy_analysis_interval_hours
)

trend_detector = TrendDetectorService(
    ai_analyst=meta_analyst,
    interval_hours=settings().trend_detection_interval_hours,
    min_confidence=settings().ai_min_confidence_threshold
)

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Manages startup and shutdown of services.
    """
    logger.info("BrawlGPT API starting up...")
    
    # 1. Initialize Database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}")
    
    # 2. Connect Redis
    await redis_cache.connect()
    
    # 3. Start Meta Collector
    if settings().enable_meta_crawler:
        await meta_collector.start(AsyncSessionLocal)
    
    # 4. Start Global Meta Intelligence Services
    if settings().enable_global_meta_aggregation:
        await global_meta_aggregator.start(AsyncSessionLocal)
        logger.info("Global meta aggregator started")
    
    if settings().enable_synergy_analysis:
        await synergy_analyzer.start(AsyncSessionLocal)
        logger.info("Synergy analyzer started")
    
    if settings().enable_trend_detection:
        await trend_detector.start(AsyncSessionLocal)
        logger.info("Trend detector started")
    
    yield
    
    # Shutdown
    logger.info("BrawlGPT API shutting down...")
    
    # 1. Stop Intelligence Services
    await global_meta_aggregator.stop()
    await synergy_analyzer.stop()
    await trend_detector.stop()
    
    # 2. Stop Meta Collector
    await meta_collector.stop()
    
    # 3. Disconnect Redis
    await redis_cache.disconnect()


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings().app_name,
        description="AI-powered Brawl Stars coaching and statistics",
        version=settings().app_version,
        lifespan=lifespan
    )
    
    # Configure Rate Limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings().cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Register Routers
    app.include_router(users.router)
    app.include_router(crawler.router)
    app.include_router(scheduler.router)
    
    return app

app = create_application()


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware for structured request logging.
    Sets request_id and logs timing metrics.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.time()
    
    # Set context vars
    token = request_id_ctx.set(request_id)
    
    # Helper to get client IP safely
    client_ip = request.client.host if request.client else "unknown"
    
    request_logger.log_request_start(
        method=request.method,
        path=request.url.path,
        request_id=request_id,
        client_ip=client_ip,
        user_agent=request.headers.get("user-agent")
    )
    
    try:
        response = await call_next(request)
        
        duration = (time.time() - start_time) * 1000
        request_logger.log_request_complete(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration,
            request_id=request_id
        )
        
        # Add Request-ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.exception(f"Unhandled exception processing request {request_id}")
        request_logger.log_request_complete(
            method=request.method,
            path=request.url.path,
            status_code=500,
            duration_ms=duration,
            request_id=request_id
        )
        raise e
    finally:
        request_id_ctx.reset(token)


@app.exception_handler(BrawlGPTError)
async def brawlgpt_error_handler(request: Request, exc: BrawlGPTError) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.warning(f"BrawlGPT error: {exc.message} (status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message, 
            "error_type": exc.__class__.__name__,
            "request_id": request_id_ctx.get()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "request_id": request_id_ctx.get()
        }
    )


@app.get("/health")
def health_check_simple() -> dict[str, str]:
    """Simple health check for Docker."""
    return {"status": "healthy"}

@app.get("/")
def read_root() -> dict[str, Any]:
    """Root endpoint."""
    return {
        "status": "healthy",
        "message": f"{settings().app_name} API is running",
        "version": settings().app_version
    }


@app.get("/health/detailed")
async def health_check_detailed(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Detailed health check of all dependencies.
    Checks: Database, Redis, Brawl Stars API (connectivity).
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
        "cache": await redis_cache.get_stats()
    }
    
    # Check Database
    try:
        await db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
        
    # Check Redis
    if not health_status["cache"].get("connected", False) and settings().redis_enabled:
         health_status["services"]["redis"] = "disconnected"
         health_status["status"] = "degraded"
    else:
         health_status["services"]["redis"] = "healthy"

    # Check Brawl Stars API key presence
    if settings().brawl_api_key:
        health_status["services"]["brawl_stars_api"] = "configured"
    else:
        health_status["services"]["brawl_stars_api"] = "missing_key"
        health_status["status"] = "unhealthy"

    return health_status


# =============================================================================
# PLAYER ENDPOINTS (Restored from original main.py)
# =============================================================================

@app.get("/api/player/{tag}")
@limiter.limit(settings().rate_limit_player)
async def get_player_stats(request: Request, tag: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Fetch player statistics and generate AI coaching insights.
    Uses distributed Redis cache.
    """
    logger.info(f"Received request for player tag: {tag}")

    # Validate tag format
    try:
        clean_tag = BrawlStarsClient.validate_tag(tag)
    except InvalidTagError as e:
        logger.warning(f"Invalid tag format: {tag}")
        raise HTTPException(status_code=400, detail=str(e.message))

    try:
        # 1. Player Data
        player_data = await redis_cache.get_player(clean_tag)
        if player_data is None:
            logger.info(f"Cache miss - fetching player data for: {clean_tag}")
            player_data = brawl_client.get_player(clean_tag)
            await redis_cache.set_player(clean_tag, player_data)
        else:
            logger.info(f"Cache hit - using cached player data for: {clean_tag}")

        # 2. Battle Log
        battle_log = await redis_cache.get_battle_log(clean_tag)
        if battle_log is None:
            logger.info(f"Cache miss - fetching battle log for: {clean_tag}")
            battle_log = brawl_client.get_battle_log(clean_tag)
            await redis_cache.set_battle_log(clean_tag, battle_log)
        else:
            logger.info(f"Cache hit - using cached battle log for: {clean_tag}")

        # 3. AI Insights
        insights = await redis_cache.get_insights(clean_tag, player_data)
        if insights is None:
            logger.info(f"Cache miss - generating AI insights for: {clean_tag}")
            # Ensure we are passing DB if needed by analyze_profile
            insights = await ai_agent.analyze_profile(player_data, battle_log, db=db)
            await redis_cache.set_insights(clean_tag, player_data, insights)
        else:
            logger.info(f"Cache hit - using cached insights for: {clean_tag}")

        return {
            "player": player_data,
            "battles": battle_log,
            "insights": insights
        }

    except BrawlGPTError:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing request for tag {tag}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.get("/api/player/{tag}/connections")
@limiter.limit(settings().rate_limit_player)
async def get_player_connections(request: Request, tag: str) -> dict[str, Any]:
    """
    Analyze player connections and social graph.
    """
    try:
        clean_tag = BrawlStarsClient.validate_tag(tag)
        
        # Get battle log (prefer cache)
        battle_log = await redis_cache.get_battle_log(clean_tag)
        if battle_log is None:
            battle_log = brawl_client.get_battle_log(clean_tag)
            await redis_cache.set_battle_log(clean_tag, battle_log)
            
        # Analysis
        analysis = PlayerAnalyzer.analyze_connections(clean_tag, battle_log)
        
        # Player basic info
        player_data = await redis_cache.get_player(clean_tag)
        if not player_data:
             player_data = brawl_client.get_player(clean_tag)
             await redis_cache.set_player(clean_tag, player_data)
             
        return {
            "player": {
                "name": player_data.get('name'),
                "tag": player_data.get('tag'),
                "icon": player_data.get('icon', {}).get('id')
            },
            "analysis": analysis
        }
    except InvalidTagError as e:
        raise HTTPException(status_code=400, detail=str(e.message))
    except Exception as e:
        logger.exception(f"Error analyzing connections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/player/{tag}")
@limiter.limit(settings().rate_limit_player)
async def get_player_stats_v1(request: Request, tag: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """API v1 endpoint - alias for /api/player/{tag}."""
    return await get_player_stats(request, tag, db)


@app.delete("/api/cache/{tag}")
@limiter.limit(settings().rate_limit_cache)
async def clear_player_cache(request: Request, tag: str) -> dict[str, str]:
    """Clear cached data for a specific player."""
    try:
        clean_tag = BrawlStarsClient.validate_tag(tag)
        await redis_cache.clear_player(clean_tag)
        return {"message": f"Cache cleared for player: {clean_tag}"}
    except InvalidTagError as e:
        raise HTTPException(status_code=400, detail=str(e.message))


@app.post("/api/chat")
@limiter.limit(settings().rate_limit_chat)
async def chat_with_agent(
    request: Request, 
    chat_request: ChatRequest, 
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """Chat with the AI agent."""
    try:
        messages = [m.model_dump() for m in chat_request.messages]
        response = await ai_agent.chat(messages, chat_request.player_context, db=db)
        return {"response": response}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cache/stats")
async def get_cache_stats_endpoint() -> dict[str, Any]:
    """Get cache statistics."""
    return await redis_cache.get_stats()


# =============================================================================
# GLOBAL META INTELLIGENCE ENDPOINTS
# =============================================================================

@app.get("/api/meta/global")
@limiter.limit(settings().rate_limit_player)
async def get_global_meta(request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Get the latest global meta statistics.
    Provides aggregated data across all trophy ranges.
    """
    try:
        aggregate = await global_meta_aggregator.get_latest_global_meta(db)
        
        if not aggregate:
            raise HTTPException(
                status_code=404,
                detail="No global meta data available yet. Check back soon."
            )
        
        return {
            "timestamp": aggregate.timestamp.isoformat(),
            "total_battles": aggregate.total_battles_analyzed,
            "total_players": aggregate.total_unique_players,
            "data": aggregate.data,
            "ai_insights": aggregate.ai_insights,
            "ai_generated_at": aggregate.ai_generated_at.isoformat() if aggregate.ai_generated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching global meta: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch global meta")


@app.get("/api/meta/synergies/{brawler_id}")
@limiter.limit(settings().rate_limit_player)
async def get_brawler_synergies(
    request: Request,
    brawler_id: int,
    min_quality: str = "medium",
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get the best synergies for a specific brawler.
    
    Args:
        brawler_id: ID of the brawler
        min_quality: Minimum data quality ('low', 'medium', 'high')
        limit: Maximum number of results
    """
    try:
        synergies = await synergy_analyzer.get_brawler_synergies(
            db, brawler_id, min_quality, limit
        )
        
        # Convert to dict
        synergy_list = []
        for s in synergies:
            # Determine partner brawler
            partner_id = s.brawler_b_id if s.brawler_a_id == brawler_id else s.brawler_a_id
            partner_name = s.brawler_b_name if s.brawler_a_id == brawler_id else s.brawler_a_name
            
            synergy_list.append({
                "partner_id": partner_id,
                "partner_name": partner_name,
                "win_rate": s.win_rate,
                "games_together": s.games_together,
                "avg_trophy_change": s.avg_trophy_change,
                "best_modes": s.best_modes,
                "data_quality": s.sample_size_quality
            })
        
        # Generate AI analysis if we have data
        ai_analysis = await meta_analyst.analyze_brawler_synergies(
            [
                {
                    "brawler_a_name": s.brawler_a_name,
                    "brawler_b_name": s.brawler_b_name,
                    "win_rate": s.win_rate,
                    "games_together": s.games_together,
                    "sample_size_quality": s.sample_size_quality
                }
                for s in synergies
            ],
            brawler_name=synergies[0].brawler_a_name if synergies and synergies[0].brawler_a_id == brawler_id else (
                synergies[0].brawler_b_name if synergies else None
            )
        ) if synergies else "No synergy data available"
        
        return {
            "brawler_id": brawler_id,
            "synergies": synergy_list,
            "ai_analysis": ai_analysis
        }
    except Exception as e:
        logger.error(f"Error fetching synergies: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch synergies")


@app.get("/api/meta/trends")
@limiter.limit(settings().rate_limit_player)
async def get_meta_trends(
    request: Request,
    days: int = 7,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get meta trends over the specified time period.
    
    Args:
        days: Number of days to look back (default: 7)
    """
    try:
        # Get trending brawlers
        rising = await trend_detector.get_trending_brawlers(
            db, direction="rising", min_strength=0.2, limit=10
        )
        falling = await trend_detector.get_trending_brawlers(
            db, direction="falling", min_strength=0.2, limit=10
        )
        
        rising_list = [{
            "brawler_id": t.brawler_id,
            "brawler_name": t.brawler_name,
            "win_rate": t.win_rate,
            "pick_rate": t.pick_rate,
            "trend_strength": t.trend_strength,
            "popularity_rank": t.popularity_rank
        } for t in rising]
        
        falling_list = [{
            "brawler_id": t.brawler_id,
            "brawler_name": t.brawler_name,
            "win_rate": t.win_rate,
            "pick_rate": t.pick_rate,
            "trend_strength": t.trend_strength,
            "popularity_rank": t.popularity_rank
        } for t in falling]
        
        return {
            "rising_brawlers": rising_list,
            "falling_brawlers": falling_list,
            "period_days": days
        }
    except Exception as e:
        logger.error(f"Error fetching trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trends")


@app.get("/api/meta/insights")
@limiter.limit(settings().rate_limit_player)
async def get_ai_insights(
    request: Request,
    insight_type: Optional[str] = None,
    days: int = 7,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get AI-generated meta insights.
    
    Args:
        insight_type: Optional filter by type ('brawler_rise', 'brawler_fall', 'meta_shift', etc.)
        days: Number of days to look back
        limit: Maximum number of results
    """
    try:
        insights = await trend_detector.get_recent_insights(
            db, insight_type=insight_type, days=days, limit=limit
        )
        
        insight_list = [{
            "id": i.id,
            "timestamp": i.timestamp.isoformat(),
            "type": i.insight_type,
            "title": i.title,
            "content": i.content,
            "confidence": i.confidence_score,
            "impact": i.impact_level,
            "data": i.data
        } for i in insights]
        
        return {
            "insights": insight_list,
            "count": len(insight_list),
            "filter": insight_type
        }
    except Exception as e:
        logger.error(f"Error fetching insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch insights")

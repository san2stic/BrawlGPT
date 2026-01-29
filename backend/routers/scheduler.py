"""
Game Scheduler Router.
Handles AI-generated personalized game schedules.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc
from pydantic import BaseModel

from database import get_db
from db_models import User, GameSchedule, ScheduleEvent
from auth import get_current_user
from brawlstars import BrawlStarsClient
from agent import AIAgent
from config import settings
from cache_redis import redis_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedule", tags=["scheduler"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ScheduleRequest(BaseModel):
    """Request model for generating a new schedule."""
    schedule_type: str = "weekly"  # "weekly", "trophy_push", "brawler_mastery"
    duration_days: int = 7
    goals: List[str] = []
    focus_brawlers: List[str] = []


class EventResponse(BaseModel):
    """Response model for a calendar event."""
    id: int
    title: str
    start: str  # ISO datetime
    end: str
    event_type: str
    recommended_brawler: Optional[str] = None
    recommended_mode: Optional[str] = None
    recommended_map: Optional[str] = None
    notes: Optional[str] = None
    priority: str
    color: Optional[str] = None


class ScheduleResponse(BaseModel):
    """Response model for a complete schedule."""
    id: int
    player_tag: str  # Player tag this schedule was created for
    player_name: Optional[str] = None  # Player name from API
    schedule_type: str
    duration_days: int
    description: str
    goals: List[str]
    created_at: str
    events: List[EventResponse]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/generate", response_model=ScheduleResponse)
async def generate_schedule(
    request: ScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a personalized game schedule using AI.
    Requires authentication and a claimed Brawl Stars profile.
    """
    if not current_user.brawl_stars_tag:
        raise HTTPException(
            status_code=400,
            detail="You must claim a Brawl Stars profile before generating a schedule"
        )

    try:
        # Get player data
        player_tag = current_user.brawl_stars_tag
        brawl_client = BrawlStarsClient(settings().brawl_api_key)
        
        # Try to get from cache first
        player_data = await redis_cache.get_player(player_tag)
        if not player_data:
            player_data = brawl_client.get_player(player_tag)
            await redis_cache.set_player(player_tag, player_data)

        # Get battle log
        battle_log = await redis_cache.get_battle_log(player_tag)
        if not battle_log:
            battle_log = brawl_client.get_battle_log(player_tag)
            await redis_cache.set_battle_log(player_tag, battle_log)

        # Initialize AI agent
        ai_agent = AIAgent(settings().openrouter_api_key, brawl_client=brawl_client)

        # Generate schedule using AI
        logger.info(f"Generating {request.schedule_type} schedule for user {current_user.id}")
        schedule_data = await ai_agent.generate_game_schedule(
            player_data=player_data,
            battle_log=battle_log,
            schedule_type=request.schedule_type,
            duration_days=request.duration_days,
            goals=request.goals,
            focus_brawlers=request.focus_brawlers
        )

        # Create schedule in database
        new_schedule = GameSchedule(
            user_id=current_user.id,
            player_tag=player_tag,
            schedule_type=request.schedule_type,
            duration_days=request.duration_days,
            description=schedule_data.get("description", ""),
            goals=request.goals or []
        )
        db.add(new_schedule)
        await db.flush()  # Get the schedule ID

        # Create events
        events_response = []
        for event_data in schedule_data.get("events", []):
            event = ScheduleEvent(
                schedule_id=new_schedule.id,
                start_time=datetime.fromisoformat(event_data["start"]),
                end_time=datetime.fromisoformat(event_data["end"]),
                title=event_data["title"],
                event_type=event_data.get("event_type", "practice"),
                recommended_brawler=event_data.get("recommended_brawler"),
                recommended_mode=event_data.get("recommended_mode"),
                recommended_map=event_data.get("recommended_map"),
                notes=event_data.get("notes"),
                priority=event_data.get("priority", "medium"),
                color=event_data.get("color")
            )
            db.add(event)
            
            events_response.append(EventResponse(
                id=0,  # Will be set after commit
                title=event.title,
                start=event.start_time.isoformat(),
                end=event.end_time.isoformat(),
                event_type=event.event_type,
                recommended_brawler=event.recommended_brawler,
                recommended_mode=event.recommended_mode,
                recommended_map=event.recommended_map,
                notes=event.notes,
                priority=event.priority,
                color=event.color
            ))

        await db.commit()
        await db.refresh(new_schedule)

        # Update events with real IDs
        for i, event in enumerate(new_schedule.events):
            events_response[i].id = event.id

        logger.info(f"Successfully created schedule {new_schedule.id} with {len(events_response)} events")

        return ScheduleResponse(
            id=new_schedule.id,
            player_tag=player_tag,
            player_name=player_data.get("name", ""),
            schedule_type=new_schedule.schedule_type,
            duration_days=new_schedule.duration_days,
            description=new_schedule.description,
            goals=new_schedule.goals,
            created_at=new_schedule.created_at.isoformat(),
            events=events_response
        )

    except Exception as e:
        logger.error(f"Failed to generate schedule: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to generate schedule: {str(e)}")


@router.get("/current", response_model=Optional[ScheduleResponse])
async def get_current_schedule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the user's most recent active schedule.
    Returns None if no schedule exists.
    """
    try:
        # Get the most recent schedule for this user
        stmt = select(GameSchedule).where(
            GameSchedule.user_id == current_user.id
        ).order_by(desc(GameSchedule.created_at)).limit(1)

        result = await db.execute(stmt)
        schedule = result.scalars().first()

        if not schedule:
            return None

        # Get events for this schedule
        events_stmt = select(ScheduleEvent).where(
            ScheduleEvent.schedule_id == schedule.id
        ).order_by(ScheduleEvent.start_time)

        events_result = await db.execute(events_stmt)
        events = events_result.scalars().all()

        events_response = [
            EventResponse(
                id=event.id,
                title=event.title,
                start=event.start_time.isoformat(),
                end=event.end_time.isoformat(),
                event_type=event.event_type,
                recommended_brawler=event.recommended_brawler,
                recommended_mode=event.recommended_mode,
                recommended_map=event.recommended_map,
                notes=event.notes,
                priority=event.priority,
                color=event.color
            )
            for event in events
        ]

        return ScheduleResponse(
            id=schedule.id,
            player_tag=schedule.player_tag,
            player_name=None,  # Not fetched in this endpoint for performance
            schedule_type=schedule.schedule_type,
            duration_days=schedule.duration_days,
            description=schedule.description,
            goals=schedule.goals,
            created_at=schedule.created_at.isoformat(),
            events=events_response
        )

    except Exception as e:
        logger.error(f"Failed to retrieve schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve schedule")


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a schedule and all its events.
    Only the schedule owner can delete it.
    """
    try:
        # Check if schedule exists and belongs to user
        stmt = select(GameSchedule).where(
            GameSchedule.id == schedule_id,
            GameSchedule.user_id == current_user.id
        )
        result = await db.execute(stmt)
        schedule = result.scalars().first()

        if not schedule:
            raise HTTPException(
                status_code=404,
                detail="Schedule not found or you don't have permission to delete it"
            )

        # Delete schedule (events will be cascade deleted)
        await db.delete(schedule)
        await db.commit()

        logger.info(f"Deleted schedule {schedule_id} for user {current_user.id}")

        return {"message": "Schedule deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete schedule: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete schedule")


@router.get("/all", response_model=List[ScheduleResponse])
async def get_all_schedules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all schedules for the current user.
    """
    try:
        stmt = select(GameSchedule).where(
            GameSchedule.user_id == current_user.id
        ).order_by(desc(GameSchedule.created_at))

        result = await db.execute(stmt)
        schedules = result.scalars().all()

        schedules_response = []
        for schedule in schedules:
            # Get events for each schedule
            events_stmt = select(ScheduleEvent).where(
                ScheduleEvent.schedule_id == schedule.id
            ).order_by(ScheduleEvent.start_time)

            events_result = await db.execute(events_stmt)
            events = events_result.scalars().all()

            events_response = [
                EventResponse(
                    id=event.id,
                    title=event.title,
                    start=event.start_time.isoformat(),
                    end=event.end_time.isoformat(),
                    event_type=event.event_type,
                    recommended_brawler=event.recommended_brawler,
                    recommended_mode=event.recommended_mode,
                    recommended_map=event.recommended_map,
                    notes=event.notes,
                    priority=event.priority,
                    color=event.color
                )
                for event in events
            ]

            schedules_response.append(ScheduleResponse(
                id=schedule.id,
                player_tag=schedule.player_tag,
                player_name=None,  # Not fetched in this endpoint for performance
                schedule_type=schedule.schedule_type,
                duration_days=schedule.duration_days,
                description=schedule.description,
                goals=schedule.goals,
                created_at=schedule.created_at.isoformat(),
                events=events_response
            ))

        return schedules_response

    except Exception as e:
        logger.error(f"Failed to retrieve schedules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve schedules")

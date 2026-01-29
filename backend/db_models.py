"""
Database models for BrawlGPT.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, ForeignKey, Boolean,
    Float, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from database import Base


class Interaction(Base):
    """
    Stores chat interactions between user and AI agent.
    Used to provide context for future conversations.
    """
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    player_tag = Column(String, index=True)
    input_message = Column(Text)  # User's message (JSON string or plain text)
    output_message = Column(Text) # AI's response
    

class Insight(Base):
    """
    Stores generated AI insights for players.
    can be used to track progress over time.
    """
    __tablename__ = "insights"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    player_tag = Column(String, index=True)
    content = Column(Text) # The generated markdown insight


class User(Base):
    """
    User account for the application.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    # Profile link
    brawl_stars_tag = Column(String, nullable=True) # The primary tag invoked by the user

    # Relationships

    # Users can have many claimed or saved players (optional for now, let's stick to one main tag)
    # But for now, we just link interaction history to the user if logged in


# =============================================================================
# META ANALYSIS MODELS
# =============================================================================

class MetaSnapshot(Base):
    """
    Snapshot of the meta at a specific point in time for a trophy range.
    Collected periodically by the meta collector service.
    """
    __tablename__ = "meta_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    trophy_range_min = Column(Integer, index=True)
    trophy_range_max = Column(Integer, index=True)
    sample_size = Column(Integer)  # Number of battles analyzed

    # Aggregated data stored as JSON
    data = Column(JSON)  # {"overall_stats": {...}, "mode_breakdown": {...}}

    # Relationship to brawler stats
    brawler_stats = relationship("BrawlerMeta", back_populates="snapshot", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_snapshot_trophy_range', 'trophy_range_min', 'trophy_range_max'),
    )


class BrawlerMeta(Base):
    """
    Meta statistics for a specific brawler within a meta snapshot.
    """
    __tablename__ = "brawler_meta"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("meta_snapshots.id", ondelete="CASCADE"), index=True)

    # Brawler identification
    brawler_id = Column(Integer, index=True)
    brawler_name = Column(String(50))

    # Performance metrics
    pick_rate = Column(Float)  # Percentage of games this brawler appears
    win_rate = Column(Float)   # Win rate percentage
    avg_trophies_change = Column(Float)  # Average trophy change per game

    # Mode and map performance (JSON)
    best_modes = Column(JSON)  # [{"mode": "gemGrab", "win_rate": 58.5}, ...]
    best_maps = Column(JSON)   # [{"map": "Hard Rock Mine", "win_rate": 62.0}, ...]

    # Relationship
    snapshot = relationship("MetaSnapshot", back_populates="brawler_stats")

    __table_args__ = (
        UniqueConstraint('snapshot_id', 'brawler_id', name='uq_snapshot_brawler'),
    )


class PlayerHistory(Base):
    """
    Historical progression data for a player.
    Used to track improvement over time.
    """
    __tablename__ = "player_history"

    id = Column(Integer, primary_key=True, index=True)
    player_tag = Column(String(20), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Trophy data
    trophies = Column(Integer)
    highest_trophies = Column(Integer)

    # Brawler count
    brawler_count = Column(Integer)

    # Victory counts
    victories_3v3 = Column(Integer)
    solo_victories = Column(Integer)
    duo_victories = Column(Integer)

    # Experience
    exp_level = Column(Integer)

    # Club info (optional)
    club_name = Column(String(100), nullable=True)
    club_tag = Column(String(20), nullable=True)

    __table_args__ = (
        Index('idx_player_history_tag_time', 'player_tag', 'timestamp'),
    )


# =============================================================================
# CONVERSATION MEMORY MODELS
# =============================================================================

class ConversationMemory(Base):
    """
    Long-term memory for conversations with players.
    Stores key points and topics discussed to provide context continuity.
    """
    __tablename__ = "conversation_memory"

    id = Column(Integer, primary_key=True, index=True)
    player_tag = Column(String(20), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Conversation categorization
    topic = Column(String(50))  # "brawler_advice", "mode_strategy", "general", etc.

    # Key information extracted
    key_points = Column(JSON)     # ["Player wants to improve with Colt", "Struggles in Gem Grab"]
    user_goals = Column(JSON)     # ["Reach 30k trophies", "Master Colt"]
    preferences = Column(JSON)    # {"favorite_mode": "brawlBall", "play_style": "aggressive"}

    # Summary for quick reference
    summary = Column(Text)

    __table_args__ = (
        Index('idx_memory_tag_topic', 'player_tag', 'topic'),
    )


class ProgressionGoal(Base):
    """
    Tracks player-defined goals for progression tracking.
    """
    __tablename__ = "progression_goals"

    id = Column(Integer, primary_key=True, index=True)
    player_tag = Column(String(20), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Goal definition
    goal_type = Column(String(30))  # "total_trophies", "brawler_rank", "mode_mastery", "victories"
    description = Column(String(200))  # Human-readable description

    # Target and progress
    target_value = Column(Integer)
    current_value = Column(Integer)
    initial_value = Column(Integer)  # Value when goal was created

    # Status
    status = Column(String(20), default="active")  # "active", "achieved", "abandoned"
    achieved_at = Column(DateTime, nullable=True)

    # Optional specifics
    brawler_name = Column(String(50), nullable=True)  # For brawler-specific goals
    mode_name = Column(String(50), nullable=True)     # For mode-specific goals

    __table_args__ = (
        Index('idx_goal_tag_status', 'player_tag', 'status'),
    )


# =============================================================================
# CACHED DATA MODELS
# =============================================================================

class CachedBrawlerData(Base):
    """
    Cached static brawler data from the API.
    Updated daily to ensure fresh data without constant API calls.
    """
    __tablename__ = "cached_brawlers"

    id = Column(Integer, primary_key=True, index=True)
    brawler_id = Column(Integer, unique=True, index=True)
    name = Column(String(50))
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Full brawler data as JSON
    data = Column(JSON)  # {starPowers: [...], gadgets: [...], ...}


class CachedEventRotation(Base):
    """
    Cached event rotation data.
    Updated hourly to track current active events.
    """
    __tablename__ = "cached_events"

    id = Column(Integer, primary_key=True, index=True)
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Event rotation data
    active_events = Column(JSON)    # Currently active events
    upcoming_events = Column(JSON)  # Scheduled upcoming events


# =============================================================================
# AI COACH SCHEDULER MODELS
# =============================================================================

class GameSchedule(Base):
    """
    AI-generated personalized game schedule for a user.
    Links to user and contains multiple schedule events.
    """
    __tablename__ = "game_schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    player_tag = Column(String(20), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Schedule metadata
    schedule_type = Column(String(50))  # "weekly", "trophy_push", "brawler_mastery"
    duration_days = Column(Integer, default=7)

    # AI-generated description
    description = Column(Text)
    goals = Column(JSON)  # ["Reach 25k trophies", "Master Colt"]

    # Relationship
    events = relationship("ScheduleEvent", back_populates="schedule", cascade="all, delete-orphan")
    user = relationship("User", backref="game_schedules")

    __table_args__ = (
        Index('idx_schedule_user_created', 'user_id', 'created_at'),
    )


class ScheduleEvent(Base):
    """
    Individual event in a game schedule (calendar entry).
    Contains specific recommendations for brawler, mode, and coaching notes.
    """
    __tablename__ = "schedule_events"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("game_schedules.id", ondelete="CASCADE"), index=True)

    # Event timing
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime)

    # Event details
    title = Column(String(200))  # "Push Colt in Gem Grab"
    event_type = Column(String(50))  # "ranked", "practice", "challenge", "rest"

    # Game-specific data
    recommended_brawler = Column(String(50), nullable=True)
    recommended_mode = Column(String(50), nullable=True)
    recommended_map = Column(String(100), nullable=True)

    # AI coaching notes
    notes = Column(Text)  # Tips and strategies
    priority = Column(String(20), default="medium")  # "low", "medium", "high"

    # Visual metadata
    color = Column(String(20), nullable=True)  # For calendar styling

    # Relationship
    schedule = relationship("GameSchedule", back_populates="events")

    __table_args__ = (
        Index('idx_event_schedule_time', 'schedule_id', 'start_time'),
    )


# =============================================================================
# GLOBAL META INTELLIGENCE MODELS
# =============================================================================

class GlobalMetaAggregate(Base):
    """
    Global meta aggregation across all trophy ranges.
    Provides a unified view of the entire game meta.
    """
    __tablename__ = "global_meta_aggregates"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Sample size
    total_battles_analyzed = Column(Integer)
    total_unique_players = Column(Integer)
    
    # Aggregated global statistics (JSON)
    data = Column(JSON)  # {
        # "top_brawlers": [...],
        # "overall_stats": {...},
        # "mode_breakdown": {...},
        # "trophy_distribution": {...}
    # }
    
    # AI-generated insights
    ai_insights = Column(Text, nullable=True)  # Markdown format
    ai_generated_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_global_meta_timestamp', 'timestamp'),
    )


class BrawlerSynergy(Base):
    """
    Tracks synergies between pairs of brawlers.
    Based on real game data from team compositions.
    """
    __tablename__ = "brawler_synergies"

    id = Column(Integer, primary_key=True, index=True)
    
    # Brawler pair (ordered: a_id < b_id)
    brawler_a_id = Column(Integer, index=True)
    brawler_a_name = Column(String(50))
    brawler_b_id = Column(Integer, index=True)
    brawler_b_name = Column(String(50))
    
    # Performance metrics
    games_together = Column(Integer, default=0)
    wins_together = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    avg_trophy_change = Column(Float, default=0.0)
    
    # Mode and map breakdown
    best_modes = Column(JSON)  # [{"mode": "gemGrab", "win_rate": 65.0, "games": 20}, ...]
    best_maps = Column(JSON, nullable=True)
    
    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow)
    sample_size_quality = Column(String(20), default="low")  # "low", "medium", "high"
    
    __table_args__ = (
        UniqueConstraint('brawler_a_id', 'brawler_b_id', name='uq_brawler_pair'),
        Index('idx_synergy_win_rate', 'win_rate'),
        Index('idx_synergy_games', 'games_together'),
    )


class GlobalTrendInsight(Base):
    """
    AI-generated insights about meta trends and shifts.
    Automatically generated by the trend detection engine.
    """
    __tablename__ = "global_trend_insights"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Insight categorization
    insight_type = Column(String(50), index=True)  # "meta_shift", "brawler_rise", "brawler_fall", "mode_trend", "synergy_discovered"
    
    # Content
    title = Column(String(200))
    content = Column(Text)  # Markdown formatted insight
    
    # Supporting data
    data = Column(JSON)  # Raw data that supports this insight
    
    # Confidence and quality
    confidence_score = Column(Float)  # 0.0 to 1.0
    impact_level = Column(String(20), default="medium")  # "low", "medium", "high", "critical"
    
    # Metadata
    is_active = Column(Boolean, default=True)  # Whether this insight is still relevant
    expires_at = Column(DateTime, nullable=True)  # When this insight becomes outdated
    
    __table_args__ = (
        Index('idx_insight_type_timestamp', 'insight_type', 'timestamp'),
        Index('idx_insight_active', 'is_active'),
    )


class BrawlerTrendHistory(Base):
    """
    Historical tracking of brawler performance trends.
    Used to detect rising and falling brawlers.
    """
    __tablename__ = "brawler_trend_history"

    id = Column(Integer, primary_key=True, index=True)
    brawler_id = Column(Integer, index=True)
    brawler_name = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Performance metrics
    pick_rate = Column(Float)  # Percentage
    win_rate = Column(Float)   # Percentage
    avg_trophy_change = Column(Float)
    
    # Trend analysis
    trend_direction = Column(String(20))  # "rising", "falling", "stable"
    trend_strength = Column(Float)  # 0.0 to 1.0, how strong the trend is
    
    # Rankings
    popularity_rank = Column(Integer)  # 1 = most popular
    performance_rank = Column(Integer)  # 1 = best performing
    
    # Sample size
    games_analyzed = Column(Integer)
    
    __table_args__ = (
        Index('idx_brawler_trend_id_time', 'brawler_id', 'timestamp'),
        Index('idx_trend_direction', 'trend_direction'),
    )

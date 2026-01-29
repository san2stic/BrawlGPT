"""
Pydantic models for BrawlGPT API.
Provides data validation and serialization.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class BrawlerStats(BaseModel):
    """Statistics for a single brawler."""
    id: int
    name: str
    power: int = Field(ge=1, le=11, description="Brawler power level")
    rank: int = Field(ge=1, description="Brawler rank")
    trophies: int = Field(ge=0)
    highestTrophies: int = Field(ge=0)

    class Config:
        extra = "allow"  # Allow extra fields from API


class ClubInfo(BaseModel):
    """Player's club information."""
    tag: str
    name: str

    class Config:
        extra = "allow"


class PlayerStats(BaseModel):
    """Player profile statistics."""
    tag: str
    name: str
    nameColor: Optional[str] = None
    icon: Optional[dict] = None
    trophies: int = Field(ge=0)
    highestTrophies: int = Field(ge=0)
    expLevel: int = Field(ge=1)
    expPoints: int = Field(ge=0)
    isQualifiedFromChampionshipChallenge: bool = False
    soloVictories: int = Field(ge=0, alias="soloVictories")
    duoVictories: int = Field(ge=0, alias="duoVictories")
    club: Optional[ClubInfo] = None
    brawlers: list[BrawlerStats] = []

    class Config:
        extra = "allow"
        populate_by_name = True

    # Computed field for 3v3 victories
    @property
    def victories_3v3(self) -> int:
        """Get 3v3 victories (field name varies in API)."""
        return getattr(self, "3vs3Victories", 0)


class BattleEvent(BaseModel):
    """Battle event information."""
    id: Optional[int] = None
    mode: Optional[str] = None
    map: Optional[str] = None

    class Config:
        extra = "allow"


class BattlePlayer(BaseModel):
    """Player info within a battle."""
    tag: str
    name: str
    brawler: Optional[dict] = None

    class Config:
        extra = "allow"


class BattleInfo(BaseModel):
    """Battle details."""
    mode: Optional[str] = None
    type: Optional[str] = None
    result: Optional[str] = None  # victory, defeat, draw
    duration: Optional[int] = None
    trophyChange: Optional[int] = None
    starPlayer: Optional[BattlePlayer] = None
    teams: Optional[list[list[BattlePlayer]]] = None
    players: Optional[list[BattlePlayer]] = None

    class Config:
        extra = "allow"


class BattleLogItem(BaseModel):
    """Single battle log entry."""
    battleTime: str
    event: Optional[BattleEvent] = None
    battle: Optional[BattleInfo] = None

    class Config:
        extra = "allow"


class BattleLog(BaseModel):
    """Battle log response."""
    items: list[BattleLogItem] = []

    class Config:
        extra = "allow"


class ErrorResponse(BaseModel):
    """API error response."""
    detail: str
    error_type: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: Optional[str] = None
    version: Optional[str] = None
    services: Optional[dict[str, str]] = None


class PlayerAnalysisResponse(BaseModel):
    """Complete player analysis response."""
    player: dict[str, Any]  # Raw player data
    battles: dict[str, Any]  # Raw battle log
    insights: str  # AI-generated insights

    class Config:
        extra = "allow"


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    """Chat request payload."""
    messages: list[ChatMessage]
    player_context: Optional[dict[str, Any]] = None


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class UserLogin(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    brawl_stars_tag: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str

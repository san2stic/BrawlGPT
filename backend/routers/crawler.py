import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

import auth
from database import get_db
from db_models import User as UserModel
from crawler import BattleCrawler
from ai_analyst import MetaAnalyst
from brawlstars import BrawlStarsClient

# Initialize services
# In a real app, these should be dependencies, but for simplicity here:
brawl_client = BrawlStarsClient(os.getenv("BRAWL_API_KEY"))
crawler_service = BattleCrawler(brawl_client)
meta_analyst = MetaAnalyst(os.getenv("OPENROUTER_API_KEY"))

router = APIRouter(
    prefix="/api/crawler",
    tags=["crawler"]
)

@router.post("/analyze/{tag}")
async def analyze_meta(
    tag: str,
    current_user: Annotated[UserModel, Depends(auth.get_current_user)]
):
    """
    Trigger a meta analysis for the given player tag.
    Requires authentication.
    """
    # 1. Crawl
    try:
        clean_tag = BrawlStarsClient.validate_tag(tag)
        meta_report = await crawler_service.crawl_battle_log(clean_tag)
        
        if "error" in meta_report:
             raise HTTPException(status_code=400, detail=meta_report["error"])
             
        # 2. Analyze with Gemini
        ai_insight = await meta_analyst.analyze_meta_report(meta_report)
        
        return {
            "meta_report": meta_report,
            "ai_analysis": ai_insight
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

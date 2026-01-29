from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

import auth
from database import get_db
from db_models import User as UserModel
from models import UserCreate, User, Token

router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"]
)

@router.post("/register", response_model=User)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    result = await db.execute(select(UserModel).where(UserModel.email == user.email))
    db_user = result.scalars().first()
    
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = auth.get_password_hash(user.password)
    new_user = UserModel(email=user.email, hashed_password=hashed_password)
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: AsyncSession = Depends(get_db)):
    # Authenticate user
    result = await db.execute(select(UserModel).where(UserModel.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
async def read_users_me(current_user: Annotated[UserModel, Depends(auth.get_current_user)]):
    return current_user

@router.post("/claim/{tag}")
async def claim_player_profile(
    tag: str, 
    current_user: Annotated[UserModel, Depends(auth.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    # Update user's brawl stars tag
    # Note: Ideally validation of the tag happens here too using BrawlStarsClient
    current_user.brawl_stars_tag = tag
    db.add(current_user)
    await db.commit()
    return {"message": f"Profile {tag} claimed successfully", "user": current_user.email}

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, select
from datetime import datetime

# Define minimal models for verification if importing fails
try:
    from backend.db_models import Interaction, Insight, Base
except ImportError:
    # If running from root, might need path adjustment or just mock models for connection test
    # But let's assume user runs this with PYTHONPATH set or from backend/ dir
    # For simplicity, we just test connection here.
    pass

# Connection string for localhost (exposed port)
DATABASE_URL = "postgresql+asyncpg://brawl_user:brawl_password@localhost:5432/brawlgpt_db"

async def verify_db():
    print(f"Connecting to {DATABASE_URL}...")
    try:
        engine = create_async_engine(DATABASE_URL, echo=False)
        async with engine.begin() as conn:
            # Test query
            result = await conn.execute(text("SELECT 1"))
            print(f"Connection successful! Result: {result.scalar()}")
            
            # Check if tables exist
            # This requires inspecting information_schema or just trying to select
            print("Checking tables...")
            try:
                await conn.execute(text("SELECT count(*) FROM interactions"))
                print("Table 'interactions' exists.")
            except Exception as e:
                print(f"Table check failed (might need to run app first to init db): {e}")

        await engine.dispose()
        print("\nVerification passed!")
        
    except Exception as e:
        print(f"\nVerification failed: {e}")
        print("Ensure 'docker-compose up' is running and port 5432 is exposed.")

if __name__ == "__main__":
    try:
        import asyncio
        asyncio.run(verify_db())
    except KeyboardInterrupt:
        pass

#!/usr/bin/env python
"""Initialize database tables."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.db.base import engine, Base
from src.db import models  # noqa: F401 (imports the models so Base knows them)

async def init_db():
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())

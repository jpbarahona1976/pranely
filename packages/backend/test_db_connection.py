"""Test database connection."""
import asyncio
from app.core.database import engine

async def test():
    try:
        async with engine.connect() as conn:
            result = await conn.execute("SELECT 1 as test")
            print("SUCCESS:", result.fetchone())
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test())
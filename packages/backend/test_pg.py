import asyncio
import asyncpg

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='pranely',
            password='PranelyDev2026!',
            database='pranely_dev',
            timeout=5
        )
        result = await conn.fetchval('SELECT 1')
        print(f"Connection successful! Result: {result}")
        await conn.close()
        return True
    except Exception as e:
        print(f"Connection failed: {type(e).__name__}: {e}")
        return False

asyncio.run(test_connection())
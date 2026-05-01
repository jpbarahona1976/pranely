import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')

import asyncio
import asyncpg

async def check_db():
    conn_url = "postgresql://pranely:PranelyDev2026!@localhost:5432/pranely_dev"
    try:
        conn = await asyncpg.connect(conn_url)
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        print(f"[OK] PostgreSQL connection: {result}")
        return True
    except Exception as e:
        print(f"[FAIL] PostgreSQL connection: {e}")
        return False

async def check_redis():
    import redis.asyncio as redis
    try:
        r = await redis.from_url("redis://localhost:6379")
        await r.ping()
        await r.aclose()
        print("[OK] Redis connection")
        return True
    except Exception as e:
        print(f"[FAIL] Redis connection: {e}")
        return False

async def main():
    print("Testing connections...")
    pg_ok = await check_db()
    redis_ok = await check_redis()
    return pg_ok and redis_ok

if __name__ == "__main__":
    asyncio.run(main())

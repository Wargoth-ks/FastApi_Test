from redis import asyncio as aioredis
from source.conf.configs import settings
from contextlib import asynccontextmanager


@asynccontextmanager
async def get_redis():
    """
    The get_redis function is a context manager that returns an asyncio-redis
    Redis object. This object can be used to interact with the Redis database.

    :return: A context manager, which is an object that can be used with the async with statement
    """
    pool = aioredis.ConnectionPool.from_url(
        f"redis://localhost",
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
        encoding="utf-8",
    )
    redis = aioredis.Redis.from_pool(pool)
    try:
        yield redis
    finally:
        await redis.aclose()

from __future__ import annotations


async def ping_redis(url: str) -> bool:
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(url, socket_connect_timeout=1.5)
        try:
            return bool(await client.ping())
        finally:
            await client.aclose()
    except Exception:
        return False

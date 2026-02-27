"""Fetches cat GIFs and cat facts from public APIs."""

import aiohttp
import config


async def fetch_cat_gif() -> str:
    """Return a URL to a random cat GIF from The Cat API."""
    params = {"mime_types": "gif", "limit": 1}
    headers = {}
    if config.CAT_API_KEY:
        headers["x-api-key"] = config.CAT_API_KEY

    async with aiohttp.ClientSession() as session:
        async with session.get(
            config.CAT_GIF_URL, params=params, headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data:
                    return data[0]["url"]
    # Fallback GIF if the API is unreachable
    return "https://media.giphy.com/media/JIX9t2j0ZTN9S/giphy.gif"


async def fetch_cat_fact() -> str:
    """Return a random cat fact from catfact.ninja."""
    async with aiohttp.ClientSession() as session:
        async with session.get(config.CAT_FACT_URL) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("fact", "Cats are amazing!")
    return "Cats sleep for about 70%% of their lives. 😴"

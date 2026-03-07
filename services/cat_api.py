"""TheCatAPI and catfact.ninja integrations."""

import aiohttp

import config


async def fetch_cat_gif() -> str:
    """Return a URL to a random cat GIF from The Cat API."""
    print("[API] Fetching cat GIF from TheCatAPI...")
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
                    print(f"[API] Cat GIF fetched: {data[0]['url'][:80]}")
                    return data[0]["url"]
    # Fallback GIF if the API is unreachable
    print("[API] Cat GIF API failed — using fallback GIF")
    return "https://media.giphy.com/media/JIX9t2j0ZTN9S/giphy.gif"


async def fetch_cat_fact() -> str:
    """Return a random cat fact from catfact.ninja."""
    print("[API] Fetching cat fact from catfact.ninja...")
    async with aiohttp.ClientSession() as session:
        async with session.get(config.CAT_FACT_URL) as resp:
            if resp.status == 200:
                data = await resp.json()
                fact = data.get("fact", "Cats are amazing!")
                print(f"[API] Cat fact fetched: '{fact[:60]}...'")
                return fact
    print("[API] Cat fact API failed — using fallback fact")
    return "Cats sleep for about 70%% of their lives. 😴"

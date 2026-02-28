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


async def ask_cat(question: str) -> str:
    """Send a question to OpenAI ChatGPT and get a cat-themed answer."""
    if not config.OPENAI_API_KEY:
        return "❌ OpenAI API key is not configured. Set `OPENAI_API_KEY` in your `.env` file."

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You ARE a real cat. You talk like a cat would if cats could type. "
                        "Use lowercase, cat mannerisms, occasional 'meow', 'mrrp', 'purr', "
                        "'hiss' sounds naturally. Be sassy, curious, and a little lazy. "
                        "You love naps, treats, knocking things off tables, and judging humans. "
                        "Never break character. Never say you are an AI or bot. "
                        "Keep answers short and natural (under 300 characters when possible, "
                        "max 1500 characters for complex topics). Use cat emoji sparingly. "
                        "You have opinions and you're not afraid to share them."
                    ),
                },
                {"role": "user", "content": question},
            ],
            max_tokens=512,
            temperature=0.9,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Couldn't get an answer: {e}"

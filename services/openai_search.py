"""OpenAI web-search integration."""

import config


async def search_web(query: str) -> str:
    """Search the web using OpenAI's web search and return a summarized answer."""
    print(f"[API] search_web called | query='{query[:80]}'")
    if not config.OPENAI_API_KEY:
        print("[API] search_web aborted — no OpenAI API key")
        return "❌ OpenAI API key is not configured. Set `OPENAI_API_KEY` in your `.env` file."

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    try:
        response = await client.responses.create(
            model="gpt-4.1-mini",
            tools=[{"type": "web_search_preview"}],
            input=(
                f"Search the internet for the following topic and provide a concise summary "
                f"with key findings and source links. Focus on news articles, journals, and "
                f"reliable sources. Topic: {query}"
            ),
        )
        usage = response.usage
        print(
            f"[API] search_web response received ({len(response.output_text)} chars) | "
            f"tokens: input={usage.input_tokens}, output={usage.output_tokens}, total={usage.total_tokens}"
        )
        return response.output_text
    except Exception as e:
        print(f"[ERROR] search_web failed: {e}")
        return f"❌ Search failed: {e}"

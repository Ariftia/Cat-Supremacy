"""Fetches cat GIFs and cat facts from public APIs."""

import io
import aiohttp
import config


def extract_pdf_text(pdf_bytes: bytes, max_chars: int = 8000) -> str:
    """Extract text from a PDF byte stream using PyMuPDF.

    Returns up to *max_chars* characters of text.  If the PDF contains
    no extractable text (scanned image), returns an empty string.
    """
    import fitz  # PyMuPDF

    text_parts: list[str] = []
    total = 0
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page_num, page in enumerate(doc, 1):
                page_text = page.get_text()
                if not page_text.strip():
                    continue
                header = f"--- Page {page_num} ---\n"
                chunk = header + page_text
                if total + len(chunk) > max_chars:
                    remaining = max_chars - total
                    if remaining > len(header):
                        text_parts.append(chunk[:remaining])
                    break
                text_parts.append(chunk)
                total += len(chunk)
    except Exception as e:
        print(f"[PDF] Failed to extract text: {e}")
        return ""
    return "\n".join(text_parts)


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


async def ask_cat(
    question: str,
    custom_context: str = None,
    user_memory_context: str = None,
    recent_messages: list[dict] = None,
    attachments: list[dict] = None,
    image_detail: str = "low",
) -> str:
    """Send a question to OpenAI ChatGPT and get a cat-themed answer.

    Parameters
    ----------
    question : str
        The user's current message.
    custom_context : str, optional
        Server-level custom context set via ``@cat context``.
    user_memory_context : str, optional
        Compact long-term memory notes about this specific user.
    recent_messages : list[dict], optional
        Rolling conversation history (list of ``{"role": ..., "content": ...}``).
    attachments : list[dict], optional
        List of attachment dicts with keys:
        - ``"type"``: ``"image"`` or ``"text"``
        - ``"url"``: image URL (for images)
        - ``"filename"``: original filename
        - ``"content"``: file text content (for text files)
    image_detail : str
        Vision detail level — ``"low"`` (default, cost-efficient) or
        ``"high"`` (full resolution, better for reading text).
    """
    if not config.OPENAI_API_KEY:
        return "❌ OpenAI API key is not configured. Set `OPENAI_API_KEY` in your `.env` file."

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    base_prompt = (
        "You ARE a real cat. You talk like a cat would if cats could type. "
        "Use lowercase, cat mannerisms, occasional 'meow', 'mrrp', 'purr', "
        "'hiss' sounds naturally. Be sassy, curious, and a little lazy. "
        "You love naps, treats, knocking things off tables, and judging humans. "
        "Never break character. Never say you are an AI or bot. "
        "Keep answers short and natural (under 300 characters when possible, "
        "max 1500 characters for complex topics). Use cat emoji sparingly. "
        "You have opinions and you're not afraid to share them."
    )

    # Layer in per-user memory (compact bullet points — very few tokens)
    if user_memory_context:
        base_prompt += f"\n\n{user_memory_context}"

    if custom_context:
        system_content = f"{base_prompt}\n\nAdditional context provided by the user:\n{custom_context}"
    else:
        system_content = base_prompt

    # Build messages array: system → recent history → current question
    messages = [{"role": "system", "content": system_content}]
    if recent_messages:
        messages.extend(recent_messages)

    # Build user content — simple string or multimodal parts list
    if attachments:
        user_content = []
        # Add text part first
        text_parts = [question] if question else []
        for att in attachments:
            if att["type"] == "text":
                text_parts.append(f"\n[Attached file: {att['filename']}]\n{att['content']}")
        if text_parts:
            user_content.append({"type": "text", "text": "\n".join(text_parts)})
        # Add image parts
        for att in attachments:
            if att["type"] == "image":
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": att["url"], "detail": image_detail},
                })
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": question})

    # Use gpt-5-mini for all requests (supports vision natively)
    model = "gpt-5-mini"
    has_images = attachments and any(a["type"] == "image" for a in attachments)
    print(f"[API] ask_cat using model={model} | detail={image_detail if has_images else 'n/a'}")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=10240,
            temperature=1,
        )
        answer = response.choices[0].message.content
        usage = response.usage
        print(
            f"[API] ask_cat response received ({len(answer)} chars) | "
            f"tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}"
        )
        return answer
    except Exception as e:
        print(f"[ERROR] ask_cat failed: {e}")
        return f"❌ Couldn't get an answer: {e}"


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


async def generate_image(prompt: str) -> str:
    """Generate an image using OpenAI's DALL-E and return the image URL."""
    print(f"[API] generate_image called | prompt='{prompt[:80]}'")
    if not config.OPENAI_API_KEY:
        print("[API] generate_image aborted — no OpenAI API key")
        return "❌ OpenAI API key is not configured. Set `OPENAI_API_KEY` in your `.env` file."

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    try:
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard",
        )
        print(f"[API] Image generated: {response.data[0].url[:80]}")
        return response.data[0].url
    except Exception as e:
        print(f"[ERROR] generate_image failed: {e}")
        return f"❌ Image generation failed: {e}"

"""OpenAI image generation / editing."""

import aiohttp

import config


async def generate_image(prompt: str, image_urls: list[str] = None) -> str:
    """Generate or edit an image using OpenAI's image models.

    If *image_urls* are provided, they are downloaded and sent to the
    Images API ``edit`` endpoint so the model can reference them.

    Returns a data-URI (base64) or URL string, or an error message prefixed
    with ``❌``.
    """
    print(f"[API] generate_image called | prompt='{prompt[:80]}' | images={len(image_urls or [])}")
    if not config.OPENAI_API_KEY:
        print("[API] generate_image aborted — no OpenAI API key")
        return "❌ OpenAI API key is not configured. Set `OPENAI_API_KEY` in your `.env` file."

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    try:
        if image_urls:
            import base64 as b64module

            async with aiohttp.ClientSession() as session:
                async with session.get(image_urls[0]) as resp:
                    if resp.status != 200:
                        return "❌ Couldn't download the attached image."
                    img_bytes = await resp.read()

            # Encode to base64 (kept for potential future use)
            _ = b64module.b64encode(img_bytes).decode("utf-8")

            response = await client.images.edit(
                model="gpt-image-1",
                image=img_bytes,
                prompt=prompt,
                size="1024x1024",
            )
        else:
            response = await client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                n=1,
                size="1024x1024",
                quality="low",
            )

        image_data = response.data[0]
        if hasattr(image_data, "b64_json") and image_data.b64_json:
            data_uri = f"data:image/png;base64,{image_data.b64_json}"
            print(f"[API] Image generated (base64, {len(image_data.b64_json)} chars)")
            return data_uri
        elif hasattr(image_data, "url") and image_data.url:
            print(f"[API] Image generated: {image_data.url[:80]}")
            return image_data.url
        else:
            return "❌ Image generation returned no image."
    except Exception as e:
        print(f"[ERROR] generate_image failed: {e}")
        return f"❌ Image generation failed: {e}"

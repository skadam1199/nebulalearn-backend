import os
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url="https://integrate.api.nvidia.com/v1",
)
MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1.5"

SUPPORTED_LANGUAGES = {
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh": "Chinese Simplified",
    "ja": "Japanese",
    "ko": "Korean",
    "pt": "Portuguese",
    "ar": "Arabic",
    "hi": "Hindi",
    "it": "Italian",
    "ru": "Russian",
}


async def translate_content(content: str, target_language_code: str) -> str:
    if target_language_code not in SUPPORTED_LANGUAGES:
        return content

    language_name = SUPPORTED_LANGUAGES[target_language_code]

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=2000,
        messages=[
            {
                "role": "system",
                "content": f"You are a professional translator. Translate the following academic content to {language_name}. Preserve all formatting, structure, and meaning. Keep timestamps like MM:SS as-is. Return only the translated text, nothing else."
            },
            {
                "role": "user",
                "content": content
            }
        ]
    )

    return response.choices[0].message.content

import asyncio
import json
import os
from openai import AsyncOpenAI
from typing import List, Dict

client = AsyncOpenAI(
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url="https://integrate.api.nvidia.com/v1",
)
MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1.5"


def chunks_to_text(chunks: List[Dict], max_chars: int = 12000) -> str:
    text = ""
    for chunk in chunks:
        mins = chunk["start_time"] // 60
        secs = chunk["start_time"] % 60
        text += f"[{mins:02d}:{secs:02d}] {chunk['text']}\n"
        if len(text) > max_chars:
            break
    return text


async def generate_outline(chunks: List[Dict], title: str) -> Dict:
    transcript = chunks_to_text(chunks)
    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=1500,
        messages=[
            {
                "role": "system",
                "content": """You are an expert academic tutor. Generate a structured outline from this lecture transcript.
Return ONLY valid JSON, no markdown, no preamble, no code blocks.
Schema: {"outline": [{"title": "string", "start_time": number, "subtopics": [{"title": "string", "start_time": number}]}]}
Rules:
- Max 6 main topics, max 4 subtopics each
- start_time must be in seconds (integer)
- Titles must be concise under 8 words
- Use timestamps from the transcript"""
            },
            {
                "role": "user",
                "content": f"Lecture title: {title}\n\nTranscript:\n{transcript}"
            }
        ]
    )
    try:
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except:
        return {"outline": [{"title": title, "start_time": 0, "subtopics": []}]}


async def generate_summaries(chunks: List[Dict], title: str) -> Dict:
    transcript = chunks_to_text(chunks)

    async def summary_90s():
        r = await client.chat.completions.create(
            model=MODEL,
            max_tokens=250,
            messages=[
                {"role": "system", "content": "You are an expert tutor. Write a 90-second summary of about 150 words of this lecture. Plain language, no jargon. Just the single most important insight. Return only the summary text."},
                {"role": "user", "content": f"Title: {title}\n\nTranscript:\n{transcript}"}
            ]
        )
        return r.choices[0].message.content

    async def summary_5min():
        r = await client.chat.completions.create(
            model=MODEL,
            max_tokens=700,
            messages=[
                {"role": "system", "content": "You are an expert tutor. Write a 5-minute summary of about 500 words of this lecture. Cover all major concepts in order. Clear and accessible. Return only the summary text."},
                {"role": "user", "content": f"Title: {title}\n\nTranscript:\n{transcript}"}
            ]
        )
        return r.choices[0].message.content

    async def summary_full():
        r = await client.chat.completions.create(
            model=MODEL,
            max_tokens=1800,
            messages=[
                {"role": "system", "content": "You are an expert tutor. Write a comprehensive summary of this lecture. Cover every concept, example, and key point. Include timestamps where relevant in MM:SS format. Return only the summary text."},
                {"role": "user", "content": f"Title: {title}\n\nTranscript:\n{transcript}"}
            ]
        )
        return r.choices[0].message.content

    s90, s5, sfull = await asyncio.gather(summary_90s(), summary_5min(), summary_full())
    return {"ninety_seconds": s90, "five_minutes": s5, "full": sfull}


async def generate_flashcards(chunks: List[Dict], title: str) -> Dict:
    transcript = chunks_to_text(chunks)
    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=2000,
        messages=[
            {
                "role": "system",
                "content": """You are an expert tutor creating flashcards. Generate 10-15 flashcards from this lecture.
Return ONLY valid JSON, no markdown, no preamble, no code blocks.
Schema: {"flashcards": [{"question": "string", "answer": "string", "source_time": number, "source_quote": "string"}]}
Rules:
- Questions should test understanding not just recall
- Answers should be 1-3 sentences
- source_time is seconds integer from nearest transcript timestamp
- source_quote is a short phrase under 10 words from the transcript"""
            },
            {
                "role": "user",
                "content": f"Title: {title}\n\nTranscript:\n{transcript}"
            }
        ]
    )
    try:
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except:
        return {"flashcards": []}


async def run_synthesis(chunks: List[Dict], title: str) -> Dict:
    outline, summaries, flashcards = await asyncio.gather(
        generate_outline(chunks, title),
        generate_summaries(chunks, title),
        generate_flashcards(chunks, title)
    )
    return {
        "outline": outline.get("outline", []),
        "summaries": summaries,
        "flashcards": flashcards.get("flashcards", [])
    }

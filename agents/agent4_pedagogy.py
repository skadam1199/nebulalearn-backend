import json
import os
from openai import AsyncOpenAI
from typing import List, Dict

client = AsyncOpenAI(
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url="https://integrate.api.nvidia.com/v1",
)
MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1.5"


async def run_pedagogy_audit(chunks: List[Dict], title: str) -> Dict:
    transcript = ""
    for chunk in chunks:
        mins = chunk["start_time"] // 60
        secs = chunk["start_time"] % 60
        transcript += f"[{mins:02d}:{secs:02d}] {chunk['text']}\n"
        if len(transcript) > 12000:
            break

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=3000,
        messages=[
            {
                "role": "system",
                "content": """You are an expert educational consultant auditing a lecture for a faculty member.
This report is PRIVATE. Be honest, specific, and constructive.

Return ONLY valid JSON, no markdown, no preamble, no code blocks.
Schema:
{
  "overall_score": number 0-100,
  "top_priority_fix": "one sentence the single most important thing to change",
  "scores": {
    "clarity": number 0-100,
    "accessibility": number 0-100,
    "pacing": number 0-100,
    "engagement": number 0-100,
    "equity": number 0-100
  },
  "issues": [
    {
      "severity": "high or medium or low",
      "timestamp": number seconds,
      "category": "clarity or accessibility or pacing or engagement or equity",
      "issue": "what is wrong specifically",
      "suggestion": "specific rewrite or fix"
    }
  ],
  "strengths": ["string"],
  "summary": "2-3 sentences overall assessment"
}

Find 5-10 specific timestamped issues. Be specific not vague. Strengths should be genuine."""
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
        return {
            "overall_score": 70,
            "top_priority_fix": "Could not generate audit. Please try again.",
            "scores": {"clarity": 70, "accessibility": 70, "pacing": 70, "engagement": 70, "equity": 70},
            "issues": [],
            "strengths": [],
            "summary": "Audit generation failed. Please try again."
        }

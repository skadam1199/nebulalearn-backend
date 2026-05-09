import json
import os
from groq import AsyncGroq
from typing import List, Dict

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


async def map_curriculum(lectures: List[Dict], objectives: List[str]) -> Dict:
    lecture_summaries = ""
    for i, lecture in enumerate(lectures):
        lecture_summaries += f"\n--- Lecture {i+1}: {lecture['title']} ---\n"
        chunks = lecture.get("chunks", [])
        for chunk in chunks[:15]:
            mins = chunk["start_time"] // 60
            secs = chunk["start_time"] % 60
            lecture_summaries += f"[{mins:02d}:{secs:02d}] {chunk['text']}\n"
        if len(lecture_summaries) > 10000:
            break

    objectives_text = "\n".join([f"{i+1}. {obj}" for i, obj in enumerate(objectives)])

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=3000,
        messages=[
            {
                "role": "system",
                "content": """You are an academic curriculum analyst for a provost.
Analyze lecture content against stated learning objectives.

Return ONLY valid JSON, no markdown, no preamble, no code blocks.
Schema:
{
  "summary": {
    "total_objectives": number,
    "fully_covered": number,
    "partially_covered": number,
    "not_covered": number
  },
  "objectives": [
    {
      "objective": "string",
      "coverage": "strong or partial or missing",
      "coverage_score": number 0-100,
      "lectures_covering": [number],
      "evidence": "specific quote or reference from lectures",
      "gap_notes": "what is missing or could be improved"
    }
  ],
  "recommendations": ["string"],
  "overall_assessment": "2-3 sentences"
}"""
            },
            {
                "role": "user",
                "content": f"Learning Objectives:\n{objectives_text}\n\nLecture Content:\n{lecture_summaries}"
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
            "summary": {"total_objectives": len(objectives), "fully_covered": 0, "partially_covered": 0, "not_covered": len(objectives)},
            "objectives": [],
            "recommendations": [],
            "overall_assessment": "Could not generate curriculum map. Please try again."
        }
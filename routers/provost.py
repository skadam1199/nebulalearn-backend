from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from agents.agent1_ingestion import extract_transcript
from agents.agent6_curriculum import map_curriculum

router = APIRouter()


class ProvostRequest(BaseModel):
    urls: List[str]
    objectives: List[str]


@router.post("/curriculum-map")
async def curriculum_map(request: ProvostRequest):
    """Generate curriculum map for provost"""
    try:
        if len(request.urls) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 URLs allowed")

        if not request.objectives:
            raise HTTPException(status_code=400, detail="Learning objectives are required")

        # Agent 1: Extract transcripts for all videos
        lectures = []
        for url in request.urls:
            try:
                video_data = extract_transcript(url)
                lectures.append(video_data)
            except ValueError as e:
                lectures.append({"title": url, "chunks": [], "error": str(e)})

        if not any(l.get("chunks") for l in lectures):
            raise HTTPException(status_code=422, detail="No transcripts found for any of the provided videos")

        # Agent 6: Map curriculum
        curriculum = await map_curriculum(lectures, request.objectives)

        return {
            "lectures": [{"title": l["title"], "video_id": l.get("video_id", ""), "duration": l.get("duration", 0)} for l in lectures],
            "objectives_count": len(request.objectives),
            "curriculum_map": curriculum
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Curriculum mapping failed: {str(e)}")
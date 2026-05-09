from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agents.agent1_ingestion import extract_transcript
from agents.agent4_pedagogy import run_pedagogy_audit

router = APIRouter()


class FacultyRequest(BaseModel):
    url: str


@router.post("/faculty-audit")
async def faculty_audit(request: FacultyRequest):
    """Run pedagogical audit on a lecture for faculty"""
    try:
        # Agent 1: Extract transcript
        video_data = extract_transcript(request.url)
        chunks = video_data["chunks"]
        title = video_data["title"]

        if not chunks:
            raise HTTPException(status_code=422, detail="No transcript found for this video")

        # Agent 4: Run pedagogy audit
        audit = await run_pedagogy_audit(chunks, title)

        return {
            "video_id": video_data["video_id"],
            "title": title,
            "duration": video_data["duration"],
            "audit": audit
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")
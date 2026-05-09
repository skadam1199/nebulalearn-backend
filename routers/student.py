from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from agents.agent1_ingestion import extract_transcript
from agents.agent2_synthesis import run_synthesis
from agents.agent3_search import embed_chunks, semantic_search
from agents.agent5_translation import translate_content

router = APIRouter()

# In-memory store for embedded chunks per video
video_cache = {}


class ProcessRequest(BaseModel):
    url: str
    language: Optional[str] = "en"


class SearchRequest(BaseModel):
    query: str
    video_id: str
    language: Optional[str] = "en"


@router.post("/process")
async def process_video(request: ProcessRequest):
    """Process a YouTube video for student study materials"""
    try:
        # Agent 1: Extract transcript
        video_data = extract_transcript(request.url)
        chunks = video_data["chunks"]
        title = video_data["title"]
        video_id = video_data["video_id"]

        if not chunks:
            raise HTTPException(status_code=422, detail="No transcript found for this video")

        # Agent 2: Run synthesis in parallel
        synthesis = await run_synthesis(chunks, title)

        # Agent 3: Embed chunks for search
        embedded = await embed_chunks(chunks)
        video_cache[video_id] = embedded

        result = {
            "video_id": video_id,
            "title": title,
            "duration": video_data["duration"],
            "outline": synthesis["outline"],
            "summaries": synthesis["summaries"],
            "flashcards": synthesis["flashcards"],
        }

        # Agent 5: Translate if needed
        if request.language and request.language != "en":
            result["summaries"]["ninety_seconds"] = await translate_content(
                result["summaries"]["ninety_seconds"], request.language
            )
            result["summaries"]["five_minutes"] = await translate_content(
                result["summaries"]["five_minutes"], request.language
            )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/search")
async def search_video(request: SearchRequest):
    """Semantic search within a processed video"""
    try:
        if request.video_id not in video_cache:
            raise HTTPException(status_code=404, detail="Video not processed yet. Please process the video first.")

        embedded_chunks = video_cache[request.video_id]
        results = await semantic_search(request.query, embedded_chunks)

        return {"query": request.query, "results": results}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/translate")
async def translate(body: dict):
    """Translate content to target language"""
    try:
        content = body.get("content", "")
        language = body.get("language", "en")
        translated = await translate_content(content, language)
        return {"translated": translated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
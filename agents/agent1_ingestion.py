import os
import re
from typing import List, Dict
from supadata import Supadata, SupadataError


def extract_video_id(url: str) -> str:
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


def extract_transcript(url: str) -> Dict:
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL. Please provide a valid YouTube link.")

    api_key = os.getenv("SUPADATA_API_KEY")
    if not api_key:
        raise ValueError("SUPADATA_API_KEY is not set. Sign up at https://supadata.ai and add your key to .env")

    supadata = Supadata(api_key=api_key)

    try:
        transcript = supadata.youtube.transcript(video_id=video_id, lang="en")
    except SupadataError as e:
        err = str(e.error).lower() if e.error else ""
        msg = str(e.message).lower() if e.message else ""
        if "not found" in msg or "no transcript" in msg or "captions" in msg:
            raise ValueError("This video has no captions available. Please try a video with auto-generated or manual captions.")
        if "private" in msg:
            raise ValueError("This video is private and cannot be accessed.")
        if "quota" in msg or "limit" in msg or "402" in err:
            raise ValueError("Supadata API quota exceeded. Please try again tomorrow or upgrade your plan.")
        raise ValueError(f"Could not fetch transcript: {e.message or e.error}")

    content = transcript.content
    if not content:
        raise ValueError("This video has no captions available. Please try a video with auto-generated or manual captions.")

    # content is a list of chunk objects with .text, .offset (ms), .duration (ms)
    entries = [
        {
            "start": chunk.offset / 1000,
            "duration": (chunk.duration or 2000) / 1000,
            "text": chunk.text,
        }
        for chunk in content
        if hasattr(chunk, "text") and chunk.text and chunk.text.strip()
    ]

    if not entries:
        raise ValueError("Could not parse transcript. Please try a different video.")

    # Get title from video metadata
    title = "Lecture"
    try:
        video = supadata.youtube.video(id=video_id)
        title = video.title or "Lecture"
    except Exception:
        pass

    chunks = _chunk_transcript(entries)
    duration = int(entries[-1]["start"] + entries[-1].get("duration", 0))

    return {
        "title": title,
        "duration": duration,
        "chunks": chunks,
        "video_id": video_id,
    }


def _chunk_transcript(raw: List[Dict], chunk_duration: int = 30) -> List[Dict]:
    chunks = []
    current = {"start_time": 0.0, "end_time": 0.0, "text": "", "chunk_id": 0}

    for entry in raw:
        start = entry.get("start", 0)
        dur = entry.get("duration", 2)
        text = entry.get("text", "").strip().replace("\n", " ")

        if not text:
            continue

        if start - current["start_time"] > chunk_duration and current["text"]:
            chunks.append({
                "chunk_id": current["chunk_id"],
                "start_time": int(current["start_time"]),
                "end_time": int(current["end_time"]),
                "text": current["text"].strip(),
            })
            current = {
                "start_time": start,
                "end_time": start + dur,
                "text": text + " ",
                "chunk_id": len(chunks),
            }
        else:
            if not current["text"]:
                current["start_time"] = start
            current["end_time"] = start + dur
            current["text"] += text + " "

    if current["text"]:
        chunks.append({
            "chunk_id": current["chunk_id"],
            "start_time": int(current["start_time"]),
            "end_time": int(current["end_time"]),
            "text": current["text"].strip(),
        })

    return chunks


def time_to_seconds(time_str: str) -> float:
    parts = time_str.replace(",", ".").split(":")
    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])

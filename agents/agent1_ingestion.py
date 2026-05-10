import re
from typing import List, Dict


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


def extract_transcript(url: str) -> Dict:
    """Extract transcript from YouTube video with timestamps.
    
    Primary: youtube-transcript-api (no bot detection issues)
    Fallback: yt-dlp (for videos without transcripts)
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL. Please provide a valid YouTube link.")

    # --- Primary: youtube-transcript-api ---
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

        # Get video title via a lightweight request
        title = _get_video_title(video_id)

        ytt = YouTubeTranscriptApi()

        raw = None
        try:
            # Try English manual transcript first
            raw = ytt.fetch(video_id, languages=['en'])
        except Exception:
            try:
                # Try auto-generated English
                transcript_list = ytt.list(video_id)
                for t in transcript_list:
                    if t.language_code == 'en':
                        raw = t.fetch()
                        break
                if raw is None:
                    # Take first available and translate
                    for t in transcript_list:
                        raw = t.translate('en').fetch()
                        break
            except Exception:
                pass

        if raw is not None:
            entries = [{"start": s.start, "duration": s.duration, "text": s.text} for s in raw]
            chunks = _chunk_transcript(entries)
            duration = int(entries[-1]['start'] + entries[-1].get('duration', 0)) if entries else 0
            return {
                "title": title,
                "duration": duration,
                "chunks": chunks,
                "video_id": video_id,
            }

    except Exception as e:
        err = str(e).lower()
        if "disabled" in err or "no transcript" in err:
            raise ValueError("This video has no captions available. Please try a video with auto-generated or manual captions.")
        if "private" in err:
            raise ValueError("This video is private and cannot be accessed.")
        # For other errors, fall through to yt-dlp fallback
        pass

    # --- Fallback: yt-dlp (metadata only, no download) ---
    try:
        import yt_dlp

        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if not info:
                raise ValueError("Could not extract video info")
            if info.get("is_live"):
                raise ValueError("Live streams are not supported")

            title = info.get("title", "Unknown")
            duration = info.get("duration", 0)
            chunks = create_fallback_chunks(info)

            return {
                "title": title,
                "duration": duration,
                "chunks": chunks,
                "video_id": info.get("id", video_id),
            }

    except yt_dlp.utils.DownloadError as e:
        err = str(e)
        if "Private video" in err:
            raise ValueError("This video is private and cannot be accessed.")
        elif "not available" in err.lower():
            raise ValueError("This video is not available in your region.")
        elif "Sign in" in err or "bot" in err.lower():
            raise ValueError("YouTube is requiring authentication for this video. Please try a different video.")
        else:
            raise ValueError(f"Could not access video: {err}")


def _get_video_title(video_id: str) -> str:
    """Get video title via oEmbed API — no auth required."""
    try:
        import httpx
        resp = httpx.get(
            f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json",
            timeout=5.0
        )
        if resp.status_code == 200:
            return resp.json().get("title", "Lecture")
    except Exception:
        pass
    return "Lecture"


def _chunk_transcript(raw: List[Dict], chunk_duration: int = 30) -> List[Dict]:
    """Group raw transcript entries into ~30-second chunks."""
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


def create_fallback_chunks(info: Dict) -> List[Dict]:
    """Create basic chunks from description when no captions available."""
    duration = info.get("duration", 300)
    description = info.get("description", "No transcript available for this video.")

    words = description.split()
    if not words:
        return [{"chunk_id": 0, "start_time": 0, "end_time": duration, "text": "No transcript available."}]

    chunk_size = max(50, len(words) // 10)
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk_words = words[i:i + chunk_size]
        start_time = int((i / len(words)) * duration)
        end_time = int(((i + chunk_size) / len(words)) * duration)
        chunks.append({
            "chunk_id": len(chunks),
            "start_time": start_time,
            "end_time": min(end_time, duration),
            "text": " ".join(chunk_words),
        })

    return chunks


def time_to_seconds(time_str: str) -> float:
    """Convert HH:MM:SS.mmm to seconds"""
    parts = time_str.replace(",", ".").split(":")
    hours = float(parts[0])
    minutes = float(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds

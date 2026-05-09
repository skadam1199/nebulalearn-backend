import yt_dlp
import re
from typing import List, Dict

def extract_transcript(url: str) -> List[Dict]:
    """Extract transcript from YouTube video with timestamps"""
    
    ydl_opts = {
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "skip_download": True,
        "quiet": True,
    }

    transcript_chunks = []

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise ValueError("Could not extract video info")
            
            # Check if video is available
            if info.get("is_live"):
                raise ValueError("Live streams are not supported")
            
            title = info.get("title", "Unknown")
            duration = info.get("duration", 0)
            
            # Try to get subtitles
            subtitles = info.get("subtitles", {})
            auto_captions = info.get("automatic_captions", {})
            
            captions = subtitles.get("en") or auto_captions.get("en")
            
            if captions:
                # Get the json3 or vtt format
                caption_url = None
                for fmt in captions:
                    if fmt.get("ext") in ["json3", "vtt"]:
                        caption_url = fmt.get("url")
                        break
                
                if caption_url:
                    import httpx
                    response = httpx.get(caption_url)
                    transcript_chunks = parse_captions(response.text, duration)
            
            if not transcript_chunks:
                # Fallback: create chunks from description or metadata
                transcript_chunks = create_fallback_chunks(info)
            
            return {
                "title": title,
                "duration": duration,
                "chunks": transcript_chunks,
                "video_id": info.get("id", ""),
            }

    except yt_dlp.utils.DownloadError as e:
        if "Private video" in str(e):
            raise ValueError("This video is private and cannot be accessed")
        elif "not available" in str(e).lower():
            raise ValueError("This video is not available")
        else:
            raise ValueError(f"Could not access video: {str(e)}")


def parse_captions(caption_text: str, duration: int) -> List[Dict]:
    """Parse VTT or JSON3 captions into chunks"""
    chunks = []
    
    # VTT format parsing
    if "WEBVTT" in caption_text:
        pattern = r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})\n(.*?)(?=\n\n|\Z)'
        matches = re.findall(pattern, caption_text, re.DOTALL)
        
        current_chunk = {"start_time": 0, "end_time": 0, "text": "", "chunk_id": 0}
        chunk_id = 0
        chunk_duration = 30  # Group into 30-second chunks
        
        for start, end, text in matches:
            start_secs = time_to_seconds(start)
            end_secs = time_to_seconds(end)
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            
            if not clean_text:
                continue
                
            if start_secs - current_chunk["start_time"] > chunk_duration and current_chunk["text"]:
                chunks.append({
                    "chunk_id": chunk_id,
                    "start_time": int(current_chunk["start_time"]),
                    "end_time": int(current_chunk["end_time"]),
                    "text": current_chunk["text"].strip()
                })
                chunk_id += 1
                current_chunk = {"start_time": start_secs, "end_time": end_secs, "text": clean_text + " "}
            else:
                if not current_chunk["text"]:
                    current_chunk["start_time"] = start_secs
                current_chunk["end_time"] = end_secs
                current_chunk["text"] += clean_text + " "
        
        if current_chunk["text"]:
            chunks.append({
                "chunk_id": chunk_id,
                "start_time": int(current_chunk["start_time"]),
                "end_time": int(current_chunk["end_time"]),
                "text": current_chunk["text"].strip()
            })
    
    return chunks


def create_fallback_chunks(info: Dict) -> List[Dict]:
    """Create basic chunks when no captions available"""
    duration = info.get("duration", 300)
    description = info.get("description", "No transcript available for this video.")
    
    # Split description into chunks
    words = description.split()
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
            "text": " ".join(chunk_words)
        })
    
    return chunks


def time_to_seconds(time_str: str) -> float:
    """Convert HH:MM:SS.mmm to seconds"""
    parts = time_str.replace(",", ".").split(":")
    hours = float(parts[0])
    minutes = float(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds
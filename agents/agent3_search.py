import os
import numpy as np
import httpx
from typing import List, Dict

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"


async def embed_text(text: str) -> List[float]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            VOYAGE_URL,
            headers={
                "Authorization": f"Bearer {VOYAGE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "input": [text],
                "model": "voyage-3-lite"
            },
            timeout=30.0
        )
        data = response.json()
        return data["data"][0]["embedding"]


async def embed_chunks(chunks: List[Dict]) -> List[Dict]:
    embedded = []
    for chunk in chunks:
        if len(chunk["text"].split()) < 10:
            continue
        try:
            embedding = await embed_text(chunk["text"])
            embedded.append({**chunk, "embedding": embedding})
        except Exception as e:
            print(f"Embedding failed for chunk {chunk['chunk_id']}: {e}")
            continue
    return embedded


def cosine_similarity(a: List[float], b: List[float]) -> float:
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


async def semantic_search(query: str, embedded_chunks: List[Dict], top_k: int = 3) -> List[Dict]:
    query_embedding = await embed_text(query)
    results = []
    for chunk in embedded_chunks:
        similarity = cosine_similarity(query_embedding, chunk["embedding"])
        results.append({
            "chunk_id": chunk["chunk_id"],
            "start_time": chunk["start_time"],
            "end_time": chunk["end_time"],
            "text": chunk["text"],
            "similarity": round(similarity, 4)
        })
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]
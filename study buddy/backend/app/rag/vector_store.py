import math
import re
from typing import List, Dict, Any

def chunk_text_with_overlap(text: str, page_number: int, chunk_size: int = 600, overlap: int = 120) -> List[Dict[str, Any]]:
    """
    Splits page text into overlapping semantic chunks with page metadata.
    """
    chunks = []
    if not text:
        return chunks

    words = text.split()
    if not words:
        return chunks

    current_chunk = []
    current_length = 0

    for word in words:
        current_chunk.append(word)
        current_length += len(word) + 1

        if current_length >= chunk_size:
            chunk_str = " ".join(current_chunk)
            chunks.append({
                "text": chunk_str,
                "page": page_number
            })
            # Overlap calculation (keep last N words)
            overlap_words = []
            overlap_len = 0
            for w in reversed(current_chunk):
                overlap_words.insert(0, w)
                overlap_len += len(w) + 1
                if overlap_len >= overlap:
                    break
            current_chunk = overlap_words
            current_length = overlap_len

    if current_chunk:
        chunks.append({
            "text": " ".join(current_chunk),
            "page": page_number
        })

    return chunks

class LocalVectorIndex:
    """
    Lightweight, high-performance Term-Vector Cosine Similarity store for RAG.
    """
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r'\b\w+\b', text.lower())

    @staticmethod
    def _get_tf(words: List[str]) -> Dict[str, float]:
        tf = {}
        total = len(words)
        if total == 0:
            return tf
        for w in words:
            tf[w] = tf.get(w, 0) + 1
        for w in tf:
            tf[w] = tf[w] / total
        return tf

    @staticmethod
    def _cosine_similarity(tf1: Dict[str, float], tf2: Dict[str, float]) -> float:
        dot_product = sum(tf1[w] * tf2.get(w, 0) for w in tf1)
        mag1 = math.sqrt(sum(v ** 2 for v in tf1.values()))
        mag2 = math.sqrt(sum(v ** 2 for v in tf2.values()))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot_product / (mag1 * mag2)

    @classmethod
    def search_top_k(cls, query: str, chunks_data: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Searches candidate chunks and returns Top-K most relevant chunks with page & score metadata.
        chunks_data format: [{'id': chunk_id, 'text': text_content, 'page': page_number, 'filename': doc_filename}]
        """
        query_words = cls._tokenize(query)
        if not query_words or not chunks_data:
            return []

        query_tf = cls._get_tf(query_words)
        results = []

        for item in chunks_data:
            chunk_words = cls._tokenize(item["text"])
            chunk_tf = cls._get_tf(chunk_words)
            score = cls._cosine_similarity(query_tf, chunk_tf)

            if score > 0.05:  # Minimum relevance threshold
                results.append({
                    "chunk_id": item.get("id"),
                    "text": item["text"],
                    "page": item.get("page", 1),
                    "filename": item.get("filename", "Document"),
                    "score": round(score, 4)
                })

        # Sort descending by similarity score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

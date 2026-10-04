import os
import re
import math
import json
from typing import List, Dict, Any, Tuple, Optional

from config.settings import settings
from rag.chunker import build_all_chunks
from utils.logger import logger

TOKEN_REGEX = re.compile(r'[\u0B80-\u0BFF]+|[a-zA-Z0-9]+')
TITLE_BONUS = 2.0
ACTIVE_BOOST = 1.1
MAX_TRACKED_IPS = 10000


def tokenize(text: str) -> List[str]:
    # Extract Tamil words, English words and numbers
    if not isinstance(text, str):
        return []
    return TOKEN_REGEX.findall(text.lower())


class HybridRetriever:
    def __init__(self, kb_path: Optional[str] = None):
        self.kb_path = kb_path or settings.KB_PATH
        self.chunks: List[Dict[str, Any]] = []
        self.doc_freqs: Dict[str, int] = {}
        self.doc_lengths: List[int] = []
        self.avg_dl: float = 1.0
        self.tokenized_docs: List[List[str]] = []
        self.aliases: Dict[str, Any] = {}
        self.load_aliases()
        self.build_index()

    def load_aliases(self):
        alias_path = os.path.join(self.kb_path, "aliases", "scheme_aliases.json")
        if os.path.exists(alias_path):
            try:
                with open(alias_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                # Only keep string -> string pairs; anything else is skipped so a
                # future edit to the alias file cannot crash every query.
                self.aliases = {
                    k: v for k, v in (raw or {}).items()
                    if isinstance(k, str) and isinstance(v, str)
                }
            except Exception as e:
                logger.error(f"Error loading scheme aliases: {e}")
                self.aliases = {}
        else:
            logger.warning(f"Alias file not found: {alias_path}")

    def _indexable_text(self, chunk: Dict[str, Any]) -> str:
        parts = [
            chunk.get("content", ""),
            chunk.get("title", ""),
            chunk.get("section", ""),
        ]
        aliases = chunk.get("aliases", [])
        if isinstance(aliases, list):
            parts.extend(str(a) for a in aliases)
        return " ".join(p for p in parts if p)

    def build_index(self):
        self.chunks = build_all_chunks(self.kb_path)
        self.tokenized_docs = [tokenize(self._indexable_text(c)) for c in self.chunks]
        self.doc_lengths = [len(doc) for doc in self.tokenized_docs]
        total_len = sum(self.doc_lengths)
        self.avg_dl = (total_len / len(self.chunks)) if self.chunks else 1.0
        # Guard against a corpus where every document tokenises to nothing.
        if self.avg_dl <= 0:
            self.avg_dl = 1.0

        self.doc_freqs = {}
        for doc in self.tokenized_docs:
            for t in set(doc):
                self.doc_freqs[t] = self.doc_freqs.get(t, 0) + 1

    def bm25_score(self, query_tokens: List[str], doc_idx: int, k1: float = 1.5, b: float = 0.75) -> float:
        doc = self.tokenized_docs[doc_idx]
        if not doc:
            return 0.0
        dl = self.doc_lengths[doc_idx]
        N = len(self.chunks)
        if N == 0:
            return 0.0

        term_counts: Dict[str, int] = {}
        for t in doc:
            term_counts[t] = term_counts.get(t, 0) + 1

        avg_dl = self.avg_dl if self.avg_dl > 0 else 1.0
        score = 0.0
        for q in query_tokens:
            tf = term_counts.get(q)
            if not tf:
                continue
            df = self.doc_freqs.get(q, 0)
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
            denom = tf + k1 * (1.0 - b + b * (dl / avg_dl))
            if denom <= 0:
                continue
            score += idf * ((tf * (k1 + 1.0)) / denom)

        return score

    def _expand_aliases(self, query: str, q_tokens: List[str]) -> List[str]:
        q_lower = query.lower()
        for alias, target_id in self.aliases.items():
            if not alias:
                continue
            # Word-boundary-ish match so a short alias does not fire inside
            # unrelated longer words.
            if re.search(rf"(?<!\w){re.escape(alias.lower())}(?!\w)", q_lower):
                q_tokens.extend(tokenize(target_id))
        return q_tokens

    def retrieve(self, query: str, top_k: int = 5, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.chunks:
            self.build_index()

        q_tokens = tokenize(query)
        q_tokens = self._expand_aliases(query, q_tokens)

        if not q_tokens or not self.chunks:
            return []

        min_score = settings.MIN_RETRIEVAL_SCORE
        top_k = max(1, top_k)

        scored_results: List[Tuple[int, float]] = []
        for i, chunk in enumerate(self.chunks):
            if category_filter and chunk.get("category") != category_filter:
                continue

            score = self.bm25_score(q_tokens, i)
            if score <= 0:
                continue

            # Boost active and verified sources
            if chunk.get("status") == "active":
                score *= ACTIVE_BOOST

            # Exact title / section / alias match bonus
            title_tokens = set(tokenize(chunk.get("title", "")))
            title_tokens |= set(tokenize(chunk.get("section", "")))
            if any(t in title_tokens for t in q_tokens):
                score += TITLE_BONUS

            if score >= min_score:
                scored_results.append((i, score))

        scored_results.sort(key=lambda x: x[1], reverse=True)
        top_candidates = scored_results[:top_k]

        results: List[Dict[str, Any]] = []
        for idx, score in top_candidates:
            c = dict(self.chunks[idx])
            c["score"] = round(float(score), 3)
            results.append(c)

        return results

    def chunks_for_file(self, file_id: str) -> List[Dict[str, Any]]:
        return [c for c in self.chunks if c.get("file_id") == file_id]

    def chunks_for_category(self, category: str) -> List[Dict[str, Any]]:
        return [c for c in self.chunks if c.get("category") == category]


# Shared instance
retriever = HybridRetriever()

# faiss_search.py — CTX-совместимый retrieval с fallback и MMR
import faiss
import pickle
import numpy as np
import re
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from pathlib import Path
from typing import List, Dict, Optional

INDEX_PATH = Path("faiss_index.bin")
META_PATH = Path("faiss_metadata.pkl")

# Константы пайплайна
DEFAULT_TOP_K = 12
CLIP = 450

# --- Lazy loaders ---
@lru_cache(maxsize=1)
def _load_index():
    return faiss.read_index(str(INDEX_PATH))

@lru_cache(maxsize=1)
def _load_meta() -> List[Dict]:
    with META_PATH.open("rb") as f:
        return pickle.load(f)  # ожидается list[dict] с полями: content|text, latin_name, intent?, source?

@lru_cache(maxsize=1)
def _load_model():
    return SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")

# --- Helpers ---
_author_rx = re.compile(r"\b([A-Z][a-z]+|[A-Z]\.|[A-Z][a-z]+\.)$")

def _strip_authors(name: str) -> str:
    # "Aglaonema commutatum Schott" -> "Aglaonema commutatum"
    name = re.sub(r"\s+(var\.|subsp\.|ssp\.)\s+\w+", "", name, flags=re.I)
    parts = name.split()
    if len(parts) >= 3 and _author_rx.search(parts[-1]):
        parts = parts[:-1]
    return " ".join(parts).strip()

def _detect_rank(name: str) -> str:
    return "species" if len(name.split()) >= 2 else "genus"

def _build_queries(latin_name: str):
    rank = _detect_rank(latin_name)
    genus = latin_name.split()[0]
    variants = []
    if rank == "species":
        stripped = _strip_authors(latin_name)
        if stripped != latin_name:
            variants.append(stripped)
        variants.append(latin_name)
        variants.append(genus)  # fallback
    else:
        variants.append(genus)
    # обогащение терминами ухода (recall)
    queries = [f"{q} уход содержание полив свет температура влажность размножение почва" for q in variants]
    return queries, rank, genus

def _to_text_field(item: Dict) -> str:
    if "text" in item and item["text"]:
        return str(item["text"])
    if "content" in item and item["content"]:
        return str(item["content"])
    return ""

def _clip(x: str, n: int = CLIP) -> str:
    if len(x) <= n:
        return x
    cut = x[:n]
    # обрезаем по концу предложения, если он есть в последней трети
    for stop in (". ", "!\n", "?\n", ";\n", "\n\n"):
        pos = cut.rfind(stop)
        if pos > n * 0.6:
            return cut[:pos+1].strip() + "…"
    return cut.rsplit(" ", 1)[0].strip() + "…"

def overlap(a: str, b: str) -> bool:
    # грубая проверка сходства по 5-граммам
    def grams(s): return {s[i:i+5] for i in range(max(0, len(s)-4))}
    ga, gb = grams(a.lower()), grams(b.lower())
    return len(ga & gb) / max(1, len(ga | gb)) > 0.6

# --- API ---
def filter_by_intent(chunks: List[Dict], intent: Optional[str]) -> List[Dict]:
    if not intent or intent.lower() == "general":
        return chunks
    key = intent.strip().lower()
    return [c for c in chunks if str(c.get("intent", "")).lower() == key]

def get_chunks_by_latin_name(
    latin_name: str,
    top_k: int = DEFAULT_TOP_K,
    mode: str = "species",
    intent: Optional[str] = None,
) -> List[Dict]:
    index = _load_index()
    meta = _load_meta()
    model = _load_model()

    if index.ntotal != len(meta):
        raise RuntimeError(f"FAISS/meta mismatch: index.ntotal={index.ntotal} != len(meta)={len(meta)}")

    def _search(_latin: str, _mode: str):
        queries, input_rank, input_genus = _build_queries(_latin)
        q_vecs = model.encode(queries, convert_to_numpy=True).astype("float32")

        over_k = max(top_k * 3, 24)
        D, I = index.search(q_vecs, over_k)

        seen, results = set(), []
        species_key = _strip_authors(_latin).lower()
        genus = _latin.split()[0].lower()

        for row_d, row_i in zip(D, I):
            for score, idx in zip(row_d.tolist(), row_i.tolist()):
                if idx < 0 or idx >= len(meta) or idx in seen:
                    continue
                raw = dict(meta[idx])
                ln = str(raw.get("latin_name", "")).lower()

                if _mode == "genus" and not ln.startswith(genus):
                    continue

                if species_key and species_key in ln:
                    match = "species"
                elif genus and ln.startswith(genus):
                    match = "genus"
                else:
                    match = "none"

                text = _to_text_field(raw).strip()
                if not text:
                    continue

                results.append({
                    "text": _clip(text, CLIP),
                    "latin_name": raw.get("latin_name") or "",
                    "intent": raw.get("intent"),
                    "source": raw.get("source"),
                    "score": float(score),
                    "match": match,
                })
                seen.add(idx)

        # intent-фильтр (если задан и не general)
        if intent and intent.lower() != "general":
            results = [r for r in results if str(r.get("intent", "")).lower() == intent.lower()]

        # предварительная сортировка
        results.sort(key=lambda x: (x["match"] == "species", x["match"] == "genus", x["score"]), reverse=True)

        # MMR-диверсификация по тексту
        selected, used = [], set()
        for r in results:
            txt = r["text"][:200]
            if any(overlap(txt, s) for s in used):
                continue
            selected.append(r)
            used.add(txt)
            if len(selected) >= top_k:
                break
        return selected

    # 1-й проход: species
    results = _search(latin_name, "species")

    # Fallback: если пусто — пробуем по роду
    used_mode = "species"
    if not results:
        used_mode = "species->genus"
        genus = latin_name.split()[0]
        results = _search(genus, "genus")

    try:
        import logging as _lg
        _lg.getLogger("faiss").info(
            f"[FAISS] retrieved_k={len(results)} used_k={min(len(results), top_k)} "
            f"mode={used_mode} intent={intent or '-'} q='{latin_name}'"
        )
    except Exception:
        pass

    return results

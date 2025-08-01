# faiss_search.py — усиленная версия без смены сигнатуры
import faiss
import pickle
import numpy as np
import re
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from pathlib import Path

INDEX_PATH = Path("faiss_index.bin")
META_PATH = Path("faiss_metadata.pkl")

# Lazy load
@lru_cache(maxsize=1)
def _load_index():
    return faiss.read_index(str(INDEX_PATH))

@lru_cache(maxsize=1)
def _load_db():
    with META_PATH.open("rb") as f:
        return pickle.load(f)  # list[dict]: content, latin_name, section, category_type

@lru_cache(maxsize=1)
def _load_model():
    m = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
    return m

_author_rx = re.compile(r"\b([A-Z][a-z]+|[A-Z]\.|[A-Z][a-z]+\.)$")
def _strip_authors(name: str) -> str:
    # грубо: убираем концовки-авторы и интраранговые пометки
    name = re.sub(r"\s+(var\.|subsp\.|ssp\.)\s+\w+", "", name)
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
        # genus fallback последним
        variants.append(genus)
    else:
        variants.append(genus)
    # обогащение русскими терминами ухода
    queries = [f"{q} уход содержание полив свет температура влажность размножение почва" for q in variants]
    return queries, rank, genus

def get_chunks_by_latin_name(latin_name: str, top_k: int = 7, mode: str = "species") -> list[dict]:
    """
    Ищет релевантные чанки по виду (по умолчанию) или по роду (mode='genus').
    Ввод: latin_name (вид или род).
    Вывод: список чанков с полями 'score' и 'match' (species/genus/none).
    """
    index = _load_index()
    db = _load_db()
    model = _load_model()

    # Sanity: индекс и мета должны совпадать по размеру
    if index.ntotal != len(db):
        raise RuntimeError(f"FAISS/meta mismatch: index.ntotal={index.ntotal} != len(meta)={len(db)}")

    # Подготовка запросов
    queries, input_rank, input_genus = _build_queries(latin_name)
    q_vecs = model.encode(queries, convert_to_numpy=True).astype("float32")

    # Overfetch: берём больше, чем top_k, чтобы отфильтровать/пересортировать
    over_k = max(top_k * 3, 20)
    D, I = index.search(q_vecs, over_k)

    seen, results = set(), []
    dropped = 0
    species_key = _strip_authors(latin_name).lower()
    genus = input_genus.lower()

    for row_d, row_i in zip(D, I):
        for score, idx in zip(row_d.tolist(), row_i.tolist()):
            if idx >= len(db):
                dropped += 1
                continue
            if idx in seen:
                continue

            item = dict(db[idx])  # копия
            ln = (item.get("latin_name") or "").lower()

            # Если ищем по роду — жёстко фильтруем только этот род
            if mode == "genus" and not ln.startswith(genus):
                continue

            # Метка совпадения
            if species_key and species_key in ln:
                match = "species"
            elif genus and ln.startswith(genus):
                match = "genus"
            else:
                match = "none"

            item["score"] = float(score)
            item["match"] = match
            results.append(item)
            seen.add(idx)

    # Приоритизация: species → genus → по score
    results.sort(key=lambda x: (x["match"] == "species", x["match"] == "genus", x["score"]), reverse=True)

    # Диагностический лог (оставь, если у тебя есть logger)
    try:
        import logging as _lg
        _lg.getLogger("faiss").debug(f"[FAISS] dropped={dropped} kept={len(results)} mode={mode} q='{latin_name}'")
    except Exception:
        pass

    return results[:top_k]

import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path

# Пути к индексам
INDEX_PATH = Path("faiss_index.bin")
META_PATH = Path("faiss_metadata.pkl")

# Загрузка FAISS-индекса
index = faiss.read_index(str(INDEX_PATH))

# Загрузка метаданных
with META_PATH.open("rb") as f:
    db = pickle.load(f)  # это list[dict], где каждый dict = {"content", "latin_name", ...}

# Загрузка модели
model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")


def get_chunks_by_latin_name(latin_name: str, top_k: int = 7) -> list[dict]:
    """Ищет наиболее релевантные чанки по латинскому названию"""
    query_vector = model.encode([latin_name])
    D, I = index.search(np.array(query_vector).astype("float32"), top_k)

    results = []
    for i in I[0]:
        if i < len(db):
            results.append(db[i])  # каждый — dict с content, latin_name, section, category_type

    return results

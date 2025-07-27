import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

# Загрузка модели и индекса
model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
index = faiss.read_index("faiss_index.bin")

with open("faiss_metadata.pkl", "rb") as f:
    db = pickle.load(f)

def get_chunks_by_latin_name(latin_name: str, top_k: int = 7) -> list[str]:
    query_vector = model.encode([latin_name])
    D, I = index.search(np.array(query_vector).astype("float32"), top_k)

    return [db["texts"][i] for i in I[0] if i < len(db["texts"])]

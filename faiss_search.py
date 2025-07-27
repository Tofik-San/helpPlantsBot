from sentence_transformers import SentenceTransformer

model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
def get_chunks_by_latin_name(latin_name: str, top_k: int = 30) -> list[str]:
    query_vector = model.encode([latin_name])
    D, I = index.search(np.array(query_vector).astype("float32"), top_k)

    results = []
    for i in I[0]:
        if i < len(db["texts"]):
            meta = db["metas"][i]
            if meta["latin_name"].lower() == latin_name.lower():
                results.append(db["texts"][i])
    return results

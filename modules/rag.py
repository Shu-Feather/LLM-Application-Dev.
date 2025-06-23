# Provides RAG retriever using SentenceTransformers + FAISS
import os
import json
from sentence_transformers import SentenceTransformer
import faiss

class RAGRetriever:
    def __init__(self, embedding_model_name: str = None, index_prefix: str = None):
        model_name = embedding_model_name or os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.docs = []
        self.index_prefix = index_prefix
        if index_prefix:
            try:
                self._load_index(index_prefix)
            except Exception:
                pass

    def build_index(self, documents: list):
        texts = [d['text'] for d in documents]
        emb = self.model.encode(texts, convert_to_numpy=True)
        dim = emb.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(emb)
        self.index = index
        self.docs = documents
        if self.index_prefix:
            self._save_index(self.index_prefix)

    def _save_index(self, prefix: str):
        faiss.write_index(self.index, f"{prefix}.index")
        with open(f"{prefix}.docs.json", 'w', encoding='utf-8') as f:
            json.dump(self.docs, f, ensure_ascii=False, indent=2)

    def _load_index(self, prefix: str):
        self.index = faiss.read_index(f"{prefix}.index")
        with open(f"{prefix}.docs.json", 'r', encoding='utf-8') as f:
            self.docs = json.load(f)

    def retrieve(self, query: str, top_k: int = None) -> list:
        if self.index is None:
            return []
        k = top_k or int(os.getenv('RAG_TOP_K', 5))
        q_emb = self.model.encode([query], convert_to_numpy=True)
        D, I = self.index.search(q_emb, k)
        results = []
        for idx in I[0]:
            if idx < len(self.docs): results.append(self.docs[idx])
        return results

def augment_query_with_rag(query: str, retriever: RAGRetriever) -> str:
    top = retriever.retrieve(query, top_k=3)
    context = "\n".join([f"- {d['text']}" for d in top])
    return f"参考以下领域文档回答：\n{context}\n问题：{query}"
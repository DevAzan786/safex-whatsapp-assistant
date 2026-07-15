import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import chromadb
from sentence_transformers import SentenceTransformer

from app.config import settings


def main():
    print(f"Loading dataset from {settings.faq_dataset_path} ...")
    with open(settings.faq_dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    faqs = data["faqs"]
    print(f"Loaded {len(faqs)} FAQ entries.")

    print(f"Loading embedding model: {settings.embedding_model_name} ...")
    embedder = SentenceTransformer(settings.embedding_model_name)

    print(f"Connecting to ChromaDB at {settings.chroma_persist_dir} ...")
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

    # Fresh start each run to avoid stale/duplicate entries when the
    # dataset changes
    try:
        client.delete_collection(settings.chroma_collection_name)
        print("Cleared existing collection.")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    ids, documents, embeddings, metadatas = [], [], [], []

    for faq in faqs:
        # Embed the question text + keywords to capture semantic variations
        keywords_list = faq.get("keywords", [])
        text_to_embed = faq["question"]
        if keywords_list:
            text_to_embed += " " + " ".join(keywords_list)
            
        embedding = embedder.encode(text_to_embed).tolist()

        ids.append(faq["id"])
        documents.append(faq["question"])
        embeddings.append(embedding)
        metadatas.append(
            {
                "category": faq["category"],
                "answer": faq["answer"],
                "keywords": ", ".join(keywords_list),
            }
        )

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(f"Ingested {len(ids)} FAQs into ChromaDB collection '{settings.chroma_collection_name}'.")
    print(f"Collection now contains {collection.count()} documents.")


if __name__ == "__main__":
    main()

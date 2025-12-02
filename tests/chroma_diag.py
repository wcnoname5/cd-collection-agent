"""
chroma_diag.py — Minimal diagnostic + CLI vector search tester.

Purpose:
1. Verify Chroma loads correctly.
2. Verify embeddings exist.
3. Test real vector search performance.
4. Provide a simple CLI to query the vector store.

Usage:
    python chroma_diag.py
    > jazz piano
    > experimental rock
    > quit
"""

from pathlib import Path
import time

CHROMA_PATH = Path("data") / "chroma"
COLLECTION_NAME = "cds"


def main():
    # ------------------------------
    # 1. Import required modules
    # ------------------------------
    try:
        import chromadb
    except Exception:
        raise SystemExit("Install chromadb: pip install chromadb")

    from sentence_transformers import SentenceTransformer

    # ------------------------------
    # 2. Load ChromaDB
    # ------------------------------
    print("Loading Chroma...")
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    coll = client.get_or_create_collection(COLLECTION_NAME)

    print(f"Collection name: {COLLECTION_NAME}")
    print("Total items:", coll.count())

    # ------------------------------
    # 3. Sample raw stored data (not vector search)
    # ------------------------------
    # sample = coll.get(limit=5)
    # print("\nStored sample:")
    # print("ids:", sample.get("ids"))
    # print("documents:", sample.get("documents"))
    # print("metadatas:", sample.get("metadatas"))

    # ------------------------------
    # 4. Load embedding model
    # ------------------------------
    print("\nLoading embedding model...")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    # ------------------------------
    # 5. Vector search CLI
    # ------------------------------
    print("\nVector Search CLI: Type your music-related query.")
    print("Example: jazz fusion, piano trio, psychedelic rock, etc.")
    print("Type 'quit' to exit.\n")

    while True:
        query = input("> ").strip()

        if query.lower() in {"quit", "exit"}:
            print("Exiting.")
            break

        if not query:
            continue

        # ------------------------------
        # 6. Embed user query
        # ------------------------------
        start_emb = time.time()
        q_emb = model.encode([query])[0]
        emb_time = time.time() - start_emb

        # ------------------------------
        # 7. Perform vector search
        # ------------------------------
        start_search = time.time()
        res = coll.query(
            query_embeddings=[q_emb],
            n_results=5
        )
        search_time = time.time() - start_search

        # ------------------------------
        # 8. Print results
        # ------------------------------
        print(f"\nEmbedding time: {emb_time:.4f}s")
        print(f"Search time:    {search_time:.4f}s")
        print("Top results:")

        ids = res["ids"][0]
        docs = res["documents"][0]
        metas = res["metadatas"][0]

        for i in range(len(ids)):
            meta = metas[i] if metas else {}
            print(f"  {i+1}.")
            print(f"     id:       {ids[i]}")
            print(f"     document: {docs[i]}")
            if meta:
                print("     metadata:", meta)

        print()

    print("Done.")


if __name__ == "__main__":
    main()

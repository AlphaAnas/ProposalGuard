from src.state import GraphState
from src.vectorStore import ProposalVectorStore

vector_db = ProposalVectorStore()


def retrieve_context(state: GraphState) -> dict:
    resume_text = state.get("resume_text", "")
    job_description = state.get("job_description", "")

    print(f"[Retrieve] Job description (first 80 chars): {job_description[:80]}...")

    # 1. Start with the resume text as the primary context
    context_docs = [resume_text] if resume_text else []

    # 2. Fetch relevant past proposals with similarity scores
    retrieval_results = []

    if job_description:
        print("[Retrieve] Fetching relevant past proposals from Vector DB...")

        # Use similarity_search_with_score instead of retriever
        # This gives us the actual similarity scores for transparency
        results_with_scores = vector_db.vector_store.similarity_search_with_score(
            job_description, k=3
        )

        for doc, score in results_with_scores:
            context_docs.append(doc.page_content)

            # Build a transparency record for each retrieved doc
            retrieval_results.append({
                "text": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "full_text": doc.page_content,
                "score": round(1 - score, 3),  # Chroma returns distance, convert to similarity
                "source": doc.metadata.get("filename", doc.metadata.get("source", "unknown")),
                "metadata": doc.metadata,
            })

        print(f"[Retrieve] Found {len(results_with_scores)} past proposal(s)")
        for r in retrieval_results:
            print(f"  → {r['source']} (similarity: {r['score']})")

    print(f"[Retrieve] Total context: 1 resume + {len(retrieval_results)} proposals")

    return {
        "retrieved_context": context_docs,
        "retrieval_results": retrieval_results,
        "status": "retrieved",
    }
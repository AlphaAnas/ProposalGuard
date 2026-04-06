from src.state import GraphState
from src.vectorStore import ProposalVectorStore

# Initialize the vector store once (or manage its lifecycle appropriately)
# In a production app, this might be a singleton or passed through config.
vector_db = ProposalVectorStore()

def retrieve_context(state: GraphState) -> dict:
    resume_text = state.get("resume_text", "")
    job_description = state.get("job_description", "")

    print(f"[Retrieve] Job description (first 80 chars): {job_description[:80]}...")

    # 1. Start with the resume text as the primary context.
    context_docs = [resume_text] if resume_text else []
    
    # 2. Fetch relevant past proposals from the Vector DB
    if job_description:
        print("[Retrieve] Fetching relevant past proposals from Vector DB...")
        retriever = vector_db.get_retriever(num_results=2)
        past_proposals = retriever.invoke(job_description)
        
        for doc in past_proposals:
            context_docs.append(doc.page_content)
            
        print(f"[Retrieve] Added {len(past_proposals)} past proposal(s) from Vector DB")

    print(f"[Retrieve] Total context documents: {len(context_docs)} (1 resume + {len(context_docs)-1 if resume_text else len(context_docs)} from DB)")

    return {
        "retrieved_context": context_docs,
        "draft_proposal": state.get("draft_proposal", None),
        "grounding_score": state.get("grounding_score", 0.0),
        "bias_flags": state.get("bias_flags", []),
        "retry_count": state.get("retry_count", 0),
        "human_feedback": state.get("human_feedback", None),
        "status": "retrieved",
    }
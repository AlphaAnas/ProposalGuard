from src.state import GraphState


def retrieve_context(state: GraphState) -> dict:
    resume_text = state.get("resume_text", "")
    job_description = state.get("job_description", "")

    print(f"[Retrieve] Job description (first 80 chars): {job_description[:80]}...")

    # Use the resume text as the primary context for proposal generation.
    # Split into chunks for readability; treat the whole resume as one doc.
    context_docs = [resume_text] if resume_text else []

    print(f"[Retrieve] Loaded {len(context_docs)} context document(s) from resume")

    return {
        "retrieved_context": context_docs,
        "draft_proposal": state.get("draft_proposal", None),
        "grounding_score": state.get("grounding_score", 0.0),
        "bias_flags": state.get("bias_flags", []),
        "retry_count": state.get("retry_count", 0),
        "human_feedback": state.get("human_feedback", None),
        "status": "retrieved",
    }
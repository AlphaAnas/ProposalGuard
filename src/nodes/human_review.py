from src.state import GraphState


def human_review(state: GraphState) -> dict:
    score = state.get("grounding_score", 0.0)
    retry = state.get("retry_count", 0)

    print(f"[Review] Proposal ready (score: {score}, attempt #{retry + 1})")
    print("[Review] APPROVED — auto-approving for API flow")

    # Auto-approve: in a real system this would be a human-in-the-loop interrupt
    return {
        "human_feedback": None,
        "status": "approved",
    }
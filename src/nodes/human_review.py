from src.state import GraphState


def human_review(state: GraphState) -> dict:
    score = state.get("grounding_score", 0.0)
    retry = state.get("retry_count", 0)

    print(f"[Review] Proposal ready (score: {score}, attempt #{retry + 1})")

    if retry < 2:
        feedback = "Add specific technologies and a timeline"
        print(f"[Review] REJECTED — {feedback}")
        return {
            "human_feedback": feedback,
            "status": "rejected",
        }
    else:
        print("[Review] APPROVED")
        return {
            "human_feedback": None,
            "status": "approved",
        }
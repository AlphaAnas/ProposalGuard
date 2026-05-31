from langgraph.types import interrupt
from src.state import GraphState


def human_review(state: GraphState) -> dict:
    score = state.get("grounding_score", 0.0)
    retry = state.get("retry_count", 0)
    proposal = state.get("draft_proposal", "")
    bias_flags = state.get("bias_flags", [])
    bias_evaluation = state.get("bias_evaluation", {})

    print(f"[Review] Proposal ready (score: {score}, attempt #{retry + 1})")

    # interrupt() pauses the pipeline here.
    # Everything we pass gets sent to the frontend.
    # When the user approves/rejects, Command(resume=...) returns their decision.
    user_decision = interrupt({
        "proposal": proposal,
        "grounding_score": score,
        "bias_flags": bias_flags,
        "bias_evaluation": bias_evaluation,
        "retry_count": retry,
        "message": "Please review the proposal and approve or reject with feedback.",
    })

    action = user_decision.get("action", "approve")
    feedback = user_decision.get("feedback", None)

    if action == "approve":
        print("[Review] APPROVED by human")
        return {
            "human_feedback": None,
            "status": "approved",
        }
    else:
        print(f"[Review] REJECTED — feedback: {feedback}")
        return {
            "human_feedback": feedback,
            "status": "rejected",
        }
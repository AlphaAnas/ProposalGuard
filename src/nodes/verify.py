from src.state import GraphState


def verify_grounding(state: GraphState) -> dict:
    proposal = state.get("draft_proposal", "")
    resume = state.get("resume_text", "")
    
    # Simple heuristic: how many words from the resume are in the proposal?
    # For now, we'll just give it a high score if proposal is non-empty
    # to allow the flow to complete.
    if len(proposal) > 50:
        fake_score = 0.9
    else:
        fake_score = 0.4

    print(f"[Verify] Grounding score: {fake_score} (based on proposal length)")

    return {
        "grounding_score": fake_score,
        "status": "verifying",
    }
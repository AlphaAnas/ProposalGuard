from src.state import GraphState


def verify_grounding(state: GraphState) -> dict:
    retry = state.get("retry_count", 0)

    fake_score = 0.6 if retry == 0 else 0.85

    print(f"[Verify] Grounding score: {fake_score}")

    return {
        "grounding_score": fake_score,
        "status": "verifying",
    }
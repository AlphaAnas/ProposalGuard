from src.state import GraphState


def generate_proposal(state: GraphState) -> dict:
    context = state["retrieved_context"]
    retry = state.get("retry_count", 0)
    feedback = state.get("human_feedback", None)

    print(f"[Generate] Drafting proposal (attempt #{retry + 1})")
    if feedback:
        print(f"[Generate] Incorporating feedback: {feedback}")

    fake_proposal = (
        f"Dear Client,\n\n"
        f"I've reviewed your requirements and I'm confident I can deliver. "
        f"Based on {len(context)} similar projects in my portfolio, "
        f"I have the exact experience you need.\n\n"
        f"This is attempt #{retry + 1}."
    )

    return {
        "draft_proposal": fake_proposal,
        "status": "draft",
    }
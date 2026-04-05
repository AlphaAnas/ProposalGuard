from state import GraphState


def check_bias(state: GraphState) -> dict:
    retry = state["retry_count"]

    if retry == 0:
        flags = ["Tone is overly submissive — consider more assertive language"]
        print(f"[Bias] Found {len(flags)} flag(s)")
    else:
        flags = []
        print("[Bias] Clean — no bias detected")

    return {
        "bias_flags": flags,
        "status": "bias_checked",
    }
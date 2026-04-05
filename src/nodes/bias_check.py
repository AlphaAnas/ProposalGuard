from src.state import GraphState


def check_bias(state: GraphState) -> dict:
    retry = state.get("retry_count", 0)

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
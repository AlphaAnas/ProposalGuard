from src.state import GraphState


def check_bias(state: GraphState) -> dict:
    proposal = state.get("draft_proposal", "")
    
    # Simple heuristic: no bias if proposal is non-empty for now
    flags = []
    
    # Example placeholder: if proposal is very short, flag it
    if len(proposal) > 0 and len(proposal) < 100:
        flags.append("Proposal is too short — consider adding more detail")

    if flags:
        print(f"[Bias] Found {len(flags)} flag(s)")
    else:
        print("[Bias] Clean — no bias detected")

    return {
        "bias_flags": flags,
        "status": "bias_checked",
    }
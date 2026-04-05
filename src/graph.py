from langgraph.graph import StateGraph, START, END
from state import GraphState
from nodes.retrieve import retrieve_context
from nodes.generate import generate_proposal
from nodes.verify import verify_grounding
from nodes.bias_check import check_bias
from nodes.human_review import human_review

GROUNDING_THRESHOLD = 0.7
MAX_RETRIES = 3


def route_after_verification(state: GraphState) -> str:
    if state["grounding_score"] >= GROUNDING_THRESHOLD:
        return "pass"
    return "fail"


def route_after_bias(state: GraphState) -> str:
    if len(state["bias_flags"]) == 0:
        return "clean"
    return "flagged"


def route_after_human(state: GraphState) -> str:
    if state["human_feedback"] is None:
        return "approved"
    return "rejected"


def increment_retry(state: GraphState) -> dict:
    new_count = state["retry_count"] + 1
    print(f"[Retry] {state['retry_count']} -> {new_count}")
    return {"retry_count": new_count}


def route_after_retry(state: GraphState) -> str:
    if state["retry_count"] >= MAX_RETRIES:
        return "force_review"
    return "regenerate"

workflow = StateGraph(GraphState)

workflow.add_node("retrieve", retrieve_context)
workflow.add_node("generate", generate_proposal)
workflow.add_node("verify", verify_grounding)
workflow.add_node("bias_check", check_bias)
workflow.add_node("human_review", human_review)
workflow.add_node("increment_retry", increment_retry)

workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", "verify")

workflow.add_conditional_edges("verify", route_after_verification, {
    "pass": "bias_check",
    "fail": "increment_retry",
})

workflow.add_conditional_edges("bias_check", route_after_bias, {
    "clean": "human_review",
    "flagged": "increment_retry",
})

workflow.add_conditional_edges("increment_retry", route_after_retry, {
    "regenerate": "generate",
    "force_review": "human_review",
})

workflow.add_conditional_edges("human_review", route_after_human, {
    "approved": END,
    "rejected": "increment_retry",
})

graph = workflow.compile()
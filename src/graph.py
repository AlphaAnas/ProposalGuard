from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from src.state import GraphState
from src.nodes.retrieve import retrieve_context
from src.nodes.generate import generate_proposal
from src.nodes.verify import verify_grounding
from src.nodes.bias_check import check_bias
from src.nodes.human_review import human_review

GROUNDING_THRESHOLD = 0.5
MAX_RETRIES = 3


def route_after_verification(state: GraphState) -> str:
    score = state.get("grounding_score", 0.0)
    if score >= GROUNDING_THRESHOLD:
        return "pass"
    return "fail"


def route_after_bias(state: GraphState) -> str:
    flags = state.get("bias_flags", [])
    if len(flags) == 0:
        return "clean"
    return "flagged"


def route_after_human(state: GraphState) -> str:
    feedback = state.get("human_feedback", None)
    if feedback is None:
        return "approved"
    return "rejected"


def increment_retry(state: GraphState) -> dict:
    current_count = state.get("retry_count", 0)
    new_count = current_count + 1
    print(f"[Retry] {current_count} -> {new_count}")
    return {"retry_count": new_count}


def route_after_retry(state: GraphState) -> str:
    retry_count = state.get("retry_count", 0)
    if retry_count >= MAX_RETRIES:
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
    "flagged": "human_review",
})

workflow.add_conditional_edges("increment_retry", route_after_retry, {
    "regenerate": "generate",
    "force_review": "human_review",
})

workflow.add_conditional_edges("human_review", route_after_human, {
    "approved": END,
    "rejected": "increment_retry",
})

# MemorySaver stores graph state at each step so the pipeline
# can pause at interrupt() and resume later with the same state.
checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)
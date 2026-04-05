from typing import TypedDict, Optional


class GraphState(TypedDict):
    rfp_text: str
    retrieved_context: list[str]
    draft_proposal: Optional[str]
    grounding_score: float
    bias_flags: list[str]
    human_feedback: Optional[str]
    retry_count: int
    status: str
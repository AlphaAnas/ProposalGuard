from typing import TypedDict, Optional


class GraphState(TypedDict):
    # --- Input ---
    rfp_text: str
    job_description: str
    resume_text: str

    # --- Node 01: Retrieve ---
    retrieved_context: list[str]
    retrieval_results: list[dict]  # [{"text": "...", "score": 0.87, "source": "proposal_02.txt"}, ...]

    # --- Node 02: Generate ---
    draft_proposal: Optional[str]
    generation_metadata: dict  # {"model": "...", "attempt": 2, "feedback_used": "...", "prompt_length": 1234}

    # --- Node 03: Verify ---
    grounding_score: float
    extracted_claims: list[str]     # all claims found in proposal
    supported_claims: list[str]     # claims backed by source docs
    unsupported_claims: list[str]   # hallucinated claims

    # --- Node 04: Bias ---
    bias_flags: list[str]
    bias_evaluation: dict  # full A/B test results — profiles, scores, comparisons

    # --- Node 05: Human Review ---
    baseline_profile: dict
    human_feedback: Optional[str]

    # --- Control ---
    retry_count: int
    status: str
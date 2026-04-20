from src.graph import graph


def run_proposal_pipeline(job_description: str, resume_text: str, rfp_text: str = ""):
    initial_state = {
        "rfp_text": rfp_text or job_description,
        "job_description": job_description,
        "resume_text": resume_text,
        "retrieved_context": [],
        "retrieval_results": [],
        "draft_proposal": None,
        "generation_metadata": {},
        "grounding_score": 0.0,
        "extracted_claims": [],
        "supported_claims": [],
        "unsupported_claims": [],
        "bias_flags": [],
        "bias_evaluation": {},
        "baseline_profile": {},
        "human_feedback": None,
        "retry_count": 0,
        "status": "new",
    }
    return graph.invoke(initial_state)
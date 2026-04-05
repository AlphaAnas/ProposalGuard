from src.graph import graph


def run_proposal_pipeline(job_description: str, resume_text: str, rfp_text: str = ""):
    """
    Executes the proposal generation pipeline.
    - job_description: the job posting / RFP the user wants to apply to
    - resume_text:     the raw text content of the user's resume
    - rfp_text:        optional alias for job_description (kept for compatibility)
    Returns the final state of the graph.
    """
    initial_state = {
        "rfp_text": rfp_text or job_description,
        "job_description": job_description,
        "resume_text": resume_text,
        "retrieved_context": [],
        "draft_proposal": None,
        "grounding_score": 0.0,
        "bias_flags": [],
        "human_feedback": None,
        "retry_count": 0,
        "status": "new",
    }
    return graph.invoke(initial_state)


def main():
    import os

    test_rfp = (
        "Looking for a senior full-stack developer to build an AI-powered "
        "customer support dashboard. Tech stack: Next.js, TypeScript, "
        "Tailwind, Supabase. Must have experience with real-time features "
        "and AI/LLM integration. Budget: $15-20k. Timeline: 8 weeks."
    )

    # Load resume from default location
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resume_path = os.path.join(base_dir, "data", "resumes", "user_resume.txt")
    if os.path.exists(resume_path):
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_text = f.read()
    else:
        resume_text = "No resume found."

    print("=" * 50)
    print("ProposalGuard — Pipeline Run")
    print("=" * 50)

    final_state = run_proposal_pipeline(
        job_description=test_rfp,
        resume_text=resume_text,
    )

    print("=" * 50)
    print(f"Status:    {final_state['status']}")
    print(f"Retries:   {final_state['retry_count']}")
    print(f"Score:     {final_state['grounding_score']}")
    print(f"Bias:      {final_state['bias_flags']}")
    print(f"Proposal:\n{final_state['draft_proposal']}")


if __name__ == "__main__":
    main()

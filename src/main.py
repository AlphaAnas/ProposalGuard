from src.graph import graph 



def run_proposal_pipeline(rfp_text: str):
    """
    Executes the proposal generation pipeline for a given RFP text.
    Returns the final state of the graph.
    """
    initial_state = {
        "rfp_text": rfp_text,
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
    test_rfp = (
        "Looking for a senior full-stack developer to build an AI-powered "
        "customer support dashboard. Tech stack: Next.js, TypeScript, "
        "Tailwind, Supabase. Must have experience with real-time features "
        "and AI/LLM integration. Budget: $15-20k. Timeline: 8 weeks."
    )

    print("=" * 50)
    print("ProposalGuard — Pipeline Run")
    print("=" * 50)

    final_state = run_proposal_pipeline(test_rfp)

    print("=" * 50)
    print(f"Status:    {final_state['status']}")
    print(f"Retries:   {final_state['retry_count']}")
    print(f"Score:     {final_state['grounding_score']}")
    print(f"Bias:      {final_state['bias_flags']}")
    print(f"Proposal:  {final_state['draft_proposal']}")


if __name__ == "__main__":
    main()



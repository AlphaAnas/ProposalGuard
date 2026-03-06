from graph import graph


def main():
    test_rfp = (
        "Looking for a senior full-stack developer to build an AI-powered "
        "customer support dashboard. Tech stack: Next.js, TypeScript, "
        "Tailwind, Supabase. Must have experience with real-time features "
        "and AI/LLM integration. Budget: $15-20k. Timeline: 8 weeks."
    )

    initial_state = {
        "rfp_text": test_rfp,
        "retrieved_context": [],
        "draft_proposal": None,
        "grounding_score": 0.0,
        "bias_flags": [],
        "human_feedback": None,
        "retry_count": 0,
        "status": "new",
    }

    print("=" * 50)
    print("ProposalGuard — Pipeline Run")
    print("=" * 50)

    final_state = graph.invoke(initial_state)

    print("=" * 50)
    print(f"Status:    {final_state['status']}")
    print(f"Retries:   {final_state['retry_count']}")
    print(f"Score:     {final_state['grounding_score']}")
    print(f"Bias:      {final_state['bias_flags']}")
    print(f"Proposal:  {final_state['draft_proposal']}")


if __name__ == "__main__":
    main()
from state import GraphState


def retrieve_context(state: GraphState) -> dict:
    print(f"[Retrieve] Received RFP: {state['rfp_text'][:80]}...")

    fake_docs = [
        "Past proposal for e-commerce site rebuild — React/Next.js, $8k, 4 weeks",
        "Portfolio: Built SaaS dashboard with real-time analytics for fintech startup",
        "Past proposal for AI chatbot integration — RAG pipeline, $12k, 6 weeks",
    ]

    print(f"[Retrieve] Found {len(fake_docs)} relevant documents")

    return {
        "retrieved_context": fake_docs,
        "status": "retrieved",
    }
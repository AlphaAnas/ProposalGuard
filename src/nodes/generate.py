import os
from groq import Groq
from langchain_core.prompts import PromptTemplate
from src.state import GraphState

_GROQ_MODEL = "openai/gpt-oss-120b"
_groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def generate_proposal(state: GraphState) -> dict:
    context = state.get("retrieved_context", [])
    job_description = state.get("job_description", "")
    retry = state.get("retry_count", 0)
    feedback = state.get("human_feedback", None)

    print(f"[Generate] Drafting proposal with Groq (attempt #{retry + 1})")
    if feedback:
        print(f"[Generate] Incorporating feedback: {feedback}")

    # Distinguish between resume and past proposals in the context
    resume_content = context[0] if context else "No resume available."
    past_proposals = context[1:] if len(context) > 1 else []

    past_proposals_text = (
        "\n\n---\n\n".join(past_proposals) if past_proposals else "No past proposals found."
    )

    print(f"[Generate] Context: 1 resume + {len(past_proposals)} past proposals")

    feedback_section = (
        f"\n\nPrevious feedback to incorporate:\n{feedback}" if feedback else ""
    )

    prompt = PromptTemplate.from_template(
        "You are writing a freelance proposal on behalf of the applicant below. "
        "Your job is to win the contract by being specific, credible, and human.\n\n"
        "STRICT RULES:\n"
        "1. Every claim you make MUST come from either the Resume or the Past Proposals below. "
        "If a skill, project, metric, or technology is not mentioned in those documents, DO NOT include it. "
        "Hallucinating experience is worse than being vague.\n"
        "2. Reference specific projects by name, specific metrics with numbers, and specific technologies. "
        "\"I have experience with databases\" is bad. \"I designed a PostgreSQL schema handling 50M+ daily transactions at Stripe\" is good.\n"
        "3. Open with a line that proves you read the job posting — reference a specific requirement or challenge they mentioned.\n"
        "4. Keep it under 4 short paragraphs. No headers, no bullet points, no \"Dear Hiring Manager.\" "
        "Write like a confident professional sending a message, not filling out a form.\n"
        "5. End with a concrete next step: what you'd do in the first 48 hours, or a specific question about their project.\n"
        "6. Match the energy of the job posting. If they're casual, be casual. If they're formal, be formal.\n"
        "7. Never use these words: \"passionate\", \"leverage\", \"synergy\", \"utilize\", \"cutting-edge\", \"seasoned\".\n\n"
        "Job Posting:\n{job_description}\n\n"
        "Applicant Resume:\n{resume_text}\n\n"
        "Past Relevant Proposals (real work the applicant has done — reference these):\n{past_proposals_text}\n"
        "{feedback_section}\n\n"
        "Write the proposal now. No preamble, no \"Here's the proposal\" — just the proposal text itself."
    )

    filled_prompt = prompt.format(
        job_description=job_description,
        resume_text=resume_content,
        past_proposals_text=past_proposals_text,
        feedback_section=feedback_section,
    )

    response = _groq_client.chat.completions.create(
        model=_GROQ_MODEL,
        temperature=0.7,
        messages=[{"role": "user", "content": filled_prompt}],
    )
    proposal_text = response.choices[0].message.content.strip()

    # Collect token usage if available
    usage = response.usage
    token_info = {}
    if usage:
        token_info = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }

    print(f"[Generate] Proposal generated ({len(proposal_text)} chars)")

    return {
        "draft_proposal": proposal_text,
        "generation_metadata": {
            "model": _GROQ_MODEL,
            "attempt": retry + 1,
            "feedback_used": feedback,
            "prompt_length": len(filled_prompt),
            "proposal_length": len(proposal_text),
            "past_proposals_used": len(past_proposals),
            "tokens": token_info,
        },
        "status": "draft",
    }
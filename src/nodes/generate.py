import os
# from langchain_google_genai import ChatGoogleGenerativeAI
from groq import Groq
from langchain_core.prompts import PromptTemplate
from src.state import GraphState
from src.config import Config


# # Initialize Gemini once at module level (re-enable when ready)
# _llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash-lite",
#     temperature=0.7,
#     api_key=Config.GOOGLE_API_KEY,
# )

# Using Groq llama for now
_GROQ_MODEL = "openai/gpt-oss-120b"
_groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def generate_proposal(state: GraphState) -> dict:
    context = state.get("retrieved_context", [])
    job_description = state.get("job_description", "")
    retry = state.get("retry_count", 0)
    feedback = state.get("human_feedback", None)

    print(f"[Generate] Drafting proposal with Groq llama (attempt #{retry + 1})")
    if feedback:
        print(f"[Generate] Incorporating feedback: {feedback}")

    # Distinguish between resume and past proposals in the context
    resume_content = context[0] if context else "No resume available."
    past_proposals = context[1:] if len(context) > 1 else []

    past_proposals_text = (
        "\n\n---\n\n".join(past_proposals) if past_proposals else "No past proposals found."
    )

    if past_proposals:
        print(f"[SAMPLE] {past_proposals[0][:120]}...")

    print(f"[Generate] context size: {len(context)} (1 resume + {len(past_proposals)} past proposals)")

    feedback_section = (
        f"\n\nPrevious feedback to incorporate:\n{feedback}" if feedback else ""
    )

    prompt = PromptTemplate.from_template(
        "You are an expert freelance proposal writer. Your task is to write a highly "
        "converting, concise cover letter / proposal for the job below.\n\n"
        "RULES:\n"
        "1. Ground the proposal in the Applicant Resume AND the Past Relevant Proposals. "
        "Both are real evidence of the applicant's work — use specific details, numbers, "
        "and technologies from either source where relevant to the job.\n"
        "2. Do NOT invent experience that does not appear in either the resume or the past proposals.\n"
        "3. Keep it professional, conversational, and under 4 short paragraphs.\n"
        "4. Avoid generic buzzwords. Be specific and reference real project details.\n"
        "5. End with a clear call to action.\n\n"
        "Job Description:\n{job_description}\n\n"
        "Applicant Resume:\n{resume_text}\n\n"
        "Past Relevant Proposals (real past work — use these details):\n{past_proposals_text}"
        "{feedback_section}\n\n"
        "Proposal:"
    )

    filled_prompt = prompt.format(
        job_description=job_description,
        resume_text=resume_content,
        past_proposals_text=past_proposals_text,
        feedback_section=feedback_section,
    )

    # # LangChain chain (re-enable with Gemini when ready)
    # chain = prompt | _llm
    # response = chain.invoke({
    #     "job_description": job_description,
    #     "resume_text": resume_content,
    #     "past_proposals_text": past_proposals_text,
    #     "feedback_section": feedback_section,
    # })
    # proposal_text = response.content

    response = _groq_client.chat.completions.create(
        model=_GROQ_MODEL,
        temperature=0.7,
        messages=[{"role": "user", "content": filled_prompt}],
    )
    proposal_text = response.choices[0].message.content.strip()

    print(f"[Generate] Proposal generated ({len(proposal_text)} chars)")

    return {
        "draft_proposal": proposal_text,
        "status": "draft",
    }
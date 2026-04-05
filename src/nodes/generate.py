from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from src.state import GraphState
from src.config import Config


# Initialize Gemini once at module level
_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    api_key=Config.GOOGLE_API_KEY,
)


def generate_proposal(state: GraphState) -> dict:
    context = state.get("retrieved_context", [])
    job_description = state.get("job_description", "")
    retry = state.get("retry_count", 0)
    feedback = state.get("human_feedback", None)

    print(f"[Generate] Drafting proposal with Gemini (attempt #{retry + 1})")
    if feedback:
        print(f"[Generate] Incorporating feedback: {feedback}")

    resume_text = "\n\n".join(context) if context else "No resume context available."

    feedback_section = (
        f"\n\nPrevious feedback to incorporate:\n{feedback}" if feedback else ""
    )

    prompt = PromptTemplate.from_template(
        "You are an expert freelance proposal writer. Your task is to write a highly "
        "converting, concise cover letter / proposal for the job below.\n\n"
        "CRITICAL RULES:\n"
        "1. ONLY use skills and experience from the resume provided. Do NOT hallucinate.\n"
        "2. Keep it professional, conversational, and under 4 short paragraphs.\n"
        "3. Avoid generic buzzwords. Be specific and genuine.\n"
        "4. End with a clear call to action.\n\n"
        "Job Description:\n{job_description}\n\n"
        "Applicant Resume:\n{resume_text}"
        "{feedback_section}\n\n"
        "Proposal:"
    )

    chain = prompt | _llm
    response = chain.invoke({
        "job_description": job_description,
        "resume_text": resume_text,
        "feedback_section": feedback_section,
    })

    print(f"[Generate] Proposal generated ({len(response.content)} chars)")

    return {
        "draft_proposal": response.content,
        "status": "draft",
    }
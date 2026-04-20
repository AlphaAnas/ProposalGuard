import json
import os
# from langchain_google_genai import ChatGoogleGenerativeAI
from groq import Groq
from langchain_core.prompts import PromptTemplate
from src.state import GraphState
from src.config import Config

# # Initialize Gemini (re-enable when ready)
# _llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash",
#     temperature=0.0,
#     api_key=Config.GOOGLE_API_KEY,
# )

# Using Groq llama for now
_GROQ_MODEL = "llama-3.1-8b-instant"
_groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

_EXTRACT_CLAIMS_PROMPT = PromptTemplate.from_template(
    "Extract every specific factual claim this proposal makes about the applicant's "
    "experience, skills, and qualifications.\n\n"
    "A \"claim\" is anything that could be true or false - specific technologies, years of experience, "
    "project names, metrics, job titles, companies, tools, certifications, team sizes, or outcomes.\n\n"
    "Do NOT extract:\n"
    "- Generic statements like \"I'm a good communicator\" (not verifiable)\n"
    "- Future promises like \"I will deliver on time\" (not a factual claim about past experience)\n"
    "- Opinions like \"I think I'd be a great fit\" (subjective)\n\n"
    "DO extract claims like:\n"
    "- \"5 years of Python experience\"\n"
    "- \"Built a fraud detection system at Stripe\"\n"
    "- \"Reduced chargebacks by 34%\"\n"
    "- \"Experience with Next.js and TypeScript\"\n"
    "- \"Deployed on AWS SageMaker\"\n"
    "- \"Worked with a team of 5 engineers\"\n\n"
    "Proposal:\n{proposal}\n\n"
    "Return ONLY a JSON array of short claim strings. No explanation, no markdown fences.\n"
    "Example: [\"built a REST API with FastAPI\", \"5 years of Python experience\"]"
)

_VERIFY_CLAIMS_PROMPT = PromptTemplate.from_template(
    "You are a strict fact-checker. Your job is to verify whether each claim "
    "below is SUPPORTED by the source documents provided.\n\n"
    "RULES:\n"
    "1. A claim is SUPPORTED only if the source documents contain clear evidence for it. "
    "The evidence doesn't need to be word-for-word - but the substance must be there.\n"
    "2. A claim is UNSUPPORTED if:\n"
    "   - The source documents don't mention it at all\n"
    "   - The source documents mention something similar but with different specifics "
    "(e.g., claim says \"5 years\" but resume shows 3 years)\n"
    "   - The claim exaggerates or embellishes what the sources say\n"
    "3. Be strict. When in doubt, mark as UNSUPPORTED. It's better to flag a borderline claim "
    "than to let a hallucination through.\n"
    "4. Technologies/skills count as supported if they appear ANYWHERE in the source documents "
    "- in the resume skills section, in project descriptions, or in past proposals.\n\n"
    "Source Documents:\n{source_text}\n\n"
    "Claims to verify:\n{claims_json}\n\n"
    "Return ONLY a JSON object with exactly two keys:\n"
    "  \"supported\": [list of claims that ARE backed by the sources]\n"
    "  \"unsupported\": [list of claims that are NOT backed by the sources]\n\n"
    "No explanation. No markdown. Just valid JSON."
)


def verify_grounding(state: GraphState) -> dict:
    proposal = state.get("draft_proposal", "")
    context = state.get("retrieved_context", [])

    if not proposal:
        print("[Verify] No proposal to verify — score 0.0")
        return {"grounding_score": 0.0, "status": "verifying"}

    # Build the source text from resume + past proposals
    source_parts = []
    if context:
        source_parts.append(f"[RESUME]\n{context[0]}")
    for i, past in enumerate(context[1:], start=1):
        source_parts.append(f"[PAST PROPOSAL {i}]\n{past}")
    source_text = "\n\n".join(source_parts) if source_parts else "No source documents available."

    print("[Verify] Step 1 — Extracting claims from draft proposal...")
    try:
        extract_prompt = _EXTRACT_CLAIMS_PROMPT.format(proposal=proposal)
        response = _groq_client.chat.completions.create(
            model=_GROQ_MODEL,
            temperature=0.0,
            messages=[{"role": "user", "content": extract_prompt}],
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        claims: list[str] = json.loads(raw.strip())
    except Exception as e:
        print(f"[Verify] Failed to extract claims: {e} — defaulting score to 0.5")
        return {"grounding_score": 0.5, "status": "verifying"}

    if not claims:
        print("[Verify] No claims extracted — treating as fully grounded (score 1.0)")
        return {"grounding_score": 1.0, "status": "verifying"}

    print(f"[Verify] Extracted {len(claims)} claim(s): {claims}")

    print("[Verify] Step 2 — Verifying claims against resume + past proposals...")
    try:
        verify_prompt = _VERIFY_CLAIMS_PROMPT.format(
            source_text=source_text,
            claims_json=json.dumps(claims),
        )
        response2 = _groq_client.chat.completions.create(
            model=_GROQ_MODEL,
            temperature=0.0,
            messages=[{"role": "user", "content": verify_prompt}],
        )
        raw2 = response2.choices[0].message.content.strip()
        if raw2.startswith("```"):
            raw2 = raw2.split("```")[1]
            if raw2.startswith("json"):
                raw2 = raw2[4:]
        result = json.loads(raw2.strip())
        supported: list[str] = result.get("supported", [])
        unsupported: list[str] = result.get("unsupported", [])
    except Exception as e:
        print(f"[Verify] Failed to verify claims: {e} — defaulting score to 0.5")
        return {"grounding_score": 0.5, "status": "verifying"}

    total = len(supported) + len(unsupported)
    score = round(len(supported) / total, 2) if total > 0 else 1.0

    print(f"[Verify] Grounding score: {score}  ({len(supported)} supported / {total} total)")
    if unsupported:
        print(f"[Verify] Unsupported (hallucinated) claims: {unsupported}")
    else:
        print("[Verify] All claims are grounded in source documents.")

    return {
        "grounding_score": score,
        "status": "verifying",
    }
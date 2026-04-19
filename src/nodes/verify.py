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
    "Extract every specific factual claim the proposal makes about the applicant "
    "(skills, technologies, tools, project names, metrics, years of experience, etc.).\n\n"
    "Proposal:\n{proposal}\n\n"
    "Return a JSON array of short claim strings and nothing else. Example:\n"
    '[\"5 years of Python experience\", \"built a REST API with FastAPI\"]'
)

_VERIFY_CLAIMS_PROMPT = PromptTemplate.from_template(
    "You are a strict fact-checker. For each claim below, determine whether it is "
    "SUPPORTED or UNSUPPORTED based solely on the provided source documents "
    "(resume and past proposals). Do not use outside knowledge.\n\n"
    "Source Documents:\n{source_text}\n\n"
    "Claims to verify:\n{claims_json}\n\n"
    "Return a JSON object with two keys:\n"
    "  \"supported\": list of supported claims\n"
    "  \"unsupported\": list of unsupported/hallucinated claims\n"
    "Return only valid JSON, no markdown."
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
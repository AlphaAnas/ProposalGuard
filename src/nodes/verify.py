import json
import os
from groq import Groq
from langchain_core.prompts import PromptTemplate
from src.state import GraphState

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


def _strip_code_fences(raw: str) -> str:
    """Remove markdown code fences from LLM output."""
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def verify_grounding(state: GraphState) -> dict:
    proposal = state.get("draft_proposal", "")
    context = state.get("retrieved_context", [])

    if not proposal:
        print("[Verify] No proposal to verify — score 0.0")
        return {
            "grounding_score": 0.0,
            "extracted_claims": [],
            "supported_claims": [],
            "unsupported_claims": [],
            "status": "verifying",
        }

    # Build the source text from resume + past proposals
    source_parts = []
    if context:
        source_parts.append(f"[RESUME]\n{context[0]}")
    for i, past in enumerate(context[1:], start=1):
        source_parts.append(f"[PAST PROPOSAL {i}]\n{past}")
    source_text = "\n\n".join(source_parts) if source_parts else "No source documents available."

    # Step 1: Extract claims
    print("[Verify] Step 1 — Extracting claims from draft proposal...")
    try:
        extract_prompt = _EXTRACT_CLAIMS_PROMPT.format(proposal=proposal)
        response = _groq_client.chat.completions.create(
            model=_GROQ_MODEL,
            temperature=0.0,
            messages=[{"role": "user", "content": extract_prompt}],
        )
        raw = _strip_code_fences(response.choices[0].message.content.strip())
        claims = json.loads(raw)
    except Exception as e:
        print(f"[Verify] Failed to extract claims: {e} — defaulting score to 0.5")
        return {
            "grounding_score": 0.5,
            "extracted_claims": [],
            "supported_claims": [],
            "unsupported_claims": [],
            "status": "verifying",
        }

    if not claims:
        print("[Verify] No claims extracted — treating as fully grounded (score 1.0)")
        return {
            "grounding_score": 1.0,
            "extracted_claims": [],
            "supported_claims": [],
            "unsupported_claims": [],
            "status": "verifying",
        }

    print(f"[Verify] Extracted {len(claims)} claim(s)")

    # Step 2: Verify claims against source documents
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
        raw2 = _strip_code_fences(response2.choices[0].message.content.strip())
        result = json.loads(raw2)
        supported = result.get("supported", [])
        unsupported = result.get("unsupported", [])
    except Exception as e:
        print(f"[Verify] Failed to verify claims: {e} — defaulting score to 0.5")
        return {
            "grounding_score": 0.5,
            "extracted_claims": claims,
            "supported_claims": [],
            "unsupported_claims": [],
            "status": "verifying",
        }

    total = len(supported) + len(unsupported)
    score = round(len(supported) / total, 2) if total > 0 else 1.0

    print(f"[Verify] Grounding score: {score}  ({len(supported)} supported / {total} total)")
    if unsupported:
        print(f"[Verify] Hallucinated claims: {unsupported}")

    return {
        "grounding_score": score,
        "extracted_claims": claims,
        "supported_claims": supported,
        "unsupported_claims": unsupported,
        "status": "verifying",
    }
import json
import os
from groq import Groq
from langchain_core.prompts import PromptTemplate
from src.state import GraphState

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
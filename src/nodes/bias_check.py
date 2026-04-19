from __future__ import annotations

import copy
import math
import os
import re
from typing import Optional

from groq import Groq
from openai import OpenAI
from pydantic import BaseModel

from src.state import GraphState

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
MODEL_ID = "llama-3.1-70b-versatile"

SYSTEM_PROMPT = (
    "You are a structured reasoning engine. Follow instructions exactly. "
    "Do not hallucinate. Do not add information beyond what is requested. "
    "Adhere strictly to any metrics or constraints provided. "
    "Think step by step before producing output."
)

# ---------------------------------------------------------------------------
# Groq client (reuse env var; call_model assumed to share the same key)
# ---------------------------------------------------------------------------
_groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# OpenAI-compatible client pointed at Groq for embeddings
_embed_client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

EMBED_MODEL = "text-embedding-3-small"


# ---------------------------------------------------------------------------
# call_model — thin wrapper so the node is self-contained; existing graph code
# may pass its own version; this one is used internally here.
# ---------------------------------------------------------------------------
def call_model(system: str, user: str, model: str = MODEL_ID) -> str:
    response = _groq_client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Pydantic evaluation schema
# ---------------------------------------------------------------------------
class BiasEvaluation(BaseModel):
    is_biased: bool
    bias_score: float
    price_diff: float
    tone_diff: float
    length_diff: float
    similarity: float
    bias_details: list[str]
    debiasing_instructions: list[str]


# ---------------------------------------------------------------------------
# Counterfactual profile generation
# ---------------------------------------------------------------------------
_ALTERNATE_NAMES = ["Alex Johnson", "Jordan Smith", "Morgan Lee"]
_ALTERNATE_LOCATIONS = ["Berlin, Germany", "Lagos, Nigeria", "Seoul, South Korea"]


def _build_control_profiles(baseline: dict) -> list[dict]:
    """
    Return 3 control profiles derived from the baseline.

    A: same name, different location
    B: different name, same location
    C: different name, different location
    """
    name = baseline.get("name", "Jamie Rivera")
    location = baseline.get("location", "New York, USA")
    rate = baseline.get("rate", baseline.get("hourly_rate", ""))

    alt_name = _ALTERNATE_NAMES[0] if name not in _ALTERNATE_NAMES else _ALTERNATE_NAMES[1]
    alt_location = _ALTERNATE_LOCATIONS[0] if location not in _ALTERNATE_LOCATIONS else _ALTERNATE_LOCATIONS[1]

    profile_a = copy.deepcopy(baseline)
    profile_a["name"] = name
    profile_a["location"] = alt_location
    profile_a["rate"] = rate

    profile_b = copy.deepcopy(baseline)
    profile_b["name"] = alt_name
    profile_b["location"] = location
    profile_b["rate"] = rate

    profile_c = copy.deepcopy(baseline)
    profile_c["name"] = alt_name
    profile_c["location"] = alt_location
    profile_c["rate"] = rate

    return [profile_a, profile_b, profile_c]


# ---------------------------------------------------------------------------
# Control proposal generation
# ---------------------------------------------------------------------------
def _profile_to_str(profile: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in profile.items())


def _generate_control_proposal(
    job_posting: str,
    retrieved_context: str,
    profile: dict,
) -> str:
    user_prompt = (
        "Generate a professional freelance proposal for the job posting below.\n"
        "Use ONLY the applicant profile provided. Do not deviate from the profile.\n"
        "Do NOT add commentary. Return only the proposal text.\n\n"
        f"JOB POSTING:\n{job_posting}\n\n"
        f"RETRIEVED CONTEXT:\n{retrieved_context}\n\n"
        f"APPLICANT PROFILE:\n{_profile_to_str(profile)}"
    )
    return call_model(system=SYSTEM_PROMPT, user=user_prompt)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------
_HEDGING_PATTERN = re.compile(
    r"\b(maybe|perhaps|possibly|might|could|somewhat|kind of|sort of|"
    r"i think|i believe|i feel|hopefully|probably|roughly|approximately|"
    r"around|about|not sure|unsure|if possible|if needed)\b",
    re.IGNORECASE,
)

_ASSERTIVE_PATTERN = re.compile(
    r"\b(will|guarantee|deliver|ensure|committed|proven|expert|"
    r"speciali[sz]e|lead|achieve|drive|execute|confident|dedicated|"
    r"capable|provide|complete|build|launch|optimize|outperform)\b",
    re.IGNORECASE,
)

_PRICE_PATTERN = re.compile(
    r"\$\s*(\d[\d,]*(?:\.\d{1,2})?)|(\d[\d,]*(?:\.\d{1,2})?)\s*(?:USD|usd|dollars?)",
)


def extract_price(text: str) -> Optional[float]:
    matches = _PRICE_PATTERN.findall(text)
    prices: list[float] = []
    for m in matches:
        raw = (m[0] or m[1]).replace(",", "")
        try:
            prices.append(float(raw))
        except ValueError:
            continue
    return prices[0] if prices else None


def count_hedging(text: str) -> int:
    return len(_HEDGING_PATTERN.findall(text))


def count_assertive(text: str) -> int:
    return len(_ASSERTIVE_PATTERN.findall(text))


def token_count(text: str) -> int:
    # Simple whitespace tokeniser — no external dependency
    return len(re.findall(r"\S+", text))


# ---------------------------------------------------------------------------
# Cosine similarity via Groq embeddings
# ---------------------------------------------------------------------------
def _get_embedding(text: str) -> list[float]:
    response = _embed_client.embeddings.create(
        model=EMBED_MODEL,
        input=text,
    )
    return response.data[0].embedding


def cosine_similarity(text_a: str, text_b: str) -> float:
    vec_a = _get_embedding(text_a)
    vec_b = _get_embedding(text_b)

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))

    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------
PRICE_DIFF_THRESHOLD = 0.15
TONE_DIFF_THRESHOLD = 2
SIMILARITY_THRESHOLD = 0.75
LENGTH_DIFF_THRESHOLD = 0.25


# ---------------------------------------------------------------------------
# Single-pair evaluation
# ---------------------------------------------------------------------------
def _evaluate_pair(
    baseline_text: str,
    control_text: str,
    label: str,
) -> tuple[float, list[str], BiasEvaluation]:
    """
    Compare baseline vs. one control proposal.
    Returns (score, bias_details, BiasEvaluation).
    """
    # --- Step A: Extract metrics ---
    b_price = extract_price(baseline_text)
    c_price = extract_price(control_text)
    b_tokens = token_count(baseline_text)
    c_tokens = token_count(control_text)
    b_hedge = count_hedging(baseline_text)
    c_hedge = count_hedging(control_text)
    b_assert = count_assertive(baseline_text)
    c_assert = count_assertive(control_text)

    # --- Step B: Compute diffs ---
    # Price diff ratio
    if b_price is not None and c_price is not None:
        avg_price = (b_price + c_price) / 2.0
        price_diff_ratio = abs(b_price - c_price) / avg_price if avg_price != 0 else 0.0
    else:
        price_diff_ratio = 0.0

    # Tone diff: (assertive_control - hedging_control) - (assertive_baseline - hedging_baseline)
    tone_baseline = b_assert - b_hedge
    tone_control = c_assert - c_hedge
    tone_diff = tone_control - tone_baseline

    # Length diff ratio
    avg_len = (b_tokens + c_tokens) / 2.0
    length_diff_ratio = abs(b_tokens - c_tokens) / avg_len if avg_len != 0 else 0.0

    # Semantic similarity
    similarity = cosine_similarity(baseline_text, control_text)

    # --- Step C: Apply thresholds ---
    bias_details: list[str] = []
    violations = 0

    if price_diff_ratio > PRICE_DIFF_THRESHOLD:
        violations += 1
        bias_details.append(
            f"[{label}] Price divergence {price_diff_ratio:.2%} exceeds threshold "
            f"{PRICE_DIFF_THRESHOLD:.0%} "
            f"(baseline=${b_price}, control=${c_price})"
        )

    if abs(tone_diff) > TONE_DIFF_THRESHOLD:
        violations += 1
        bias_details.append(
            f"[{label}] Tone shift of {tone_diff:+d} exceeds threshold ±{TONE_DIFF_THRESHOLD} "
            f"(baseline assertive={b_assert}, hedge={b_hedge}; "
            f"control assertive={c_assert}, hedge={c_hedge})"
        )

    if similarity < SIMILARITY_THRESHOLD:
        violations += 1
        bias_details.append(
            f"[{label}] Semantic similarity {similarity:.3f} below threshold {SIMILARITY_THRESHOLD}"
        )

    if length_diff_ratio > LENGTH_DIFF_THRESHOLD:
        violations += 1
        bias_details.append(
            f"[{label}] Length divergence {length_diff_ratio:.2%} exceeds threshold "
            f"{LENGTH_DIFF_THRESHOLD:.0%} "
            f"(baseline={b_tokens} tokens, control={c_tokens} tokens)"
        )

    # --- Bias score for this pair ---
    score = violations / 4.0

    eval_obj = BiasEvaluation(
        is_biased=score > 0.5,
        bias_score=round(score, 4),
        price_diff=round(price_diff_ratio, 4),
        tone_diff=float(tone_diff),
        length_diff=round(length_diff_ratio, 4),
        similarity=round(similarity, 4),
        bias_details=bias_details,
        debiasing_instructions=[],  # filled later
    )

    return score, bias_details, eval_obj


# ---------------------------------------------------------------------------
# Debiasing instruction generation
# ---------------------------------------------------------------------------
def _generate_debiasing_instructions(all_details: list[str]) -> list[str]:
    if not all_details:
        return []

    issues_block = "\n".join(f"- {d}" for d in all_details)

    user_prompt = (
        "The following bias issues were detected across demographic counterfactual comparisons "
        "of a freelance proposal:\n\n"
        f"{issues_block}\n\n"
        "Generate a numbered list of concrete rewrite instructions that will fix EACH issue. "
        "Instructions MUST:\n"
        "1. Identify specific hedging phrases to REMOVE (quote them).\n"
        "2. Specify assertive replacement phrases to INSERT.\n"
        "3. State exact price alignment required if price bias was detected.\n"
        "4. Describe tone normalisation needed across demographic variants.\n"
        "5. Specify minimum/maximum token targets if length bias was detected.\n"
        "Return ONLY the numbered list, one instruction per line, no preamble."
    )

    raw = call_model(system=SYSTEM_PROMPT, user=user_prompt)

    instructions: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if line:
            # Strip leading numbering like "1." or "1)"
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line)
            if cleaned:
                instructions.append(cleaned)

    return instructions


# ---------------------------------------------------------------------------
# Main LangGraph node
# ---------------------------------------------------------------------------
def bias_evaluation_node(state: GraphState) -> dict:
    print("[BiasEval] Starting multi-counterfactual bias evaluation...")

    job_posting: str = state.get("job_description", "") or state.get("rfp_text", "")
    retrieved_context_list = state.get("retrieved_context", [])
    retrieved_context: str = (
        "\n\n".join(retrieved_context_list)
        if isinstance(retrieved_context_list, list)
        else str(retrieved_context_list)
    )
    baseline_profile: dict = state.get("baseline_profile", {})
    draft_proposal: str = state.get("draft_proposal", "")
    existing_flags: list[str] = list(state.get("bias_flags", []))

    if not draft_proposal:
        print("[BiasEval] No draft proposal found — skipping evaluation.")
        return {"bias_flags": existing_flags, "status": "bias_checked"}

    # Provide a sensible default baseline profile if none was supplied
    if not baseline_profile:
        baseline_profile = {
            "name": "Jamie Rivera",
            "location": "New York, USA",
            "rate": "$75/hr",
        }

    # -----------------------------------------------------------------------
    # 1. Build control profiles
    # -----------------------------------------------------------------------
    control_profiles = _build_control_profiles(baseline_profile)
    labels = [
        "Control-A (same name, diff location)",
        "Control-B (diff name, same location)",
        "Control-C (diff name, diff location)",
    ]

    # -----------------------------------------------------------------------
    # 2. Generate control proposals
    # -----------------------------------------------------------------------
    control_proposals: list[str] = []
    for i, profile in enumerate(control_profiles):
        print(f"[BiasEval] Generating {labels[i]}...")
        proposal = _generate_control_proposal(job_posting, retrieved_context, profile)
        control_proposals.append(proposal)

    # -----------------------------------------------------------------------
    # 3. Evaluate each pair
    # -----------------------------------------------------------------------
    all_scores: list[float] = []
    all_bias_details: list[str] = []

    for i, (control_text, label) in enumerate(zip(control_proposals, labels)):
        print(f"[BiasEval] Evaluating {label}...")
        score, details, _ = _evaluate_pair(draft_proposal, control_text, label)
        all_scores.append(score)
        all_bias_details.extend(details)

    # -----------------------------------------------------------------------
    # 4. Aggregate bias score
    # -----------------------------------------------------------------------
    final_bias_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
    is_biased = final_bias_score > 0.5

    print(
        f"[BiasEval] Final bias score: {final_bias_score:.4f} — "
        f"{'BIASED' if is_biased else 'CLEAN'}"
    )

    # -----------------------------------------------------------------------
    # 5. Generate debiasing instructions if biased
    # -----------------------------------------------------------------------
    new_flags = list(existing_flags)

    if is_biased and all_bias_details:
        print("[BiasEval] Generating debiasing instructions...")
        instructions = _generate_debiasing_instructions(all_bias_details)

        summary_flag = (
            f"[BiasEval] Bias detected (score={final_bias_score:.4f}). "
            f"Details: {'; '.join(all_bias_details)}"
        )
        new_flags.append(summary_flag)

        for instruction in instructions:
            new_flags.append(f"[Debias] {instruction}")

        print(f"[BiasEval] Appended {1 + len(instructions)} flag(s) to state.")
    else:
        print("[BiasEval] No demographic bias detected across counterfactual comparisons.")

    return {
        "bias_flags": new_flags,
        "status": "bias_checked",
    }


# ---------------------------------------------------------------------------
# Backward-compatible alias used by graph.py
# ---------------------------------------------------------------------------
check_bias = bias_evaluation_node
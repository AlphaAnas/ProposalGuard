from __future__ import annotations

import copy
import math
import os
import re
from typing import Optional

from groq import Groq
from pydantic import BaseModel

from src.state import GraphState
from src.nodes.generate import generate_proposal

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
MODEL_ID = "openai/gpt-oss-20b"

SYSTEM_PROMPT = (
    "You are a structured reasoning engine. Follow instructions exactly. "
    "Do not hallucinate. Do not add information beyond what is requested. "
    "Adhere strictly to any metrics or constraints provided. "
    "Think step by step before producing output."
)

_groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


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
def _generate_control_proposal(job_posting, retrieved_context, profile):
    name = profile.get("name", "")
    location = profile.get("location", "")
    rate = profile.get("rate", "")

    resume_content = retrieved_context[0] if retrieved_context else "No resume available."
    control_header = f"Applicant: {name} | Location: {location} | Rate: {rate}\n\n"
    modified_context = [control_header + resume_content] + list(retrieved_context[1:])

    control_state = {
        "job_description": job_posting,
        "retrieved_context": modified_context,
        "retry_count": 0,
        "human_feedback": None,
    }
    result = generate_proposal(control_state)
    return result["draft_proposal"]


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
    prices = []
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
    return len(re.findall(r"\S+", text))


# ---------------------------------------------------------------------------
# Semantic similarity
# ---------------------------------------------------------------------------
from sentence_transformers import SentenceTransformer

_embed_model = SentenceTransformer("all-MiniLM-L6-v2")


def _get_embedding(text: str) -> list[float]:
    return _embed_model.encode(text, normalize_embeddings=True).tolist()


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
# Thresholds
# ---------------------------------------------------------------------------
PRICE_DIFF_THRESHOLD = 0.15
TONE_DIFF_THRESHOLD = 2
SIMILARITY_THRESHOLD = 0.75
LENGTH_DIFF_THRESHOLD = 0.25


# ---------------------------------------------------------------------------
# Single-pair evaluation
# ---------------------------------------------------------------------------
def _evaluate_pair(baseline_text, control_text, label):
    b_price = extract_price(baseline_text)
    c_price = extract_price(control_text)
    b_tokens = token_count(baseline_text)
    c_tokens = token_count(control_text)
    b_hedge = count_hedging(baseline_text)
    c_hedge = count_hedging(control_text)
    b_assert = count_assertive(baseline_text)
    c_assert = count_assertive(control_text)

    if b_price is not None and c_price is not None:
        avg_price = (b_price + c_price) / 2.0
        price_diff_ratio = abs(b_price - c_price) / avg_price if avg_price != 0 else 0.0
    else:
        price_diff_ratio = 0.0

    tone_baseline = b_assert - b_hedge
    tone_control = c_assert - c_hedge
    tone_diff = tone_control - tone_baseline

    avg_len = (b_tokens + c_tokens) / 2.0
    length_diff_ratio = abs(b_tokens - c_tokens) / avg_len if avg_len != 0 else 0.0

    similarity = cosine_similarity(baseline_text, control_text)

    bias_details = []
    violations = 0

    if price_diff_ratio > PRICE_DIFF_THRESHOLD:
        violations += 1
        bias_details.append(
            f"[{label}] Price divergence {price_diff_ratio:.2%} "
            f"(baseline=${b_price}, control=${c_price})"
        )

    if abs(tone_diff) > TONE_DIFF_THRESHOLD:
        violations += 1
        bias_details.append(
            f"[{label}] Tone shift {tone_diff:+d} "
            f"(baseline: assertive={b_assert} hedge={b_hedge}, "
            f"control: assertive={c_assert} hedge={c_hedge})"
        )

    if similarity < SIMILARITY_THRESHOLD:
        violations += 1
        bias_details.append(
            f"[{label}] Semantic similarity {similarity:.3f} below {SIMILARITY_THRESHOLD}"
        )

    if length_diff_ratio > LENGTH_DIFF_THRESHOLD:
        violations += 1
        bias_details.append(
            f"[{label}] Length divergence {length_diff_ratio:.2%} "
            f"(baseline={b_tokens}, control={c_tokens} tokens)"
        )

    score = violations / 4.0

    # Return detailed metrics for transparency
    pair_details = {
        "label": label,
        "bias_score": round(score, 4),
        "violations": violations,
        "metrics": {
            "price_diff": round(price_diff_ratio, 4),
            "tone_diff": int(tone_diff),
            "similarity": round(similarity, 4),
            "length_diff": round(length_diff_ratio, 4),
        },
        "baseline_stats": {
            "price": b_price,
            "tokens": b_tokens,
            "assertive_words": b_assert,
            "hedging_words": b_hedge,
        },
        "control_stats": {
            "price": c_price,
            "tokens": c_tokens,
            "assertive_words": c_assert,
            "hedging_words": c_hedge,
        },
        "flags": bias_details,
    }

    return score, bias_details, pair_details


# ---------------------------------------------------------------------------
# Debiasing instructions
# ---------------------------------------------------------------------------
def _generate_debiasing_instructions(all_details):
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

    instructions = []
    for line in raw.splitlines():
        line = line.strip()
        if line:
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line)
            if cleaned:
                instructions.append(cleaned)
    return instructions


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------
def bias_evaluation_node(state: GraphState) -> dict:
    print("[BiasEval] Starting multi-counterfactual bias evaluation...")

    job_posting = state.get("job_description", "") or state.get("rfp_text", "")
    retrieved_context_list = state.get("retrieved_context", [])
    baseline_profile = state.get("baseline_profile", {})
    draft_proposal = state.get("draft_proposal", "")
    existing_flags = list(state.get("bias_flags", []))

    if not draft_proposal:
        print("[BiasEval] No draft proposal found — skipping.")
        return {
            "bias_flags": existing_flags,
            "bias_evaluation": {"skipped": True, "reason": "No proposal to evaluate"},
            "status": "bias_checked",
        }

    # Default baseline profile
    if not baseline_profile:
        baseline_profile = {
            "name": "Jamie Rivera",
            "location": "New York, USA",
            "rate": "$75/hr",
        }

    # 1. Build control profiles
    control_profiles = _build_control_profiles(baseline_profile)
    labels = [
        "Control-A (same name, diff location)",
        "Control-B (diff name, same location)",
        "Control-C (diff name, diff location)",
    ]

    # 2. Generate control proposals
    control_proposals = []
    profiles_detail = []
    for i, profile in enumerate(control_profiles):
        print(f"[BiasEval] Generating {labels[i]}...")
        proposal = _generate_control_proposal(job_posting, retrieved_context_list, profile)
        control_proposals.append(proposal)
        profiles_detail.append({
            "label": labels[i],
            "profile": profile,
            "proposal_preview": proposal[:200] + "..." if len(proposal) > 200 else proposal,
        })

    # 3. Evaluate each pair
    all_scores = []
    all_bias_details = []
    pair_evaluations = []

    for i, (control_text, label) in enumerate(zip(control_proposals, labels)):
        print(f"[BiasEval] Evaluating {label}...")
        score, details, pair_detail = _evaluate_pair(draft_proposal, control_text, label)
        all_scores.append(score)
        all_bias_details.extend(details)
        pair_evaluations.append(pair_detail)

    # 4. Aggregate
    final_bias_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
    is_biased = final_bias_score > 0.5

    print(f"[BiasEval] Final bias score: {final_bias_score:.4f} — {'BIASED' if is_biased else 'CLEAN'}")

    # 5. Debiasing instructions if needed
    new_flags = list(existing_flags)
    debiasing_instructions = []

    if is_biased and all_bias_details:
        print("[BiasEval] Generating debiasing instructions...")
        debiasing_instructions = _generate_debiasing_instructions(all_bias_details)

        summary_flag = (
            f"Bias detected (score={final_bias_score:.4f}). "
            f"Details: {'; '.join(all_bias_details)}"
        )
        new_flags.append(summary_flag)
        for instruction in debiasing_instructions:
            new_flags.append(f"[Debias] {instruction}")

    # 6. Build full evaluation report for transparency
    bias_evaluation = {
        "is_biased": is_biased,
        "final_score": round(final_bias_score, 4),
        "baseline_profile": baseline_profile,
        "control_profiles": profiles_detail,
        "pair_evaluations": pair_evaluations,
        "thresholds": {
            "price_diff": PRICE_DIFF_THRESHOLD,
            "tone_diff": TONE_DIFF_THRESHOLD,
            "similarity": SIMILARITY_THRESHOLD,
            "length_diff": LENGTH_DIFF_THRESHOLD,
        },
        "debiasing_instructions": debiasing_instructions,
        "total_flags": len(all_bias_details),
    }

    return {
        "draft_proposal": draft_proposal,
        "bias_flags": new_flags,
        "bias_evaluation": bias_evaluation,
        "status": "bias_checked",
    }


check_bias = bias_evaluation_node
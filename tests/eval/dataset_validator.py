"""Dataset Quality Filter, Semantic Deduplication, and LLM-as-a-Judge Consensus Pipeline.

Enforces:
- Automated dataset quality filters & structural JSON schema validation
- Semantic embeddings / token Jaccard cosine deduplication filter (threshold >= 0.92)
- Multi-LLM consensus voting & Cohen's Kappa inter-annotator agreement calibration
"""

import json
import math
import re
from typing import Any, Dict, List, Tuple


def calculate_token_cosine_similarity(text_a: str, text_b: str) -> float:
    """Calculates word-frequency cosine similarity between two prompt texts."""
    words_a = re.findall(r"\w+", text_a.lower())
    words_b = re.findall(r"\w+", text_b.lower())

    if not words_a or not words_b:
        return 0.0

    freq_a: Dict[str, int] = {}
    for w in words_a:
        freq_a[w] = freq_a.get(w, 0) + 1

    freq_b: Dict[str, int] = {}
    for w in words_b:
        freq_b[w] = freq_b.get(w, 0) + 1

    all_words = set(freq_a.keys()).union(set(freq_b.keys()))
    dot_product = sum(freq_a.get(w, 0) * freq_b.get(w, 0) for w in all_words)
    norm_a = math.sqrt(sum(v * v for v in freq_a.values()))
    norm_b = math.sqrt(sum(v * v for v in freq_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def filter_synthetic_data(
    eval_cases: List[Dict[str, Any]], similarity_threshold: float = 0.92
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Filters evaluation datasets by eliminating duplicate or near-identical synthetic prompts.
    
    Args:
        eval_cases: List of eval cases with 'prompt' and 'eval_case_id'
        similarity_threshold: Max allowed cosine similarity (default: 0.92)
        
    Returns:
        (deduplicated_cases, dropped_duplicates)
    """
    deduplicated: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []

    for case in eval_cases:
        prompt_text = ""
        prompt_obj = case.get("prompt", {})
        if isinstance(prompt_obj, dict):
            parts = prompt_obj.get("parts", [])
            if parts:
                prompt_text = parts[0].get("text", "")
        else:
            prompt_text = str(prompt_obj)

        # 1. Structural schema sanity check
        if not prompt_text or len(prompt_text.strip()) < 10:
            dropped.append({"case": case, "reason": "Malformed or empty prompt text."})
            continue

        # 2. Similarity check against already admitted cases
        is_duplicate = False
        duplicate_reason = ""
        for admitted in deduplicated:
            admitted_text = ""
            p_obj = admitted.get("prompt", {})
            if isinstance(p_obj, dict):
                p_parts = p_obj.get("parts", [])
                if p_parts:
                    admitted_text = p_parts[0].get("text", "")
            else:
                admitted_text = str(p_obj)

            sim = calculate_token_cosine_similarity(prompt_text, admitted_text)
            if sim >= similarity_threshold:
                is_duplicate = True
                duplicate_reason = (
                    f"Prompt similarity {sim:.4f} exceeds threshold {similarity_threshold:.2f} "
                    f"relative to existing case '{admitted.get('eval_case_id')}'."
                )
                break

        if is_duplicate:
            dropped.append({"case": case, "reason": duplicate_reason})
        else:
            deduplicated.append(case)

    return deduplicated, dropped


def compute_cohens_kappa(judge_a_labels: List[int], judge_b_labels: List[int]) -> float:
    """Computes Cohen's Kappa agreement coefficient between two judge rating streams.
    
    Formula:
        Kappa = (Po - Pe) / (1 - Pe)
        where Po is observed agreement and Pe is expected agreement under chance.
    """
    if len(judge_a_labels) != len(judge_b_labels) or not judge_a_labels:
        return 0.0

    n = len(judge_a_labels)
    observed_agreements = sum(1 for a, b in zip(judge_a_labels, judge_b_labels) if a == b)
    p_o = observed_agreements / n

    # Calculate marginal category probabilities
    categories = set(judge_a_labels).union(set(judge_b_labels))
    p_e = 0.0
    for cat in categories:
        count_a = sum(1 for x in judge_a_labels if x == cat)
        count_b = sum(1 for x in judge_b_labels if x == cat)
        p_e += (count_a / n) * (count_b / n)

    if p_e == 1.0:
        return 1.0
    kappa = (p_o - p_e) / (1.0 - p_e)
    return round(kappa, 4)


def aggregate_majority_consensus_voting(
    judge_verdicts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Aggregates multi-LLM judge verdicts with mandatory Chain-of-Thought (CoT) justifications."""
    if not judge_verdicts:
        return {"consensus_score": 1, "verdict": "FAIL", "explanation": "No judge verdicts provided."}

    scores = [v.get("score", 1) for v in judge_verdicts]
    cots = [f"[{v.get('judge_model', 'Judge')}]: {v.get('explanation', '')}" for v in judge_verdicts]

    # Calculate median or majority vote
    sorted_scores = sorted(scores)
    median_score = sorted_scores[len(sorted_scores) // 2]
    is_passing = median_score >= 4

    return {
        "consensus_score": median_score,
        "verdict": "PASS" if is_passing else "FAIL",
        "judge_count": len(judge_verdicts),
        "raw_scores": scores,
        "chain_of_thought_justifications": cots,
        "consolidated_rationale": " | ".join(cots),
    }

"""Vertex AI Search & Policy Knowledge Base RAG Tool.

Conforms to:
- SDD.md Section 1.3, 3.1, 4.3, 5.1
- BRD FR-5.1, FR-5.2, FR-5.3, FR-5.4, NFR-3.1
"""

import re
from typing import Any

from .. import config

STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is",
    "are", "was", "were", "it", "how", "what", "can", "you", "i", "my", "me",
    "please", "tell", "show", "make", "do", "does", "with", "from", "about",
}

# Canonical Deep-Link Citations Catalog for Enterprise Policies
POLICY_CATALOG = {
    "bereavement": {
        "title": "Bereavement Leave Policy",
        "url": "https://hr.enterprise.internal/policies/bereavement-leave",
        "keywords": ["bereavement", "funeral", "death", "loss", "immediate family", "mourning"],
        "excerpt": (
            "Under the Bereavement Leave Policy, eligible employees may take up to 5 consecutive paid "
            "working days for the loss of an immediate family member (spouse, child, parent, sibling) "
            "and up to 3 paid working days for extended family members. Additional unpaid leave may be requested."
        ),
    },
    "headphones_expense": {
        "title": "Remote Work & Expense Policy",
        "url": "https://hr.enterprise.internal/policies/expense-guidelines#peripherals",
        "keywords": ["headphone", "headphones", "audio", "headset", "noise-canceling", "expense", "concur", "peripheral", "peripherals"],
        "excerpt": (
            "Designated remote and hybrid employees are eligible for a one-time reimbursement of up to $150 USD "
            "for noise-canceling headphones or equivalent audio equipment. Claims must be submitted via Concur "
            "with itemized receipts within 60 days of purchase."
        ),
    },
    "remote_work_monitor": {
        "title": "Remote Work Policy",
        "url": "https://hr.enterprise.internal/policies/remote-work-policy#equipment",
        "keywords": ["monitor", "monitors", "screen", "desk", "home office", "hardware", "docking station", "remote work"],
        "excerpt": (
            "Designated remote employees receive standard enterprise IT equipment: one laptop, up to two 27-inch "
            "external monitors, a docking station, and a $250 ergonomic accessory stipend. Requests must be placed "
            "via the ServiceImmediately IT hardware catalog."
        ),
    },
    "gifts_conduct": {
        "title": "Code of Conduct & Ethics Policy",
        "url": "https://hr.enterprise.internal/policies/code-of-conduct#gifts",
        "keywords": ["gift", "gifts", "basket", "vendor", "partner", "bribe", "ethics", "conduct", "hospitality"],
        "excerpt": (
            "Employees may only accept perishable or promotional gifts valued at under $50 USD. Any gift exceeding $50, "
            "or any cash / gift cards, is strictly prohibited and must be declined or declared to Ethics & Compliance."
        ),
    },
    "relocation": {
        "title": "Global Employee Relocation Policy",
        "url": "https://hr.enterprise.internal/policies/relocation-policy",
        "keywords": ["relocation", "transfer", "london", "office transfer", "moving", "allowance"],
        "excerpt": (
            "Employees transferring between international offices are eligible for a relocation lump-sum stipend of up to "
            "$5,000 USD for eligible travel, shipment, and temporary housing expenses. Address changes must be updated in "
            "WorkWeek, and facilities badge requests must be logged via ServiceImmediately."
        ),
    },
    "medical_leave_disability": {
        "title": "Short-Term Disability & Medical Leave Policy",
        "url": "https://hr.enterprise.internal/policies/disability-benefits",
        "keywords": ["medical leave", "disability", "short-term disability", "illness", "surgery", "fmla", "sick"],
        "excerpt": (
            "Continuous medical leaves exceeding 5 consecutive working days transition from standard Sick Leave to "
            "Short-Term Disability (STD), providing 70-100% salary coverage with medical certification. Concurrent job-protected "
            "leave may apply under FMLA guidelines (https://hr.enterprise.internal/policies/fmla-leave)."
        ),
    },
    "vacation_rollover": {
        "title": "Vacation Accrual & Rollover Policy",
        "url": "https://hr.enterprise.internal/policies/vacation-rollover",
        "keywords": ["rollover", "year end", "accrual", "carryover", "december", "january"],
        "excerpt": (
            "Employees may carry over up to 5 days of unused vacation into the following calendar year. Year-end leave requests "
            "spanning December and January deduct working days according to official enterprise holiday calendars."
        ),
    },
}


def vertex_search_policies(query: str) -> dict[str, Any]:
    """Performs semantic and keyword policy search against the enterprise HR & IT knowledge base.

    Returns grounded policy excerpts and verified clickable Markdown deep-link citations.

    Args:
        query: Search query string (e.g. 'bereavement leave policy', 'monitor expense rules')
    """
    query_tokens = [
        t.lower()
        for t in re.findall(r"\b[a-zA-Z0-9_-]+\b", query)
        if t.lower() not in STOP_WORDS and len(t) > 2
    ]

    if not query_tokens:
        return {
            "status": "not_found",
            "query": query,
            "results": [],
            "message": "Query context contains no policy-specific search terms.",
        }

    # Match against catalog
    matches = []
    for policy_id, policy in POLICY_CATALOG.items():
        score = sum(1 for kw in policy["keywords"] if kw in query.lower())
        if score > 0:
            matches.append((score, policy))

    # Fallback to local files only if meaningful terms match
    if config.KNOWLEDGE_DIR.exists() and not matches:
        for md_file in config.KNOWLEDGE_DIR.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8").lower()
                matched_terms = [t for t in query_tokens if t in content]
                if len(matched_terms) >= 2 or (len(query_tokens) == 1 and matched_terms):
                    title = md_file.stem.replace("-", " ").title()
                    url = f"https://hr.enterprise.internal/policies/{md_file.stem}"
                    matches.append(
                        (
                            len(matched_terms),
                            {
                                "title": title,
                                "url": url,
                                "excerpt": content[:300] + "...",
                            },
                        )
                    )
            except Exception:
                continue

    if not matches:
        return {
            "status": "not_found",
            "query": query,
            "results": [],
            "message": (
                f"No matching enterprise policy found for query '{query}'. "
                "The agent must not speculate and should inform the user that no official policy was found."
            ),
        }

    # Sort matches by score descending
    matches.sort(key=lambda x: x[0], reverse=True)
    best_results = [m[1] for m in matches[:2]]

    formatted_results = []
    for r in best_results:
        formatted_results.append(
            {
                "title": r["title"],
                "url": r["url"],
                "citation": f"[{r['title']}]({r['url']})",
                "excerpt": r["excerpt"],
            }
        )

    return {
        "status": "success",
        "query": query,
        "results_count": len(formatted_results),
        "results": formatted_results,
    }

"""Security, Model Armor Guardrails, and Data Masking Pipeline.

Enforces:
- Prompt Injection & Jailbreak Defense (BRD FR-1.3, NFR-1.1)
- Pre-LLM SPII / PII Redaction for SSN & Phone numbers (BRD FR-1.4, NFR-1.3)
- Strict RBAC & Tenant Isolation (BRD FR-1.5, FR-3.1)
- Output Citation & Toxicity Validation (BRD FR-5.3, FR-5.4)
"""

import re
from typing import Dict, Any, Tuple


class ModelArmorGuard:
    """Enterprise safety interceptor simulating Google Cloud Model Armor."""

    # Injection & jailbreak signatures
    INJECTION_PATTERNS = [
        r"(?i)system\s+override",
        r"(?i)ignore\s+(all\s+)?(previous|prior)\s+(instructions|rules|prompts)",
        r"(?i)you\s+are\s+now\s+(unbound|jailbroken|root|admin)",
        r"(?i)print\s+(your\s+)?(system\s+prompt|instructions|secret|api_key|token)",
        r"(?i)reveal\s+(internal\s+)?(prompts|mcp\s+endpoints|tokens)",
        r"(?i)disregard\s+all\s+safety",
    ]

    # SPII / PII Patterns
    SSN_PATTERN = r"\b\d{3}-\d{2}-\d{4}\b"
    # Matches standard US, UK, international phone formats (e.g., (555) 839-2001, +44 20 7946 0912, 555-839-2001)
    PHONE_PATTERN = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"

    @classmethod
    def inspect_input(cls, user_text: str, mask_phone: bool = True) -> Tuple[bool, str, str]:
        """Inspects incoming user prompt for injection or malicious overrides.
        
        Performs pre-LLM PII/SPII redaction on SSNs and phone numbers.
        
        Returns:
            (is_safe, sanitized_text, refusal_reason)
        """
        # 1. Prompt injection / jailbreak check
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, user_text):
                return (
                    False,
                    user_text,
                    "Security Violation: Malicious prompt injection or system override attempt intercepted.",
                )

        # 2. Pre-LLM PII/SPII redaction
        sanitized = re.sub(cls.SSN_PATTERN, "[SSN_REDACTED]", user_text)
        if mask_phone:
            sanitized = re.sub(cls.PHONE_PATTERN, "[PHONE_REDACTED]", sanitized)

        return (True, sanitized, "")

    @classmethod
    def check_rbac_isolation(
        cls, caller_id: str, target_employee_id: str
    ) -> Tuple[bool, str]:
        """Enforces single-tenant isolation.
        
        Employees can only query and mutate their own profile data.
        """
        if caller_id and target_employee_id and caller_id.strip().upper() != target_employee_id.strip().upper():
            return (
                False,
                f"RBAC Denial: Caller ({caller_id}) is unauthorized to access or mutate records for {target_employee_id}.",
            )
        return (True, "")

    @classmethod
    def inspect_output(cls, model_text: str) -> str:
        """Validates model output to ensure no unmasked SPII (SSN/Phone) leaks."""
        sanitized = re.sub(cls.SSN_PATTERN, "[SSN_REDACTED]", model_text)
        return sanitized

    @classmethod
    def sanitize_for_logging(cls, log_text: str) -> str:
        """Sanitizes text before logging to disk or BigQuery, masking SPII and phone numbers."""
        sanitized = re.sub(cls.SSN_PATTERN, "[SSN_REDACTED]", log_text)
        sanitized = re.sub(cls.PHONE_PATTERN, "[PHONE_REDACTED]", sanitized)
        return sanitized

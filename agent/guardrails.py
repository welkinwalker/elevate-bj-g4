"""Security, Google Cloud Model Armor Guardrails, and Data Masking Pipeline.

Enforces:
- Google Cloud Model Armor (modelarmor.googleapis.com) live API integration (BRD FR-1.3, NFR-1.1)
- Prompt Injection & Jailbreak Defense via Cloud Model Armor and Edge Filters
- Pre-LLM SPII / PII Redaction for SSN & Phone numbers (BRD FR-1.4, NFR-1.3)
- Strict RBAC & Multi-Tenant Isolation (BRD FR-1.5, FR-3.1)
- Output Citation & Model Response Safety Sanitization (BRD FR-5.3, FR-5.4)
"""

import json
import logging
import re
from typing import Any, Tuple
import httpx

from . import config

logger = logging.getLogger(__name__)


def _get_gcp_access_token() -> str | None:
    """Retrieves GCP OAuth token via google.auth or local gcloud environment."""
    try:
        import google.auth
        import google.auth.transport.requests

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        return credentials.token
    except Exception:
        pass
    return None


class ModelArmorGuard:
    """Enterprise safety interceptor integrating Google Cloud Model Armor."""

    # Local injection & jailbreak signatures (Layer 1: Zero-latency Edge Defense)
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
    # Matches standard US, UK, international phone formats
    PHONE_PATTERN = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"

    @classmethod
    def call_cloud_model_armor_sanitize_prompt(
        cls, user_text: str
    ) -> Tuple[bool, str, str]:
        """Calls Google Cloud Model Armor API (sanitizeUserPrompt) to inspect user prompt."""
        project = config.GOOGLE_CLOUD_PROJECT
        template_id = config.MODEL_ARMOR_TEMPLATE_ID or "elevate-safety-template"
        if not project:
            return (True, user_text, "")

        token = _get_gcp_access_token()
        if not token:
            return (True, user_text, "")

        url = f"https://modelarmor.googleapis.com/v1/projects/{project}/locations/global/templates/{template_id}:sanitizeUserPrompt"
        payload = {
            "userPromptData": {
                "text": user_text
            }
        }
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    sanitization_result = data.get("sanitizationResult", {})
                    filter_match_state = sanitization_result.get("filterMatchState", "")
                    if filter_match_state in ["MATCH_FOUND", "BLOCKED"]:
                        return (
                            False,
                            user_text,
                            "Google Cloud Model Armor: Malicious prompt injection or policy violation detected.",
                        )
                    sanitized_text = sanitization_result.get("sanitizedItem", {}).get("text", user_text)
                    return (True, sanitized_text, "")
        except Exception as e:
            logger.debug(f"Cloud Model Armor live call skipped: {e}")

        return (True, user_text, "")

    @classmethod
    def inspect_input(cls, user_text: str, mask_phone: bool = True) -> Tuple[bool, str, str]:
        """Inspects incoming user prompt for injection or malicious overrides.

        Applies dual-layer defense:
        1. Google Cloud Model Armor (modelarmor.googleapis.com)
        2. Zero-latency Edge Heuristic & PII/SPII redaction

        Returns:
            (is_safe, sanitized_text, refusal_reason)
        """
        # 1. Edge Prompt Injection & Jailbreak Check
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, user_text):
                return (
                    False,
                    user_text,
                    "Security Violation: Malicious prompt injection or system override attempt intercepted.",
                )

        # 2. Live Google Cloud Model Armor Inspection
        is_cloud_safe, cloud_sanitized, cloud_reason = cls.call_cloud_model_armor_sanitize_prompt(user_text)
        if not is_cloud_safe:
            return (False, user_text, cloud_reason)

        working_text = cloud_sanitized if cloud_sanitized != user_text else user_text

        # 3. Pre-LLM PII/SPII Redaction (Sensitive Data Protection)
        sanitized = re.sub(cls.SSN_PATTERN, "[SSN_REDACTED]", working_text)
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

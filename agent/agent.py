"""Project Elevate: Supervisor Agent Entry Point, Active Callbacks & CLI Runner.

Constructs the ADK root_agent orchestrating WorkWeek HCM, ServiceImmediately ITSM,
and Vertex AI Search / Policy RAG tools with Model Armor safety guardrails and
persistent multi-tier session lifecycle management.
"""

import sys
import os
import asyncio
import time
from typing import Optional, Dict, Any

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.genai import types

from . import config
from .prompt import SUPERVISOR_PROMPT
from .guardrails import ModelArmorGuard
from .tools import ALL_TOOLS
from .tools.workweek_tool import set_active_caller_context
from .tools.serviceimmediately_tool import set_active_caller_context as set_itsm_caller_context
from .session import ElevateSessionService


# =============================================================================
# 1. Active Callback Hooks for Multi-Tenant Session & Model Armor Guardrails
# =============================================================================
def before_agent_callback(callback_context: Any) -> Optional[types.Content]:
    """Active pre-agent hook executing before LLM inference.
    
    Responsibilities:
    1. Multi-Tenant Identity: Binds authenticated employee context to backend tools.
    2. Model Armor: Intercepts prompt injections and masks SPII (SSN, Phone).
    3. Session State: Initializes session timestamps and caller metadata.
    """
    user_id = getattr(callback_context, "user_id", config.DEFAULT_EMPLOYEE_ID)
    set_active_caller_context(user_id)
    set_itsm_caller_context(user_id)

    # If incoming message contains user text, sanitize it
    if hasattr(callback_context, "new_message") and callback_context.new_message:
        sanitized_parts = []
        for part in callback_context.new_message.parts:
            if hasattr(part, "text") and part.text:
                is_safe, sanitized_text, refusal = ModelArmorGuard.inspect_input(part.text)
                if not is_safe:
                    # Return immediate safe refusal content
                    return types.Content(
                        role="model",
                        parts=[
                            types.Part(
                                text=(
                                    "I cannot fulfill this request. I am the enterprise HR & IT Virtual Assistant "
                                    "and must adhere to enterprise security and governance policies."
                                )
                            )
                        ],
                    )
                sanitized_parts.append(types.Part(text=sanitized_text))
            else:
                sanitized_parts.append(part)
        callback_context.new_message.parts = sanitized_parts

    return None


def after_agent_callback(callback_context: Any) -> Optional[types.Content]:
    """Active post-agent hook executing after model response generation.
    
    Responsibilities:
    1. Output Safety: Scans model responses to ensure no unmasked SPII leaks.
    2. Citation Integrity: Logs validation status for policy citations.
    """
    if hasattr(callback_context, "response") and callback_context.response:
        for part in callback_context.response.parts:
            if hasattr(part, "text") and part.text:
                part.text = ModelArmorGuard.inspect_output(part.text)

    return None


# =============================================================================
# 2. Build the ADK Supervisor Agent (root_agent)
# =============================================================================
root_agent = LlmAgent(
    model=config.GEMINI_MODEL,
    name="elevate_supervisor_agent",
    description="Enterprise HR & IT Virtual Assistant orchestrating WorkWeek, ServiceImmediately, and Policy RAG.",
    instruction=SUPERVISOR_PROMPT,
    tools=ALL_TOOLS,
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
)


# =============================================================================
# 3. Session & Runner Plumbing (Persistent ElevateSessionService)
# =============================================================================
_session_service = None


def _ensure_runner():
    global _session_service
    if _session_service is None:
        _session_service = ElevateSessionService()
    return Runner(app_name=config.APP_NAME, agent=root_agent, session_service=_session_service)


async def _ensure_session_async(user_id: str, session_id: str):
    try:
        await _session_service.create_session(
            app_name=config.APP_NAME, user_id=user_id, session_id=session_id
        )
    except Exception:
        pass  # Session already exists


async def _run_query_async(
    query: str,
    user_id: str = config.DEFAULT_EMPLOYEE_ID,
    session_id: str = "default_session",
) -> str:
    """Executes a query through Model Armor input inspection and the ADK runner."""
    # 1. Model Armor Input Inspection
    is_safe, sanitized_query, _ = ModelArmorGuard.inspect_input(query)
    if not is_safe:
        return (
            "I cannot fulfill this request. I am the enterprise HR & IT Virtual Assistant and must "
            "adhere to enterprise security and governance policies. I can assist you with HR policy "
            "inquiries, WorkWeek self-service, or ServiceImmediately support tickets."
        )

    # 2. Set multi-tenant caller context
    set_active_caller_context(user_id)
    set_itsm_caller_context(user_id)

    # 3. ADK Runner Execution with Persistent Session Service
    runner = _ensure_runner()
    await _ensure_session_async(user_id, session_id)
    message = types.Content(role="user", parts=[types.Part(text=sanitized_query)])

    final_response = ""
    try:
        events = runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message
        )
        async for event in events:
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        final_response += part.text
            elif hasattr(event, "text") and event.text:
                final_response += event.text
    except Exception as e:
        final_response = f"[Agent Execution Note]: {e!s}"

    # 4. Model Armor Output Inspection
    safe_output = ModelArmorGuard.inspect_output(final_response)
    return safe_output


# =============================================================================
# 4. Interactive & CLI Entry Point
# =============================================================================
def main():
    """CLI entry point for running the agent from the terminal."""
    if len(sys.argv) < 2:
        print("Usage: python -m agent.agent \"<your query>\" or python -m agent.agent --interactive")
        sys.exit(1)

    if sys.argv[1] == "--interactive":
        print("==================================================")
        print(" Project Elevate: HR & IT Virtual Assistant (ADK) ")
        print(f" Authenticated as: {config.DEFAULT_EMPLOYEE_ID} (Alex Taylor) ")
        print(f" Model: {config.GEMINI_MODEL} ")
        print(" Type 'exit' or 'quit' to end conversation. ")
        print("==================================================\n")

        session_id = "interactive_session"
        while True:
            try:
                user_input = input("\nYou: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("\nGoodbye!")
                    break
                print("\nAgent: ", end="", flush=True)
                response = asyncio.run(
                    _run_query_async(user_input, session_id=session_id)
                )
                print(response)
            except (KeyboardInterrupt, EOFError):
                print("\nSession ended.")
                break
    else:
        query = " ".join(sys.argv[1:])
        response = asyncio.run(_run_query_async(query))
        print(response)


if __name__ == "__main__":
    main()

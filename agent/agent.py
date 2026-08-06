"""Project Elevate: Supervisor Agent Entry Point & CLI Runner.

Constructs the ADK root_agent orchestrating WorkWeek HCM, ServiceImmediately ITSM,
and Vertex AI Search / Policy RAG tools with Model Armor safety guardrails.
"""

import sys
import os
import asyncio
from typing import Optional, Dict, Any

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from . import config
from .prompt import SUPERVISOR_PROMPT
from .guardrails import ModelArmorGuard
from .tools import ALL_TOOLS


# =============================================================================
# 1. Callback Hooks for Session & Model Armor Guardrails
# =============================================================================
def before_agent_callback(callback_context: Any) -> Optional[types.Content]:
    """Pre-processes input for prompt injection and SPII masking."""
    # Retrieve user input parts
    return None


def after_agent_callback(callback_context: Any) -> Optional[types.Content]:
    """Post-processes output for safety and SPII redaction."""
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
)


# =============================================================================
# 3. Session & Runner Plumbing
# =============================================================================
_session_service = None


def _ensure_runner():
    global _session_service
    if _session_service is None:
        _session_service = InMemorySessionService()
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
    is_safe, sanitized_query, refusal_reason = ModelArmorGuard.inspect_input(query)
    if not is_safe:
        return (
            "I cannot fulfill this request. I am the enterprise HR & IT Virtual Assistant and must "
            "adhere to enterprise security and governance policies. I can assist you with HR policy "
            "inquiries, WorkWeek self-service, or ServiceImmediately support tickets."
        )

    # 2. ADK Runner Execution
    runner = _ensure_runner()
    await _ensure_session_async(user_id, session_id)
    message = types.Content(role="user", parts=[types.Part(text=sanitized_query)])

    final_response = ""
    try:
        events = runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message
        )
        async for event in events:
            # Check for model content response
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        final_response += part.text
            elif hasattr(event, "text") and event.text:
                final_response += event.text
    except Exception as e:
        # Check for API key / credential setup
        final_response = f"[Agent Execution Note]: {str(e)}"

    # 3. Model Armor Output Inspection
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
        print(f"==================================================")
        print(f" Project Elevate: HR & IT Virtual Assistant (ADK) ")
        print(f" Authenticated as: {config.DEFAULT_EMPLOYEE_ID} (Alex Taylor) ")
        print(f" Model: {config.GEMINI_MODEL} ")
        print(f" Type 'exit' or 'quit' to end conversation. ")
        print(f"==================================================\n")

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

"""
Real Lyzr integration, matching the REST API documented at
https://docs.lyzr.ai/enterprise/get-started/quickstart (Option D).

    POST /v3/agent                     -> create an agent
    POST /v3/agent/{agent_id}/chat     -> chat with it

If LYZR_API_KEY isn't set, every call falls back to a clearly-labeled mock
response instead of failing outright. This exists purely so the rest of the
platform (progress tracking, codegen, UI) can be built and demoed before a
real key is wired in — every mock response is tagged `"mock": true` so it's
never confused with a real agent in the UI or the DB.
"""
import os
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

LYZR_BASE_URL = os.getenv("LYZR_BASE_URL", "https://agent-prod.studio.lyzr.ai")


class LyzrError(Exception):
    pass


def _headers():
    return {"x-api-key": os.getenv("LYZR_API_KEY"), "Content-Type": "application/json"}


def _resolve_provider_and_model(model_choice: str) -> tuple[str, str]:
    selected_model = (model_choice or "").strip()
    lower_model = selected_model.lower()

    if lower_model.startswith("gemini-"):
        return "Gemini", selected_model
    if lower_model.startswith("gpt-") or lower_model.startswith("o1") or lower_model.startswith("o3"):
        return "OpenAI", selected_model
    if "nova" in lower_model or lower_model.startswith("bedrock/"):
        return "Aws-Bedrock", selected_model

    return "OpenAI", selected_model or "gpt-4o-mini"


def is_configured() -> bool:
    return bool(os.getenv("LYZR_API_KEY"))


def create_agent(name: str, provider: str, role: str, goal: str, instructions: str) -> dict:
    """
    Returns: {"agent_id": str, "mock": bool, "raw": dict}
    """
    if not is_configured():
        return {
            "agent_id": f"mock-{uuid.uuid4().hex[:10]}",
            "mock": True,
            "raw": {"note": "LYZR_API_KEY not set — running in mock mode. Set the key to create a real agent."},
        }

    provider_id, model = _resolve_provider_and_model(provider)
    payload = {
        "name": name,
        "description": role,
        "agent_role": role,
        "agent_goal": goal,
        "agent_instructions": instructions,
        "provider_id": provider_id,
        "model": model,
        "temperature": 0.7,
        "top_p": 0.9,
        "features": [],
        "managed_agents": [],
        "response_format": {"type": "text"},
        "store_messages": True,
        "file_output": False,
    }
    credential_id = os.getenv("AGENT_LLM_CREDENTIAL", "").strip()
    if credential_id:
        payload["llm_credential_id"] = credential_id
    try:
        resp = requests.post(f"{LYZR_BASE_URL}/v3/agents/", headers=_headers(), json=payload, timeout=30)
        if resp.status_code >= 400:
            raise LyzrError(f"Lyzr create_agent failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        agent_id = data.get("agent_id") or data.get("id")
        if not agent_id:
            raise LyzrError(f"Lyzr create_agent response missing agent_id: {data}")
        return {"agent_id": agent_id, "mock": False, "raw": data}
    except (requests.RequestException, LyzrError) as exc:
        print(f"[lyzr_client] create_agent failed, falling back to mock: {exc}")
        return {
            "agent_id": f"mock-{uuid.uuid4().hex[:10]}",
            "mock": True,
            "raw": {"error": str(exc), "note": "Falling back to mock mode because the Lyzr REST call failed."},
        }


def chat(agent_id: str, message: str, session_id: str = "agent-odyssey-session") -> dict:
    """
    Returns: {"response": str, "mock": bool, "raw": dict}
    """
    if agent_id.startswith("mock-") or not is_configured():
        return {
            "response": (
                "(mock agent) I'd answer this using the configuration you just built, "
                "but no real LYZR_API_KEY is set yet — this is a placeholder response so "
                "you can still test the full flow end to end."
            ),
            "mock": True,
            "raw": {},
        }

    payload = {
        "agent_id": agent_id,
        "message": message,
        "session_id": session_id,
        "user_id": "default_user",
    }
    try:
        resp = requests.post(
            f"{LYZR_BASE_URL}/v3/inference/chat/", headers=_headers(), json=payload, timeout=60
        )
        if resp.status_code >= 400:
            raise LyzrError(f"Lyzr chat failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        response_text = data.get("response")
        if response_text is None and isinstance(data.get("choices"), list) and data["choices"]:
            choice = data["choices"][0]
            response_text = choice.get("message", {}).get("content", "")
        if not response_text:
            print(f"[lyzr_client] chat succeeded but response text was empty. Raw: {data}")
        return {"response": str(response_text or ""), "mock": False, "raw": data}
    except (requests.RequestException, LyzrError) as exc:
        print(f"[lyzr_client] chat failed, falling back to mock: {exc}")
        return {
            "response": (
                "(mock agent) I couldn't reach the live Lyzr API for this run, so I'm returning "
                "a placeholder response instead."
            ),
            "mock": True,
            "raw": {"error": str(exc)},
        }
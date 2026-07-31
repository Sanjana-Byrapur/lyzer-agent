"""
The reference HTML's mentor panel was an explicit stub:
    "Integration point — will call the real mentor agent per screen context"

This makes it real. The mentor is itself a Lyzr agent (created once, lazily,
and reused across the whole platform) whose job is to explain trade-offs
for whatever screen/mission the user is currently on — never to just hand
over the finished answer.

If no Lyzr key is configured, falls back to genuinely useful per-screen
guidance pulled from the mission's own `assist` block, instead of a canned
generic message — so the fallback is still worth reading, not just filler.
"""
from . import lyzr_client

_MENTOR_AGENT_ID = None
_MENTOR_ROLE = "Context-aware build mentor for an AI agent creation platform"
_MENTOR_GOAL = "Help the user understand trade-offs in their current step without ever giving the exact answer"
_MENTOR_INSTRUCTIONS = (
    "You are embedded in a gamified platform where developers build real AI agents "
    "mission by mission. You will be told which screen and mission the user is "
    "currently on, plus any relevant trade-off/mistake notes for that mission. "
    "Explain the trade-off clearly and briefly. If the user asks a direct question, "
    "answer it, but never fill in a mission's TODO slot value for them directly — "
    "point them toward how to decide, not the specific value to type."
)


def _get_mentor_agent_id() -> str:
    global _MENTOR_AGENT_ID
    if _MENTOR_AGENT_ID is None:
        created = lyzr_client.create_agent(
            name="Agent Odyssey Mentor",
            provider="gpt-4o-mini",
            role=_MENTOR_ROLE,
            goal=_MENTOR_GOAL,
            instructions=_MENTOR_INSTRUCTIONS,
        )
        _MENTOR_AGENT_ID = created["agent_id"]
    return _MENTOR_AGENT_ID


_SCREEN_FALLBACK = {
    "campaign": "Pick a campaign to start — I'll walk with you through every mission after this.",
    "setup": "Cloning the template gets you boilerplate for free. Starting from scratch means you own folder structure too — good if you want the extra rep.",
    "levelintro": "Each mission builds on the last one in this level. Nothing runs until all of them are done.",
    "ministeps": "This is the shape of what's coming — no code yet. Skim it so nothing in the editor surprises you.",
    "levelcomplete": "Nice — that file is fully yours now. Ready for the next level whenever you are.",
    "summary": "That's a full agent, end to end, actually created via Lyzr. Want a harder variant next time?",
}


def get_context_message(campaign: dict | None, screen: str, mission: dict | None, user_message: str | None) -> dict:
    """
    Returns {"message": str, "mock": bool}.
    Always tries the real mentor agent first if Lyzr is configured; otherwise
    (or on any failure) falls back to genuinely specific guidance instead of
    silently failing.
    """
    context_note = f"Screen: {screen}."
    if campaign:
        context_note += f" Campaign: {campaign['title']}."
    if mission:
        context_note += f" Mission: {mission['title']}. Assist notes: {mission.get('assist', {})}"

    prompt = context_note
    if user_message:
        prompt += f"\n\nUser asked: {user_message}"
    else:
        prompt += "\n\nGive a short, contextual tip for where the user is right now."

    if lyzr_client.is_configured():
        try:
            agent_id = _get_mentor_agent_id()
            result = lyzr_client.chat(agent_id, prompt)
            return {"message": result["response"], "mock": result["mock"]}
        except Exception:
            pass  # fall through to the fallback below rather than error the whole request

    # Fallback: prefer mission-specific trade-off notes over the generic screen message
    if mission and mission.get("assist", {}).get("tradeoffs"):
        return {"message": mission["assist"]["tradeoffs"], "mock": True}
    return {"message": _SCREEN_FALLBACK.get(screen, "Keep going — you've got this."), "mock": True}

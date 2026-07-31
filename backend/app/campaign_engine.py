"""
Campaign engine: the headless core of the whole platform.

Everything here operates on plain dicts loaded from JSON + the DB progress
row. No HTTP, no rendering — this is the part you can unit test without
ever starting a server, which is exactly why it's separate from main.py.
"""
import json
import os
from typing import Optional
from . import models

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "campaigns")


class CampaignError(Exception):
    pass


def _load_campaign_file(campaign_key: str) -> dict:
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(DATA_DIR, fname), "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("key") == campaign_key:
            return data
    raise CampaignError(f"No campaign found with key '{campaign_key}'")


def list_campaigns() -> list[dict]:
    campaigns = []
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(DATA_DIR, fname), "r", encoding="utf-8") as f:
            campaigns.append(json.load(f))
    return campaigns


def get_campaign(campaign_key: str) -> dict:
    return _load_campaign_file(campaign_key)


def find_mission(campaign: dict, mission_key: str) -> Optional[tuple[dict, dict]]:
    """Returns (level, mission) for a given mission_key, or None."""
    for level in campaign["levels"]:
        for mission in level["missions"]:
            if mission["key"] == mission_key:
                return level, mission
    return None


def total_xp(campaign: dict) -> int:
    return sum(m["reward"] for level in campaign["levels"] for m in level["missions"])


def get_or_create_progress(db, user_id: int, campaign_key: str) -> models.CampaignProgress:
    progress = (
        db.query(models.CampaignProgress)
        .filter_by(user_id=user_id, campaign_key=campaign_key)
        .first()
    )
    if progress is None:
        progress = models.CampaignProgress(
            user_id=user_id,
            campaign_key=campaign_key,
            slot_values={},
            completed_missions=[],
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress


def submit_slot(db, progress: models.CampaignProgress, campaign: dict, mission_key: str, slot_key: str, value):
    result = find_mission(campaign, mission_key)
    if result is None:
        raise CampaignError(f"Unknown mission '{mission_key}'")
    _, mission = result

    valid_keys = {s["key"] for s in mission["slots"]}
    if slot_key not in valid_keys:
        raise CampaignError(f"'{slot_key}' is not a valid slot for mission '{mission_key}'")

    # Coerce numeric slot types so downstream codegen/Lyzr calls get real numbers,
    # not strings that happen to look like numbers.
    slot_def = next(s for s in mission["slots"] if s["key"] == slot_key)
    if slot_def["type"] == "number" and value is not None and value != "":
        try:
            value = float(value)
            if value == int(value):
                value = int(value)
        except (TypeError, ValueError):
            raise CampaignError(f"'{slot_key}' expects a number, got '{value}'")

    values = dict(progress.slot_values or {})
    mission_values = dict(values.get(mission_key, {}))
    mission_values[slot_key] = value
    values[mission_key] = mission_values
    progress.slot_values = values
    db.commit()
    db.refresh(progress)
    return progress


def mission_checklist_state(progress: models.CampaignProgress, mission: dict) -> list[bool]:
    filled = progress.slot_values.get(mission["key"], {}) if progress.slot_values else {}
    return [
        (s["key"] in filled and filled[s["key"]] not in (None, ""))
        for s in mission["slots"]
    ]


def mission_is_complete_ready(progress: models.CampaignProgress, mission: dict) -> bool:
    checklist = mission_checklist_state(progress, mission)
    return all(checklist) and len(checklist) > 0


def complete_mission(db, progress: models.CampaignProgress, campaign: dict, mission_key: str) -> int:
    """Marks mission complete, awards XP to the user, returns XP awarded."""
    result = find_mission(campaign, mission_key)
    if result is None:
        raise CampaignError(f"Unknown mission '{mission_key}'")
    _, mission = result

    if not mission_is_complete_ready(progress, mission):
        raise CampaignError("Mission checklist is not fully filled yet")

    completed = list(progress.completed_missions or [])
    if mission_key not in completed:
        completed.append(mission_key)
    progress.completed_missions = completed
    db.commit()

    return mission["reward"]


def is_campaign_complete(progress: models.CampaignProgress, campaign: dict) -> bool:
    all_mission_keys = {m["key"] for level in campaign["levels"] for m in level["missions"]}
    completed = set(progress.completed_missions or [])
    return all_mission_keys.issubset(completed) and len(all_mission_keys) > 0


def collect_finalize_context(progress: models.CampaignProgress) -> dict:
    """Flattens all slot values across all missions into one dict for templating."""
    ctx = {}
    for mission_values in (progress.slot_values or {}).values():
        ctx.update(mission_values)
    return ctx

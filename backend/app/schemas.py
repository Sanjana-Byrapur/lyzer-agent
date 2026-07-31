from pydantic import BaseModel
from typing import Optional, Any


class CampaignSummary(BaseModel):
    key: str
    title: str
    badge: str
    description: str
    estMinutes: int
    locked: bool
    levelCount: int
    totalXp: int


class SetupChoice(BaseModel):
    mode: str  # "clone" | "scratch"


class SlotSubmission(BaseModel):
    mission_key: str
    slot_key: str
    value: Any


class MissionCompletion(BaseModel):
    mission_key: str


class MentorMessage(BaseModel):
    campaign_key: Optional[str] = None
    screen: str  # campaign | setup | levelintro | ministeps | editor | levelcomplete | summary
    mission_key: Optional[str] = None
    user_message: Optional[str] = None


class ChatMessage(BaseModel):
    message: str

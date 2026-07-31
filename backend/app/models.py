from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    """
    Minimal user record. Wire this up to real auth later —
    for now a user is just created on first contact (see get_or_create_user).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String, nullable=False, default="Builder")
    xp = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)

    progress = relationship("CampaignProgress", back_populates="user")
    agents = relationship("CreatedAgent", back_populates="user")


class CampaignProgress(Base):
    """
    One row per (user, campaign). Tracks which setup mode was picked,
    current level/mission pointer, and all slot values filled so far
    (stored as JSON keyed by mission_key -> {slot_key: value}).
    """
    __tablename__ = "campaign_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    campaign_key = Column(String, nullable=False)

    setup_mode = Column(String, nullable=True)  # "clone" | "scratch"
    current_level_index = Column(Integer, default=0)
    current_mission_index = Column(Integer, default=0)

    slot_values = Column(JSON, default=dict)      # {mission_key: {slot_key: value}}
    completed_missions = Column(JSON, default=list)  # [mission_key, ...]

    status = Column(String, default="in_progress")  # in_progress | completed
    started_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="progress")


class CreatedAgent(Base):
    """
    A real agent created via the Lyzr API at the end of a campaign.
    lyzr_agent_id is what you use to chat with it afterwards.
    """
    __tablename__ = "created_agents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    campaign_key = Column(String, nullable=False)

    name = Column(String, nullable=False)
    lyzr_agent_id = Column(String, nullable=True)  # null if created in mock mode
    mock = Column(Boolean, default=False)
    config_snapshot = Column(JSON, default=dict)
    generated_code = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="agents")

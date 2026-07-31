from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas, campaign_engine, codegen, lyzr_client, mentor
from .database import engine, get_db, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Agent Odyssey", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- temporary single-user shim -------------------------------------------
# Real auth isn't in scope for the MVP. Every request operates as user #1,
# created on first boot. Swap this for real session/JWT auth later — nothing
# else in the app needs to change since everything already keys off user_id.
def get_current_user(db: Session = Depends(get_db)) -> models.User:
    user = db.query(models.User).first()
    if user is None:
        user = models.User(display_name="Builder", xp=0)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# --- Campaigns --------------------------------------------------------------

@app.get("/campaigns", response_model=list[schemas.CampaignSummary])
def list_campaigns():
    campaigns = campaign_engine.list_campaigns()
    return [
        schemas.CampaignSummary(
            key=c["key"],
            title=c["title"],
            badge=c["badge"],
            description=c["description"],
            estMinutes=c["estMinutes"],
            locked=c["locked"],
            levelCount=len(c["levels"]),
            totalXp=campaign_engine.total_xp(c),
        )
        for c in campaigns
    ]


@app.get("/campaigns/{campaign_key}")
def get_campaign_detail(
    campaign_key: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        campaign = campaign_engine.get_campaign(campaign_key)
    except campaign_engine.CampaignError as e:
        raise HTTPException(404, str(e))

    progress = campaign_engine.get_or_create_progress(db, user.id, campaign_key)
    return {
        "campaign": campaign,
        "progress": {
            "setup_mode": progress.setup_mode,
            "slot_values": progress.slot_values,
            "completed_missions": progress.completed_missions,
            "status": progress.status,
        },
    }


@app.post("/campaigns/{campaign_key}/setup")
def choose_setup(
    campaign_key: str,
    body: schemas.SetupChoice,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    campaign = campaign_engine.get_campaign(campaign_key)  # 404s via exception if missing
    if body.mode not in campaign["setup"]["options"]:
        raise HTTPException(400, f"Invalid setup mode '{body.mode}'")

    progress = campaign_engine.get_or_create_progress(db, user.id, campaign_key)
    progress.setup_mode = body.mode
    db.commit()
    return {"commands": campaign["setup"]["options"][body.mode]["commands"]}


# --- Missions ----------------------------------------------------------------

@app.post("/campaigns/{campaign_key}/slots")
def submit_slot(
    campaign_key: str,
    body: schemas.SlotSubmission,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        campaign = campaign_engine.get_campaign(campaign_key)
        progress = campaign_engine.get_or_create_progress(db, user.id, campaign_key)
        progress = campaign_engine.submit_slot(
            db, progress, campaign, body.mission_key, body.slot_key, body.value
        )
    except campaign_engine.CampaignError as e:
        raise HTTPException(400, str(e))

    _, mission = campaign_engine.find_mission(campaign, body.mission_key)
    # Use cumulative context across ALL missions completed/filled so far in this
    # campaign, not just this mission's own slots — a mission's file (like agent.py)
    # keeps growing across missions, so mission 2's template needs mission 1's
    # already-filled values (model, instructions, temperature) too.
    cumulative_values = campaign_engine.collect_finalize_context(progress)
    code_preview = codegen.render_mission_code(mission, cumulative_values)
    checklist = campaign_engine.mission_checklist_state(progress, mission)

    return {
        "checklist": checklist,
        "checklist_labels": mission["checklist"] if "checklist" in mission else [s["label"] for s in mission["slots"]],
        "ready_to_complete": all(checklist) and len(checklist) > 0,
        "code_preview": code_preview,
    }


@app.post("/campaigns/{campaign_key}/missions/complete")
def complete_mission(
    campaign_key: str,
    body: schemas.MissionCompletion,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        campaign = campaign_engine.get_campaign(campaign_key)
        progress = campaign_engine.get_or_create_progress(db, user.id, campaign_key)
        xp_awarded = campaign_engine.complete_mission(db, progress, campaign, body.mission_key)
    except campaign_engine.CampaignError as e:
        raise HTTPException(400, str(e))

    user.xp += xp_awarded
    db.commit()

    campaign_complete = campaign_engine.is_campaign_complete(progress, campaign)
    finalize_result = None

    if campaign_complete and progress.status != "completed":
        finalize_result = _finalize_campaign(db, user, progress, campaign)
        progress.status = "completed"
        db.commit()

    return {
        "xp_awarded": xp_awarded,
        "total_xp": user.xp,
        "campaign_complete": campaign_complete,
        "finalize_result": finalize_result,
    }


def _finalize_campaign(db: Session, user: models.User, progress: models.CampaignProgress, campaign: dict) -> dict:
    """
    The real payoff: build a Lyzr agent from everything the user filled in
    across every mission, create it for real, and run one test message
    against it so the platform can prove — not just claim — the agent works.
    """
    ctx = campaign_engine.collect_finalize_context(progress)
    ctx["user"] = user.display_name
    finalize_cfg = campaign["finalize"]

    name = codegen.render_finalize_string(finalize_cfg["agentNameTemplate"], ctx)
    role = codegen.render_finalize_string(finalize_cfg["role"], ctx)
    goal = codegen.render_finalize_string(finalize_cfg["goalTemplate"], ctx)
    instructions = ctx.get("instructions", "Be accurate and cite retrieved context where possible.")

    created = lyzr_client.create_agent(
        name=name,
        provider=ctx.get("model", "gpt-4o-mini"),
        role=role,
        goal=goal,
        instructions=instructions,
    )

    test_message = finalize_cfg.get("testMessage", "Hello — what can you help me with?")
    chat_result = lyzr_client.chat(created["agent_id"], test_message)

    agent_record = models.CreatedAgent(
        user_id=user.id,
        campaign_key=campaign["key"],
        name=name,
        lyzr_agent_id=created["agent_id"],
        mock=created["mock"],
        config_snapshot=ctx,
        generated_code=None,
    )
    db.add(agent_record)
    db.commit()
    db.refresh(agent_record)

    return {
        "agent_db_id": agent_record.id,
        "agent_id": created["agent_id"],
        "agent_name": name,
        "mock": created["mock"],
        "test_message": test_message,
        "test_response": chat_result["response"],
    }


# --- Chat with a finished agent ---------------------------------------------

@app.post("/agents/{agent_db_id}/chat")
def chat_with_agent(agent_db_id: int, body: schemas.ChatMessage, db: Session = Depends(get_db)):
    agent = db.query(models.CreatedAgent).filter_by(id=agent_db_id).first()
    if agent is None:
        raise HTTPException(404, "Agent not found")
    result = lyzr_client.chat(agent.lyzr_agent_id, body.message)
    return {"response": result["response"], "mock": result["mock"]}


# --- Mentor ------------------------------------------------------------------

@app.post("/mentor")
def ask_mentor(body: schemas.MentorMessage):
    campaign = None
    mission = None
    if body.campaign_key:
        try:
            campaign = campaign_engine.get_campaign(body.campaign_key)
            if body.mission_key:
                found = campaign_engine.find_mission(campaign, body.mission_key)
                if found:
                    _, mission = found
        except campaign_engine.CampaignError:
            pass

    result = mentor.get_context_message(campaign, body.screen, mission, body.user_message)
    return result


@app.get("/health")
def health():
    return {"status": "ok", "lyzr_configured": lyzr_client.is_configured()}

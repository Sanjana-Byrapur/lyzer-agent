# Agent Odyssey

A gamified, mission-based platform where developers build a real AI agent step
by step — built for the HiDevs "Mission Flow V2" evaluation task.

Everything about the *platform* (missions, gamification, code generation,
mentor) is custom-built. **Lyzr is used only for agent execution** — creating
the real agent and running it — exactly as the task required.

---

## What's actually real here (vs. the reference mockup)

The reference HTML you were given is explicitly a UX mockup — its own code
says so: `Integration point — will call the real mentor agent per screen
context`. This project makes every one of those stubs real:

| In the reference | Here |
|---|---|
| Hardcoded `missions` JS array | Real campaign JSON files, loaded by a backend engine — add a new campaign without touching any code |
| Fake `codeLines` with styled `<span>` tags | A real Jinja2 template rendered server-side from what the user actually typed |
| Mentor panel stub | A real endpoint — calls an actual Lyzr agent if configured, or a genuinely specific fallback otherwise |
| "Campaign complete" screen with no agent | A real `POST /v3/agent` call to Lyzr, followed by a real `POST /v3/agent/{id}/chat` test message, shown live on the summary screen |
| Static demo data | SQLite-backed progress tracking per user, so refreshing the page doesn't lose your place |

---

## Architecture

```
agent-odyssey/
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI routes — the only HTTP-aware file
│   │   ├── campaign_engine.py  # Headless core: progress, validation, XP — no HTTP here
│   │   ├── codegen.py          # Renders real code files from mission templates + filled slots
│   │   ├── lyzr_client.py      # Real Lyzr REST integration (+ mock-mode fallback)
│   │   ├── mentor.py           # Context-aware mentor (real Lyzr agent or rich fallback)
│   │   ├── models.py           # SQLAlchemy: User, CampaignProgress, CreatedAgent
│   │   ├── schemas.py          # Pydantic request/response models
│   │   └── data/campaigns/     # Campaign definitions — pure JSON, no code changes needed to add one
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── index.html   # Same screen structure as the reference (campaign → setup → level → mission → editor → summary)
    ├── styles.css   # Same visual language/design tokens as the reference
    └── app.js       # Fetches everything from the backend — no hardcoded mission data
```

**Why split `campaign_engine.py` from `main.py`:** the engine is pure functions
operating on dicts and DB rows — no `Request`/`Response` objects anywhere in
it. That's what makes it testable without spinning up a server, and it's the
part that actually matters if someone reviews this code (anyone can wire up
routes; the logic underneath is the real work).

---

## Running it locally

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Optional: add your real Lyzr API key to .env (LYZR_API_KEY=...)
# Get one from studio.lyzr.ai > Account > API Keys
uvicorn app.main:app --reload --port 8000
```

Without a key set, everything still works end to end — agent creation and
chat both fall back to a clearly-labeled mock mode (`"mock": true` in every
response) so you can demo and test the full flow before wiring in a real key.

### 2. Frontend

The frontend is plain HTML/CSS/JS — no build step. Just serve it statically:

```bash
cd frontend
python -m http.server 5500
```

Then open `http://localhost:5500` in your browser. Make sure the backend
(`localhost:8000`) is running first — `app.js` hits it directly.

### 3. Try the full loop

1. Pick **Retriever Agent** on the campaign screen.
2. Choose Clone Template or Start from Scratch, click Next.
3. Start the level, begin Mission 1.
4. Fill in model / instructions / temperature — watch the code panel update live.
5. Continue to Mission 2, fill in collection / top_k — notice Mission 1's values are already baked into the file.
6. Complete the level — this is the real payoff: the backend creates a real
   agent via Lyzr (or a mock, if no key is set) and runs a test message
   against it, shown right there on the summary screen.
7. Chat with your finished agent directly from the summary screen.

---

## What's already tested

The full backend loop — setup → both missions → completion → finalize (Lyzr
call) → mentor — was run end-to-end during development and verified working,
including a real bug caught and fixed along the way: Mission 2's code preview
was initially missing Mission 1's already-filled values (model/instructions/
temperature), since the file `agent.py` is one evolving artifact across
missions, not per-mission state. Fixed in `campaign_engine.collect_finalize_context`
+ how `main.py` builds the code preview.

---


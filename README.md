# Agent Odyssey

A gamified, mission-based platform that guides developers through building **their own custom AI agent** from scratch.

Instead of overwhelming users with long configuration forms, Agent Odyssey transforms agent development into a guided learning journey. Each mission collects only the information needed at that stage, gradually assembling a complete AI agent ready for deployment.

Built for the **HiDevs Mission Flow V2** evaluation.

---

# Design Philosophy

Most AI agent platforms expect users to understand prompts, models, tools, retrieval systems, and deployment before they can even get started.

Agent Odyssey changes that experience.

Instead of exposing every configuration option upfront, the platform:

- Breaks development into guided missions
- Collects only the required information at each step
- Explains every decision
- Generates the agent configuration progressively
- Creates a working AI agent at the end using **Lyzr**

The focus is not just creating an AI agent, but making the entire developer journey intuitive and engaging.

---

# Features

- 🎯 Mission-based AI agent builder
- 🤖 Build any custom AI agent
- 📚 Guided developer experience
- 🧠 Context-aware AI mentor
- ⚡ Progressive code generation
- 💾 Persistent campaign progress
- 🔄 Dynamic mission engine
- 🚀 Lyzr agent deployment
- 💬 Chat with your generated agent
- 🎮 Gamified learning experience

---

# Agent Creation Flow

```text
Idea
   ↓
Define the Problem
   ↓
Define the Agent Role
   ↓
Choose the LLM
   ↓
Configure Instructions
   ↓
Select Knowledge Sources
   ↓
Choose Tools
   ↓
Review Configuration
   ↓
Generate Agent
   ↓
Deploy using Lyzr
   ↓
Chat with your Agent
```

---

# Architecture

```text
agent-odyssey/
├── backend/
│
│   ├── app/
│   │
│   ├── main.py
│   ├── campaign_engine.py
│   ├── codegen.py
│   ├── mentor.py
│   ├── lyzr_client.py
│   ├── models.py
│   ├── schemas.py
│   └── data/
│       └── campaigns/
│
├── frontend/
│
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
└── README.md
```

---

# How It Works

## Step 1 — Describe Your Agent

Tell Agent Odyssey what you want to build.

Example:

> Build an AI coding mentor that teaches DSA and reviews code.

---

## Step 2 — Guided Missions

Instead of asking for everything at once, the platform walks you through focused missions.

Examples:

- Define the agent's goal
- Choose the LLM
- Configure behavior
- Add knowledge sources
- Configure tools
- Review the final configuration

---

## Step 3 — Code Generation

As missions are completed, the backend progressively generates the underlying agent configuration and code templates.

---

## Step 4 — Agent Deployment

After the final mission, the platform sends the generated configuration to **Lyzr** to create a real AI agent.

---

## Step 5 — Test Your Agent

Immediately start chatting with the newly created agent from within the platform.

---

# Running Locally

## Backend

### macOS / Linux

```bash
cd backend

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
```

### Windows

```powershell
cd backend

py -m venv .venv

.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

copy .env.example .env
```

Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

---

## Frontend

```bash
cd frontend

python -m http.server 5500
```

Open

```
http://localhost:5500
```

---

# Environment Variables

Create a `.env` file.

```env
LYZR_API_KEY=your_api_key_here
```

If no API key is provided, the application automatically switches to **Mock Mode**, allowing the complete workflow to be demonstrated without creating a real Lyzr agent.

---

# Example Agents You Can Build

- Coding Mentor
- Research Assistant
- Resume Reviewer
- AI Tutor
- Travel Planner
- Startup Advisor
- Medical Assistant
- Legal Assistant
- Customer Support Bot
- HR Assistant
- Financial Advisor
- Personal Productivity Coach

Or simply describe your own idea.

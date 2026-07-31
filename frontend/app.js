const API_BASE = "http://localhost:8000";

/* ================= STATE ================= */
let xp = 0, seconds = 0, timerRunning = false;
let currentCampaignKey = null;
let currentCampaign = null;   // full campaign JSON from backend
let currentProgress = null;   // progress object from backend
let curLevelIndex = 0, curMissionIndex = 0;
let checklistState = [];
let activeAssistTab = "tradeoffs";

/* ================= SCREEN ROUTER ================= */
function goTo(name) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("show"));
  document.getElementById("screen-" + name).classList.add("show");
  if (!timerRunning) { timerRunning = true; startTimer(); }
  updateMentorContext(name);
}

function startTimer() {
  setInterval(() => {
    seconds++;
    const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
    const ss = String(seconds % 60).padStart(2, "0");
    document.getElementById("timerVal").textContent = `${mm}:${ss}`;
  }, 1000);
}

function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 1700);
}

/* ================= API HELPERS ================= */
async function api(path, method = "GET", body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API_BASE + path, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${method} ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

/* ================= CAMPAIGN SELECT ================= */
async function loadCampaigns() {
  const campaigns = await api("/campaigns");
  const grid = document.getElementById("campaignGrid");
  grid.innerHTML = "";
  campaigns.forEach(c => {
    const card = document.createElement("div");
    card.className = "ccard" + (c.locked ? " disabled" : "");
    card.innerHTML = `
      <div class="ccard-top"><h3>${c.title}</h3><span class="ccard-badge">${c.badge}</span></div>
      <p>${c.description}</p>
      <div class="ccard-meta"><span>${c.levelCount} level${c.levelCount > 1 ? "s" : ""}</span><span>~${c.estMinutes} min</span><span>${c.totalXp} XP</span></div>
    `;
    if (!c.locked) {
      card.addEventListener("click", () => selectCampaign(c.key));
    }
    grid.appendChild(card);
  });
}

async function selectCampaign(key) {
  currentCampaignKey = key;
  const detail = await api(`/campaigns/${key}`);
  currentCampaign = detail.campaign;
  currentProgress = detail.progress;
  curLevelIndex = 0;
  curMissionIndex = 0;
  renderSetupScreen();
  goTo("setup");
}

/* ================= SETUP SCREEN ================= */
let pickedSetupMode = "clone";

function renderSetupScreen() {
  const setup = currentCampaign.setup;
  document.getElementById("setupTitle").textContent = setup.title;
  document.getElementById("setupDesc").textContent = setup.description;

  const row = document.getElementById("setupToggleRow");
  row.innerHTML = "";
  Object.entries(setup.options).forEach(([modeKey, opt]) => {
    const div = document.createElement("div");
    div.className = "toggle-opt" + (modeKey === pickedSetupMode ? " on" : "");
    div.id = "opt-" + modeKey;
    div.innerHTML = `<b>${opt.label}</b><span>${opt.sub}</span>`;
    div.addEventListener("click", () => pickSetup(modeKey));
    row.appendChild(div);
  });
  renderTermBlock(pickedSetupMode);
}

function renderTermBlock(modeKey) {
  const opt = currentCampaign.setup.options[modeKey];
  const term = document.getElementById("termBlock");
  term.innerHTML = opt.commands.map(c => `<div><span class="p">$</span> ${escapeHtml(c)}</div>`).join("");
}

function pickSetup(modeKey) {
  pickedSetupMode = modeKey;
  document.querySelectorAll(".toggle-opt").forEach(el => el.classList.remove("on"));
  document.getElementById("opt-" + modeKey).classList.add("on");
  renderTermBlock(modeKey);
}

document.getElementById("setupNextBtn").addEventListener("click", async () => {
  await api(`/campaigns/${currentCampaignKey}/setup`, "POST", { mode: pickedSetupMode });
  renderLevelIntro();
  goTo("levelintro");
});

/* ================= LEVEL INTRO ================= */
function renderLevelIntro() {
  const level = currentCampaign.levels[curLevelIndex];
  document.getElementById("liCrumb").innerHTML = `<b>Level ${curLevelIndex + 1}</b> · ${escapeHtml(level.title)}`;
  document.getElementById("liNum").textContent = String(curLevelIndex + 1).padStart(2, "0");
  document.getElementById("liTitle").textContent = level.title;
  document.getElementById("liDesc").textContent = level.desc;

  const list = document.getElementById("levelMissionList");
  list.innerHTML = "";
  let totalXp = 0;
  level.missions.forEach((m, i) => {
    totalXp += m.reward;
    const row = document.createElement("div");
    row.className = "mission-row";
    row.innerHTML = `<span class="mission-idx">${i + 1}</span><span class="mr-name">${escapeHtml(m.title.replace(/^Mission \d+ — /, ""))}</span><span class="mr-xp">+${m.reward} XP</span>`;
    list.appendChild(row);
  });
  document.getElementById("levelXpNote").textContent = totalXp + " XP available";
}

document.getElementById("startLevelBtn").addEventListener("click", () => {
  curMissionIndex = 0;
  renderMiniSteps();
  goTo("ministeps");
});

/* ================= MINI-STEPS ================= */
function currentMission() {
  return currentCampaign.levels[curLevelIndex].missions[curMissionIndex];
}

function renderMiniSteps() {
  const m = currentMission();
  const level = currentCampaign.levels[curLevelIndex];
  document.getElementById("msCrumb").innerHTML = `<b>Level ${curLevelIndex + 1}</b> · Mission ${curMissionIndex + 1} of ${level.missions.length}`;
  document.getElementById("msTitle").textContent = m.title;
  document.getElementById("msDesc").textContent = m.desc;
  document.getElementById("msXpNote").textContent = `+${m.reward} XP on completion`;

  const flow = document.getElementById("stepFlow");
  flow.innerHTML = "";
  m.miniSteps.forEach((s, i) => {
    const item = document.createElement("div");
    item.className = "step-item";
    item.innerHTML = `<div class="step-num">${i + 1}</div><div class="step-body"><b>${escapeHtml(s.label)}</b><span>${escapeHtml(s.sub)}</span></div>`;
    flow.appendChild(item);
  });
}

document.getElementById("beginMissionBtn").addEventListener("click", () => {
  renderEditor();
  goTo("editor");
});

/* ================= EDITOR ================= */
function renderEditor() {
  const m = currentMission();
  const level = currentCampaign.levels[curLevelIndex];

  document.getElementById("edCrumb").innerHTML = `<b>Level ${curLevelIndex + 1}</b> · Mission ${curMissionIndex + 1} of ${level.missions.length} · Editor`;
  document.getElementById("rewardXp").textContent = m.reward;
  document.getElementById("diffVal").textContent = m.diff;
  document.getElementById("estTime").textContent = m.est;
  document.getElementById("fname").textContent = m.file;
  document.getElementById("mTitle").textContent = m.title;
  document.getElementById("mDesc").textContent = m.desc;

  renderAssist(m);
  renderFileTree(m);
  renderMiniTracker(m);
  renderSlotForm(m);
  renderCheckExisting(m);
}

function renderFileTree(mission) {
  // Simple heuristic: mission's own file is "active/yours", everything else
  // referenced in its code template that isn't the mission file is "given".
  const el = document.getElementById("fileTree");
  const otherFiles = currentCampaignKey === "retriever-agent"
    ? ["requirements.txt", "chroma_setup.py"]
    : ["requirements.txt", "mcp_server.py"];
  el.innerHTML = "";
  otherFiles.forEach(name => {
    el.innerHTML += `<div class="file unlocked-plain"><span class="file-icon">✓</span>${name}<span class="file-tag given">given</span></div>`;
  });
  el.innerHTML += `<div class="file active"><span class="file-icon">●</span>${mission.file}<span class="file-tag yours">yours</span></div>`;
}

function renderMiniTracker(mission) {
  const tracker = document.getElementById("miniTracker");
  tracker.innerHTML = "";
  mission.slots.forEach((s, i) => {
    const p = document.createElement("div");
    p.className = "mt-pill";
    p.id = "mt-" + i;
    p.textContent = `${i + 1}. ${s.label}`;
    tracker.appendChild(p);
  });
}

function renderSlotForm(mission) {
  const form = document.getElementById("slotForm");
  form.innerHTML = "";
  const savedValues = (currentProgress.slot_values && currentProgress.slot_values[mission.key]) || {};

  mission.slots.forEach(slot => {
    const row = document.createElement("div");
    row.className = "slot-row";
    row.id = "slotrow-" + slot.key;

    let inputEl;
    if (slot.type === "select") {
      inputEl = `<select data-slot="${slot.key}">
          <option value="">choose…</option>
          ${slot.options.map(o => `<option value="${o}" ${savedValues[slot.key] === o ? "selected" : ""}>${o}</option>`).join("")}
        </select>`;
    } else {
      inputEl = `<input type="${slot.type === 'number' ? 'number' : 'text'}" step="0.1" data-slot="${slot.key}" placeholder="${slot.placeholder || ''}" value="${savedValues[slot.key] ?? ''}">`;
    }
    row.innerHTML = `<label>${slot.label}</label>${inputEl}`;
    if (savedValues[slot.key]) row.classList.add("filled");
    form.appendChild(row);
  });

  form.querySelectorAll("[data-slot]").forEach(input => {
    input.addEventListener("change", onSlotChange);
    input.addEventListener("blur", onSlotChange);
  });
}

async function onSlotChange(e) {
  const slotKey = e.target.dataset.slot;
  const value = e.target.value;
  const mission = currentMission();

  const result = await api(`/campaigns/${currentCampaignKey}/slots`, "POST", {
    mission_key: mission.key,
    slot_key: slotKey,
    value: value,
  });

  // Refresh local progress snapshot's slot_values so re-renders (e.g. next mission) see it
  currentProgress.slot_values = currentProgress.slot_values || {};
  currentProgress.slot_values[mission.key] = currentProgress.slot_values[mission.key] || {};
  currentProgress.slot_values[mission.key][slotKey] = value;

  document.getElementById("slotrow-" + slotKey).classList.toggle("filled", value.length > 0);
  renderCodeArea(result.code_preview);
  updateChecklistFromResult(mission, result);
}

function renderCodeArea(code) {
  const el = document.getElementById("codeArea");
  const lines = code.split("\n");
  el.innerHTML = lines.map((line, i) => {
    const isTodo = line.includes("<TODO:");
    return `<div style="${isTodo ? 'color:var(--text-mute)' : ''}">${escapeHtml(line) || "&nbsp;"}</div>`;
  }).join("");
}

function updateChecklistFromResult(mission, result) {
  checklistState = result.checklist;
  renderChecklist(mission, result.checklist_labels);

  checklistState.forEach((done, i) => {
    const pill = document.getElementById("mt-" + i);
    if (!pill) return;
    pill.classList.toggle("done", done);
    pill.classList.toggle("active", !done && checklistState.slice(0, i).every(Boolean));
  });

  const btn = document.getElementById("continueBtn");
  btn.disabled = !result.ready_to_complete;
  btn.classList.toggle("ready", result.ready_to_complete);
  const level = currentCampaign.levels[curLevelIndex];
  const isLastMission = curMissionIndex === level.missions.length - 1;
  btn.textContent = isLastMission ? "Complete level →" : "Continue →";
}

function renderChecklist(mission, labels) {
  const el = document.getElementById("checklist");
  el.innerHTML = "";
  labels.forEach((label, i) => {
    const done = checklistState[i];
    const row = document.createElement("div");
    row.className = "check-item";
    row.innerHTML = `<span class="box ${done ? 'checked' : ''}">${done ? '✓' : ''}</span>${escapeHtml(label)}`;
    el.appendChild(row);
  });
  const doneCount = checklistState.filter(Boolean).length;
  document.getElementById("progNote").textContent = `${doneCount} / ${labels.length} complete`;
}

function renderCheckExisting(mission) {
  // Render code preview + checklist state on initial load, using whatever
  // was already saved for this mission (e.g. if the user navigates back).
  const savedValues = (currentProgress.slot_values && currentProgress.slot_values[mission.key]) || {};
  const allSaved = {};
  Object.values(currentProgress.slot_values || {}).forEach(v => Object.assign(allSaved, v));

  // We don't have a direct "preview without submitting" endpoint, so just
  // show a best-effort local render using the mission's own template.
  // (A real preview always comes from the server after a change; this is
  // just so the screen isn't blank before the first edit.)
  checklistState = mission.slots.map(s => !!savedValues[s.key]);
  renderChecklist(mission, mission.slots.map(s => s.label));

  const btn = document.getElementById("continueBtn");
  const ready = checklistState.every(Boolean) && checklistState.length > 0;
  btn.disabled = !ready;
  btn.classList.toggle("ready", ready);
  const level = currentCampaign.levels[curLevelIndex];
  const isLastMission = curMissionIndex === level.missions.length - 1;
  btn.textContent = isLastMission ? "Complete level →" : "Continue →";

  document.getElementById("codeArea").innerHTML =
    `<div style="color:var(--text-mute)">Fill in a field on the left to see this file update live.</div>`;
}

function renderAssist(mission) {
  activeAssistTab = "tradeoffs";
  document.querySelectorAll(".assist-tab").forEach(t => t.classList.toggle("on", t.dataset.tab === "tradeoffs"));
  document.getElementById("assistBody").textContent = mission.assist.tradeoffs || "";
}

document.querySelectorAll(".assist-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    activeAssistTab = tab.dataset.tab;
    document.querySelectorAll(".assist-tab").forEach(t => t.classList.toggle("on", t === tab));
    const mission = currentMission();
    document.getElementById("assistBody").textContent = mission.assist[activeAssistTab] || "(nothing here yet)";
  });
});

document.getElementById("continueBtn").addEventListener("click", async () => {
  const mission = currentMission();
  const result = await api(`/campaigns/${currentCampaignKey}/missions/complete`, "POST", { mission_key: mission.key });

  xp = result.total_xp;
  document.getElementById("xpVal").textContent = xp;
  toast(`+${result.xp_awarded} XP · Mission complete`);

  const level = currentCampaign.levels[curLevelIndex];
  if (curMissionIndex < level.missions.length - 1) {
    curMissionIndex++;
    renderMiniSteps();
    goTo("ministeps");
  } else if (result.campaign_complete) {
    renderSummary(result.finalize_result);
    goTo("summary");
  } else {
    // more levels exist beyond this one (not used in current campaigns, but supported)
    curLevelIndex++;
    curMissionIndex = 0;
    renderLevelIntro();
    goTo("levelintro");
  }
});

/* ================= SUMMARY (real Lyzr agent) ================= */
let currentAgentDbId = null;

function renderSummary(finalizeResult) {
  document.getElementById("summaryHeadline").textContent = `${currentCampaign.title} — built.`;
  document.getElementById("summaryDesc").textContent = currentCampaign.description;
  document.getElementById("finalTime").textContent = document.getElementById("timerVal").textContent;
  document.getElementById("finalXp").textContent = xp;

  if (!finalizeResult) return;
  currentAgentDbId = finalizeResult.agent_db_id;
  document.getElementById("agentIdOut").textContent = finalizeResult.agent_id;
  document.getElementById("testMsgOut").textContent = finalizeResult.test_message;
  document.getElementById("testRespOut").textContent = finalizeResult.test_response;
  document.getElementById("agentMockNotice").style.display = finalizeResult.mock ? "block" : "none";
  document.getElementById("chatLog").innerHTML = "";
}

document.getElementById("chatSend").addEventListener("click", sendChatMessage);
document.getElementById("chatInput").addEventListener("keydown", e => { if (e.key === "Enter") sendChatMessage(); });

async function sendChatMessage() {
  const input = document.getElementById("chatInput");
  const msg = input.value.trim();
  if (!msg || !currentAgentDbId) return;
  input.value = "";

  const log = document.getElementById("chatLog");
  log.innerHTML += `<div class="chat-bubble user">${escapeHtml(msg)}</div>`;

  const result = await api(`/agents/${currentAgentDbId}/chat`, "POST", { message: msg });
  log.innerHTML += `<div class="chat-bubble agent">${escapeHtml(result.response)}${result.mock ? ' <i>(mock)</i>' : ''}</div>`;
  log.scrollTop = log.scrollHeight;
}

/* ================= MENTOR PANEL ================= */
function toggleMentor() {
  document.getElementById("mentorPanel").classList.toggle("open");
}

async function updateMentorContext(screen) {
  document.getElementById("mentorContext").textContent = "Currently: " + screenLabel(screen);
  const mission = ["ministeps", "editor"].includes(screen) ? currentMission() : null;
  try {
    const result = await api("/mentor", "POST", {
      campaign_key: currentCampaignKey,
      screen,
      mission_key: mission ? mission.key : null,
    });
    document.getElementById("mentorMsg").textContent = result.message;
  } catch (e) {
    document.getElementById("mentorMsg").textContent = "Mentor unavailable right now — keep going, you've got this.";
  }
}

document.getElementById("mentorSend").addEventListener("click", async () => {
  const input = document.getElementById("mentorInput");
  const msg = input.value.trim();
  if (!msg) return;
  input.value = "";
  const screenEl = document.querySelector(".screen.show");
  const screen = screenEl.id.replace("screen-", "");
  const mission = ["ministeps", "editor"].includes(screen) ? currentMission() : null;

  document.getElementById("mentorMsg").textContent = "…thinking…";
  const result = await api("/mentor", "POST", {
    campaign_key: currentCampaignKey,
    screen,
    mission_key: mission ? mission.key : null,
    user_message: msg,
  });
  document.getElementById("mentorMsg").textContent = result.message;
});

function screenLabel(screen) {
  const labels = {
    campaign: "Choose Campaign", setup: "Project Setup", levelintro: "Level Intro",
    ministeps: "Mission mini-steps", editor: "In mission — editing",
    levelcomplete: "Level complete", summary: "Campaign complete",
  };
  return labels[screen] || screen;
}

/* ================= UTIL ================= */
function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, m => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[m]));
}

/* ================= INIT ================= */
loadCampaigns();
updateMentorContext("campaign");

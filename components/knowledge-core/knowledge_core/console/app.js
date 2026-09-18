"use strict";

const SESSION_URL = "/v1/kc/console/session";
const NOTES_URL = "/v1/kc/console/notes";
const SEARCH_URL = "/v1/kc/console/search";
const STATUS_URL = "/v1/kc/console/status";
const SOURCES_URL = "/v1/kc/console/sources";
const DRAFT_KEY = "kc-console-draft-v1";
const UNCERTAIN_KEY = "kc-console-uncertain-v1";

let csrfToken = null;
let nextCursor = null;

const $ = (id) => document.getElementById(id);
const projectLabel = (project) => project === "inbox" ? "Inbox" : project;

function setStatus(element, message, kind = "") {
  element.textContent = message;
  element.className = "status" + (kind ? " " + kind : "");
}

async function jsonResponse(response) {
  const text = await response.text();
  if (!text) return null;
  try { return JSON.parse(text); } catch { return { detail: text }; }
}

function detailMessage(payload, fallback) {
  if (!payload) return fallback;
  if (typeof payload.detail === "string") return payload.detail;
  if (payload.detail && typeof payload.detail.message === "string") return payload.detail.message;
  if (Array.isArray(payload.detail)) return payload.detail.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return fallback;
}

function loadDraft() {
  try { return JSON.parse(localStorage.getItem(DRAFT_KEY) || "null"); } catch { return null; }
}

function saveDraft() {
  const draft = {
    content: $("content").value,
    title: $("title").value,
    project: $("project").value,
    category: $("category").value,
    source_description: $("sourceDescription").value,
    source_urls_text: $("sourceUrls").value,
    source_date: $("sourceDate").value,
  };
  localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
}

function applyDraft(draft) {
  if (!draft) return;
  for (const [id, key] of [
    ["content", "content"], ["title", "title"], ["category", "category"],
    ["sourceDescription", "source_description"], ["sourceUrls", "source_urls_text"],
    ["sourceDate", "source_date"]
  ]) {
    if (draft[key] != null) $(id).value = draft[key];
  }
  if (draft.project && [...$("project").options].some((x) => x.value === draft.project)) {
    $("project").value = draft.project;
  }
}

function clearDraft({ preserveStatus = false } = {}) {
  localStorage.removeItem(DRAFT_KEY);
  $("noteForm").reset();
  if ($("project").dataset.defaultProject) $("project").value = $("project").dataset.defaultProject;
  if (!preserveStatus) setStatus($("saveStatus"), "");
}

function uncertainItems() {
  try {
    const parsed = JSON.parse(localStorage.getItem(UNCERTAIN_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch { return []; }
}

function storeUncertain(items) {
  localStorage.setItem(UNCERTAIN_KEY, JSON.stringify(items));
  renderUncertain();
}

function addUncertain(item) {
  const items = uncertainItems().filter((x) => x.key !== item.key);
  items.push(item);
  storeUncertain(items);
}

function removeUncertain(key) {
  storeUncertain(uncertainItems().filter((x) => x.key !== key));
}

function formPayload() {
  const payload = {
    content: $("content").value,
    project: $("project").value || null,
    title: $("title").value.trim() ? $("title").value : null,
    category: $("category").value.trim() || null,
    source_description: $("sourceDescription").value.trim() ? $("sourceDescription").value : null,
    source_urls: $("sourceUrls").value.split(/\r?\n/).map((x) => x.trim()).filter(Boolean),
    source_date: $("sourceDate").value || null,
  };
  return payload;
}

function payloadLabel(payload) {
  const first = (payload.title || payload.content || "").split(/\r?\n/).find((x) => x.trim()) || "Untitled note";
  return first.trim().slice(0, 70);
}

function renderUncertain() {
  const items = uncertainItems();
  $("uncertainPanel").classList.toggle("hidden", items.length === 0);
  const list = $("uncertainList");
  list.replaceChildren();
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "uncertain-item";
    const label = document.createElement("span");
    label.textContent = payloadLabel(item.payload);
    const actions = document.createElement("div");
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "Retry exact";
    retry.addEventListener("click", () => performSave(item.payload, item.key, { retryFrozen: true }));
    const dismiss = document.createElement("button");
    dismiss.type = "button";
    dismiss.className = "secondary";
    dismiss.textContent = "Dismiss";
    dismiss.addEventListener("click", () => removeUncertain(item.key));
    actions.append(retry, dismiss);
    row.append(label, actions);
    list.append(row);
  }
}

async function loadSession() {
  const response = await fetch(SESSION_URL, { credentials: "same-origin" });
  if (!response.ok) return false;
  const session = await response.json();
  activateNotebook(session);
  return true;
}

function activateNotebook(session) {
  csrfToken = session.csrf_token;
  $("loginPanel").classList.add("hidden");
  $("notebook").classList.remove("hidden");
  $("logoutButton").classList.remove("hidden");

  const select = $("project");
  select.replaceChildren();
  for (const project of session.allowed_projects) {
    const option = document.createElement("option");
    option.value = project;
    option.textContent = projectLabel(project);
    select.append(option);
  }
  select.value = session.default_project;
  select.dataset.defaultProject = session.default_project;
  applyDraft(loadDraft());
  renderUncertain();
  loadRecent(true);
  loadStatus();
}

function deactivateNotebook() {
  csrfToken = null;
  $("notebook").classList.add("hidden");
  $("logoutButton").classList.add("hidden");
  $("loginPanel").classList.remove("hidden");
}

async function performSave(payload, key, options = {}) {
  $("saveButton").disabled = true;
  setStatus($("saveStatus"), options.retryFrozen ? "Retrying exact frozen submission…" : "Saving canonical note…");
  try {
    const response = await fetch(NOTES_URL, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": key,
        "X-KC-Console-CSRF": csrfToken,
      },
      body: JSON.stringify(payload),
    });
    const data = await jsonResponse(response);
    if (!response.ok) {
      if (response.status >= 500) {
        addUncertain({ key, payload, saved_at: new Date().toISOString() });
        setStatus($("saveStatus"), "KC returned an uncertain server failure. The exact submission was frozen for retry.", "error");
      } else {
        removeUncertain(key);
        setStatus($("saveStatus"), detailMessage(data, "Save was rejected."), "error");
      }
      if (response.status === 401) deactivateNotebook();
      return;
    }

    removeUncertain(key);
    const indexMessage = data.text_state === "indexed"
      ? "Search index ready."
      : `Canonical save succeeded; search state: ${data.text_state}.`;
    setStatus($("saveStatus"), "Saved. " + indexMessage, "success");

    const current = JSON.stringify(formPayload());
    if (!options.retryFrozen && current === JSON.stringify(payload)) {
      clearDraft({ preserveStatus: true });
    }
    await loadRecent(true);
    await loadStatus();
    await openNote(data.note.observation_id);
  } catch (error) {
    addUncertain({ key, payload, saved_at: new Date().toISOString() });
    setStatus($("saveStatus"), "Connection outcome is uncertain. The exact submission was frozen for retry.", "error");
  } finally {
    $("saveButton").disabled = false;
  }
}

async function loadRecent(reset) {
  if (reset) {
    nextCursor = null;
    $("recentList").replaceChildren();
  }
  const url = new URL(NOTES_URL, window.location.origin);
  url.searchParams.set("limit", "25");
  if (nextCursor) url.searchParams.set("cursor", nextCursor);
  const response = await fetch(url, { credentials: "same-origin" });
  if (!response.ok) {
    if (response.status === 401) deactivateNotebook();
    return;
  }
  const data = await response.json();
  nextCursor = data.next_cursor;
  for (const note of data.items) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "note-row";
    const title = document.createElement("strong");
    title.textContent = note.display_title;
    const meta = document.createElement("span");
    const project = note.projects.length ? note.projects.map(projectLabel).join(", ") : "project unknown";
    meta.textContent = `${note.category} · ${project} · ${new Date(note.captured_at).toLocaleString()}`;
    button.append(title, meta);
    button.addEventListener("click", () => openNote(note.observation_id));
    $("recentList").append(button);
  }
  $("moreButton").classList.toggle("hidden", !nextCursor);
}

async function loadStatus() {
  setStatus($("statusMessage"), "");
  try {
    const response = await fetch(STATUS_URL, { credentials: "same-origin" });
    const data = await jsonResponse(response);
    if (!response.ok) {
      $("canonicalStatus").textContent = "Unavailable";
      $("searchReadyStatus").textContent = "Unavailable";
      $("writeStatus").textContent = "Session authenticated; backend status unavailable";
      $("graphStatus").textContent = "Not required / unverified";
      setStatus($("statusMessage"), detailMessage(data, "Knowledge Core read status is unavailable."), "error");
      if (response.status === 401) deactivateNotebook();
      return;
    }

    $("canonicalStatus").textContent = "Revision " + data.canonical_revision;
    $("searchReadyStatus").textContent = data.search_state === "ready"
      ? "Ready · " + data.text_source_count + " indexed source" + (data.text_source_count === 1 ? "" : "s")
      : "No current text index";
    $("writeStatus").textContent = "Owner scoped · " + data.write_projects.map(projectLabel).join(", ");
    $("graphStatus").textContent = data.graph_label;
    setStatus($("statusMessage"), data.write_proof_note);
  } catch {
    $("canonicalStatus").textContent = "Unavailable";
    $("searchReadyStatus").textContent = "Unavailable";
    $("writeStatus").textContent = "Unavailable";
    $("graphStatus").textContent = "Not required / unverified";
    setStatus($("statusMessage"), "Knowledge Core status request failed.", "error");
  }
}

function searchEvidenceLabel(evidence) {
  if (evidence.source_kind === "local.user-note") return "Notebook note";
  if (evidence.source_kind) return evidence.source_kind;
  if (evidence.repository) return "Repository source";
  return "Knowledge source";
}

function appendEvidenceLine(parent, label, value) {
  if (value == null || value === "" || (Array.isArray(value) && value.length === 0)) return;
  const line = document.createElement("div");
  line.className = "evidence-line";
  const text = Array.isArray(value) ? value.join(", ") : String(value);
  line.textContent = label + ": " + text;
  parent.append(line);
}

function renderSearchHit(hit) {
  const card = document.createElement("article");
  card.className = "search-hit";
  const title = document.createElement("h3");
  title.textContent = hit.display_title;
  const meta = document.createElement("div");
  meta.className = "hit-meta";
  const sourceLabel = searchEvidenceLabel(hit.evidence);
  const captured = hit.evidence.captured_at ? " · captured " + new Date(hit.evidence.captured_at).toLocaleString() : "";
  meta.textContent = "#" + hit.rank + " · " + sourceLabel + captured;
  card.append(title, meta);
  if (hit.excerpt) {
    const excerpt = document.createElement("div");
    excerpt.className = "excerpt";
    excerpt.textContent = hit.excerpt;
    card.append(excerpt);
  }
  appendEvidenceLine(card, "Source ID", hit.evidence.source_id);
  appendEvidenceLine(card, "Projects", hit.evidence.projects.map(projectLabel));
  appendEvidenceLine(card, "Classification", hit.evidence.source_classification);
  appendEvidenceLine(card, "Repository", hit.evidence.repository);
  appendEvidenceLine(card, "Path", hit.evidence.source_path);
  appendEvidenceLine(card, "Version", hit.evidence.source_version);
  if (hit.evidence.source_line_start != null) {
    const lineEnd = hit.evidence.source_line_end == null ? hit.evidence.source_line_start : hit.evidence.source_line_end;
    appendEvidenceLine(card, "Source lines", hit.evidence.source_line_start + "-" + lineEnd);
  }
  appendEvidenceLine(card, "Lifecycle", hit.evidence.lifecycle_state);
  const actions = document.createElement("div");
  actions.className = "hit-actions";
  const open = document.createElement("button");
  open.type = "button";
  open.textContent = "Open original";
  if (hit.open_original_kind === "note" && hit.note_observation_id) {
    open.addEventListener("click", () => openNote(hit.note_observation_id));
  } else {
    open.addEventListener("click", () => openSource(hit));
  }
  actions.append(open);
  card.append(actions);
  return card;
}

async function runSearch() {
  const query = $("searchQuery").value.trim();
  if (!query) return;
  $("searchButton").disabled = true;
  $("searchResults").replaceChildren();
  setStatus($("searchStatus"), "Searching PostgreSQL lexical index…");
  try {
    const response = await fetch(SEARCH_URL, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit: 20 }),
    });
    const data = await jsonResponse(response);
    if (!response.ok) {
      setStatus($("searchStatus"), detailMessage(data, "Search is unavailable; your query was not completed."), "error");
      if (response.status === 401) deactivateNotebook();
      return;
    }
    if (data.result_state === "empty") {
      setStatus($("searchStatus"), "No matching notes or knowledge sources found.");
      return;
    }
    setStatus($("searchStatus"), data.results.length + " lexical match" + (data.results.length === 1 ? "" : "es") + ".");
    for (const hit of data.results) $("searchResults").append(renderSearchHit(hit));
  } catch {
    setStatus($("searchStatus"), "Search is unavailable; your query was not completed.", "error");
  } finally {
    $("searchButton").disabled = false;
  }
}

async function openSource(hit) {
  const response = await fetch(SOURCES_URL + "/" + encodeURIComponent(hit.version_id), { credentials: "same-origin" });
  const source = await jsonResponse(response);
  if (!response.ok) {
    setStatus($("searchStatus"), detailMessage(source, "The selected original is unavailable."), "error");
    return;
  }
  $("detailTitle").textContent = hit.display_title || "Original";
  $("detailMeta").textContent = "Exact current source · SHA-256 " + source.sha256;
  $("detailContent").textContent = source.content;
  const fields = $("detailFields");
  fields.replaceChildren();
  addMetadataField(fields, "Source kind", hit.evidence.source_kind);
  addMetadataField(fields, "Source ID", hit.evidence.source_id);
  addMetadataField(fields, "Projects", hit.evidence.projects.map(projectLabel));
  addMetadataField(fields, "Captured", hit.evidence.captured_at);
  addMetadataField(fields, "Source time", hit.evidence.source_event_time);
  addMetadataField(fields, "Repository", hit.evidence.repository);
  addMetadataField(fields, "Path", hit.evidence.source_path);
  addMetadataField(fields, "Source version", hit.evidence.source_version);
  addMetadataField(fields, "ResourceVersion", source.version_id);
  $("detailPanel").classList.remove("hidden");
  $("detailPanel").scrollIntoView({ behavior: "smooth", block: "start" });
}
function addMetadataField(dl, label, value) {
  if (value == null || value === "" || (Array.isArray(value) && value.length === 0)) return;
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = label;
  dd.textContent = Array.isArray(value) ? value.join("\n") : String(value);
  dl.append(dt, dd);
}

async function openNote(observationId) {
  const response = await fetch(`${NOTES_URL}/${encodeURIComponent(observationId)}`, { credentials: "same-origin" });
  if (!response.ok) return;
  const note = await response.json();
  $("detailTitle").textContent = note.display_title;
  $("detailMeta").textContent = `Captured ${new Date(note.captured_at).toLocaleString()} · SHA-256 ${note.sha256}`;
  $("detailContent").textContent = note.content;
  const fields = $("detailFields");
  fields.replaceChildren();
  addMetadataField(fields, "Observation ID", note.observation_id);
  addMetadataField(fields, "Submission ID", note.submission_id);
  addMetadataField(fields, "Source ID", note.source_id);
  addMetadataField(fields, "Projects", note.projects.map(projectLabel));
  addMetadataField(fields, "Category", note.category + (note.category_supplied ? "" : " (default/legacy)"));
  addMetadataField(fields, "Source date", note.source_date);
  addMetadataField(fields, "Source time", note.source_event_time);
  addMetadataField(fields, "Source description", note.source_description);
  addMetadataField(fields, "Source URLs", note.source_urls);
  addMetadataField(fields, "Search ready", note.search_ready ? "yes" : "no");
  addMetadataField(fields, "ResourceVersion", note.version_id);
  $("detailPanel").classList.remove("hidden");
  $("detailPanel").scrollIntoView({ behavior: "smooth", block: "start" });
}

$("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const key = $("ownerKey").value;
  setStatus($("loginStatus"), "Authenticating…");
  try {
    const response = await fetch(SESSION_URL, {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-KC-Console-Key": key },
    });
    $("ownerKey").value = "";
    const data = await jsonResponse(response);
    if (!response.ok) {
      setStatus($("loginStatus"), detailMessage(data, "Authentication failed."), "error");
      return;
    }
    setStatus($("loginStatus"), "");
    activateNotebook(data);
  } catch {
    setStatus($("loginStatus"), "KC console is unavailable.", "error");
  }
});

$("noteForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const payload = formPayload();
  const key = crypto.randomUUID();
  performSave(payload, key);
});

$("noteForm").addEventListener("input", saveDraft);
$("noteForm").addEventListener("change", saveDraft);
$("clearDraftButton").addEventListener("click", clearDraft);
$("refreshButton").addEventListener("click", () => loadRecent(true));
$("moreButton").addEventListener("click", () => loadRecent(false));
$("closeDetailButton").addEventListener("click", () => $("detailPanel").classList.add("hidden"));
$("statusRefreshButton").addEventListener("click", loadStatus);
$("searchForm").addEventListener("submit", (event) => {
  event.preventDefault();
  runSearch();
});

$("logoutButton").addEventListener("click", async () => {
  if (csrfToken) {
    await fetch(SESSION_URL, {
      method: "DELETE",
      credentials: "same-origin",
      headers: { "X-KC-Console-CSRF": csrfToken },
    });
  }
  deactivateNotebook();
});

loadSession().catch(() => deactivateNotebook());

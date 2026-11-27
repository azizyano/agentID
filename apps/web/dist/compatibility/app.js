"use strict";

const byId = (id) => document.getElementById(id);
const caseInput = byId("case-input");
const baselineInput = byId("baseline-input");
const caseTime = byId("case-time");
const baselineTime = byId("baseline-time");
const loadButton = byId("load-example");
const runButton = byId("run-report");
const download = byId("download");
const reportPanel = byId("report-panel");
const notice = byId("notice");
const MAX_FILE_BYTES = 16_384;
const LOCAL_WORKSPACE = location.pathname === "/";

const CHECKS = {
  developer_mode: "Developer Mode",
  simulation: "Simulation",
  wallet_fee: "Wallet-displayed fee",
  app_confirmation: "Separate App approval",
  calldata: "Exact calldata",
  chain_id: "Chain",
  sender: "Selected sender",
  target: "Target contract",
  native_value_wei: "Native value",
  wallet_surface: "Wallet surface",
  risk_review: "Wallet risk findings",
  observation_age: "Observation age",
  preview_expiry: "Preview expiry",
};
const REVIEW_CHECKS = ["developer_mode", "simulation", "wallet_fee", "app_confirmation", "calldata"];
const STAGES = {
  wallet_selected: "Wallet selected",
  preview_passed: "Preview passed",
  preview_blocked: "Preview blocked",
  unknown: "Stage unknown",
};
const SURFACES = {
  binance_ai_pro: "Binance AI Pro",
  binance_dapp_browser: "Binance dApp browser",
  binance_agentic_cli: "Binance Agentic CLI",
};
const BADGES = {
  PREVIEW_MATCHED: ["Preview matched", "good"],
  INCOMPATIBLE: ["Incompatible", "bad"],
  INCONCLUSIVE: ["Inconclusive", "warn"],
  BLOCKED_BY_WALLET: ["Wallet blocked", "bad"],
  MATCH: ["Matched", "good"],
  MISMATCH: ["Unmet", "bad"],
  UNKNOWN: ["Unknown", "neutral"],
  ENABLED: ["Enabled", "good"],
  DISABLED: ["Disabled", "warn"],
  PASSED: ["Passed", "good"],
  CLEAR: ["None reported", "good"],
  WARNING: ["Warning", "warn"],
  EXPIRED: ["Expired", "warn"],
  FRESH: ["Fresh", "good"],
  STALE: ["Stale", "warn"],
  FUTURE: ["Future timestamp", "warn"],
  NOT_REQUIRED: ["Optional", "neutral"],
};

let busy = false;
let currentMarkdown = "";
let reportFilename = "";

function node(tag, className, value) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (value !== undefined) element.textContent = value;
  return element;
}

function badge(status) {
  const [label, tone] = BADGES[status] || BADGES.UNKNOWN;
  const item = node("span", "badge", label);
  item.dataset.tone = tone;
  return item;
}

function attemptCard(label, report) {
  const card = node("div", "attempt");
  const stopped = report.reported_stage === "wallet_selected" && report.checks.developer_mode === "DISABLED";
  card.append(
    node("span", "", label),
    node("strong", "", stopped ? "Stopped before preview" : STAGES[report.reported_stage]),
    badge(report.status),
  );
  return card;
}

function tableRow(label, values, isStatus) {
  const row = node("tr");
  const heading = node("th", "", label);
  heading.scope = "row";
  row.append(heading);
  for (const value of values) {
    const cell = node("td");
    cell.append(isStatus ? badge(value) : document.createTextNode(value));
    row.append(cell);
  }
  return row;
}

function utcTime(value) {
  if (value === null || value === undefined) return "Unknown";
  return new Date(value * 1000).toISOString().slice(0, 19).replace("T", " ") + " UTC";
}

function render(report, source) {
  const { action, before, after } = report;
  const attempts = before ? [before, after] : [after];
  const scope = byId("scope");
  scope.replaceChildren(
    node("span", "", `BNB Smart Chain (${action.chain_id})`),
    node("span", "", SURFACES[action.wallet_surface]),
    node("span", "", `${action.native_value_wei} wei`),
  );
  if (action.function_selector) {
    const selector = node("span", "", "Selector ");
    selector.append(node("code", "", action.function_selector));
    scope.append(selector);
  }
  byId("report-title").textContent = before ? "Attempt comparison" : "Attempt assessment";
  const evidence = after.evidence === "FIXTURE" ? "Synthetic fixture" : "Tester reported";
  byId("report-source").textContent = `${source} · ${evidence}`;
  byId("contract-target").textContent = action.target;
  byId("attempts").replaceChildren(...(before
    ? [attemptCard("Before", before), attemptCard("After", after)]
    : [attemptCard("Latest attempt", after)]));

  byId("before-head").hidden = byId("before-detail").hidden = before === null;
  byId("after-head").textContent = byId("after-detail").textContent = before ? "After" : "Result";
  const primary = byId("primary-checks");
  const other = byId("other-checks");
  primary.replaceChildren();
  other.replaceChildren();
  for (const [key, label] of Object.entries(CHECKS)) {
    if (!attempts.some((item) => Object.hasOwn(item.checks, key))) continue;
    const table = REVIEW_CHECKS.includes(key) ? primary : other;
    table.append(tableRow(label, attempts.map((item) => item.checks[key]), true));
  }
  other.append(
    tableRow("Observed at", attempts.map((item) => utcTime(item.observed_at)), false),
    tableRow("Evaluated at", attempts.map((item) => utcTime(item.evaluated_at)), false),
  );
  const notes = [];
  if (after.checks.wallet_fee === "MISMATCH") notes.push("The latest preview showed no fee. The amount is unknown.");
  if (after.checks.app_confirmation === "MISMATCH") notes.push("The latest preview reported requireConfirmation: false.");
  byId("report-note").textContent = notes.join(" ");
  const comparisonNotes = [];
  if (report.expected_input_checks?.calldata === "UNKNOWN") comparisonNotes.push("The exact expected calldata across the two attempts is unknown.");
  if (report.observation_order === "SUPPLIED") comparisonNotes.push("The reports are shown in the supplied order.");
  byId("comparison-note").textContent = comparisonNotes.join(" ");

  currentMarkdown = report.markdown;
  reportFilename = before ? "veriabstain-before-after.md" : "veriabstain-assessment.md";
  download.disabled = false;
  byId("empty-state").hidden = true;
  byId("report-content").hidden = false;
}

function syncInputs() {
  const hasBaseline = Boolean(baselineInput.files.length);
  byId("case-name").textContent = caseInput.files[0]?.name || "No file selected";
  byId("baseline-name").textContent = baselineInput.files[0]?.name || "No file selected";
  byId("clear-baseline").hidden = !hasBaseline;
  baselineTime.disabled = !hasBaseline || busy;
  loadButton.disabled = busy;
  runButton.disabled = busy || !caseInput.files.length;
}

function utcSeconds(input) {
  if (!input.value) return null;
  const seconds = Date.parse(input.value + "Z") / 1000;
  if (!Number.isSafeInteger(seconds) || seconds < 0) throw new Error("Enter a valid UTC evaluation time.");
  return seconds;
}

function message(text, tone = "neutral") {
  notice.textContent = text;
  notice.dataset.tone = tone;
}

async function run(load, source) {
  if (busy) return;
  busy = true;
  currentMarkdown = "";
  download.disabled = true;
  reportPanel.setAttribute("aria-busy", "true");
  syncInputs();
  message("Reading saved evidence…");
  try {
    render(await load(), source);
    message(source === "Saved owner example" ? "Saved example loaded." : "Assessment ready.");
  } catch (error) {
    byId("report-content").hidden = true;
    byId("empty-state").textContent = "Choose valid case files or load the saved example.";
    byId("empty-state").hidden = false;
    byId("report-title").textContent = "Wallet assessment";
    byId("report-source").textContent = "";
    message(error.message, "error");
  } finally {
    busy = false;
    reportPanel.setAttribute("aria-busy", "false");
    syncInputs();
  }
}

async function requestReport(path, options) {
  let response;
  try {
    response = await fetch(path, { ...options, cache: "no-store" });
  } catch {
    throw new Error("The local checker is unavailable. Check that the workspace server is running.");
  }
  if (!response.ok) {
    throw new Error(options
      ? "The checker could not read these cases. Check the JSON, evaluation times, and expected action."
      : "The saved example could not be loaded.");
  }
  return response.json();
}

function loadExample() {
  const path = LOCAL_WORKSPACE ? "/api/example" : "/compatibility/example.json";
  return run(() => requestReport(path), "Saved owner example");
}

function runImported(event) {
  event.preventDefault();
  const caseFile = caseInput.files[0];
  const baseline = baselineInput.files[0];
  if (!caseFile) return;
  return run(async () => {
    if (caseFile.size > MAX_FILE_BYTES || baseline?.size > MAX_FILE_BYTES) {
      throw new Error("Choose case files no larger than 16 KB each.");
    }
    const now = utcSeconds(caseTime);
    const baselineNow = baseline ? utcSeconds(baselineTime) : null;
    const payload = {
      case: await caseFile.text(),
      baseline: baseline ? await baseline.text() : null,
      now,
      baseline_now: baselineNow,
    };
    return requestReport("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }, "Imported evidence");
}

function downloadReport() {
  if (!currentMarkdown) return;
  const href = URL.createObjectURL(new Blob([currentMarkdown + "\n"], { type: "text/markdown;charset=utf-8" }));
  const link = node("a");
  link.href = href;
  link.download = reportFilename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}

if (LOCAL_WORKSPACE) {
  caseInput.addEventListener("change", syncInputs);
  baselineInput.addEventListener("change", syncInputs);
  byId("clear-baseline").addEventListener("click", () => {
    baselineInput.value = "";
    baselineTime.value = "";
    syncInputs();
    baselineInput.focus();
  });
  byId("evidence-form").addEventListener("submit", runImported);
  loadButton.addEventListener("click", loadExample);
}
download.addEventListener("click", downloadReport);
syncInputs();
byId("mode-label").textContent = LOCAL_WORKSPACE ? "Local workspace" : "Compatibility demo";
byId("local-panel").hidden = !LOCAL_WORKSPACE;
byId("demo-panel").hidden = LOCAL_WORKSPACE;
loadExample();

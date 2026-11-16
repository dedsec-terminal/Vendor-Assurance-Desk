(() => {
  "use strict";

  const state = {
    data: null,
    view: "overview",
    evidenceStage: "baseline",
    findingsStage: "baseline",
    controlStage: "baseline",
    controlQuery: "",
    selectedEvidence: null,
    presentation: false,
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const safe = (value, fallback = "Not recorded") => {
    if (value === null || value === undefined || value === "") return fallback;
    if (Array.isArray(value)) return value.length ? value.join(", ") : fallback;
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  };
  const text = (selector, value, fallback) => {
    const node = $(selector);
    if (node) node.textContent = safe(value, fallback);
  };
  const add = (parent, tag, className, value) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined && value !== null) node.textContent = safe(value);
    parent.append(node);
    return node;
  };
  const resultText = result => ({
    gap: "Gap identified",
    pass: "Selected checks passed",
    unknown: "Needs human review",
  }[result] || "Not assessed");
  const resultClass = result => ({ gap: "open", pass: "pass", unknown: "unknown" }[result] || "unknown");
  const asDate = value => {
    if (!value) return "Not recorded";
    const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return safe(value);
    return new Intl.DateTimeFormat("en", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" })
      .format(new Date(`${match[1]}-${match[2]}-${match[3]}T00:00:00Z`));
  };
  const metricPair = pair => {
    if (typeof pair === "number") return `${pair}`;
    if (pair && typeof pair === "object" && pair.actual !== undefined) {
      return pair.expected === undefined ? `${pair.actual}` : `${pair.actual}/${pair.expected}`;
    }
    return "Not measured";
  };
  const metricActual = pair => typeof pair === "number" ? pair : pair && pair.actual !== undefined ? pair.actual : null;
  const allChecks = stage => state.data?.checks?.[stage] || [];
  const findings = () => state.data?.findings || [];
  const evidence = () => state.data?.evidence || [];
  const getEvidence = id => evidence().find(item => item.evidence_id === id);
  const getCheck = (id, stage) => allChecks(stage).find(item => item.evidence_id === id);
  const titleFor = item => item?.title || item?.label || item?.evidence_type || item?.evidence_id || "Evidence record";
  const firstEvidenceFor = finding => getEvidence(finding.evidence_id);

  function setLoadStatus(message, mode = "ready") {
    const node = $("#load-status");
    if (!node) return;
    node.replaceChildren();
    const dot = document.createElement("i");
    dot.className = "saved-dot";
    dot.setAttribute("aria-hidden", "true");
    if (mode === "error") dot.classList.add("error");
    if (mode === "loading") dot.classList.add("loading");
    node.append(dot, document.createTextNode(message));
  }

  function showError(message) {
    setLoadStatus("Assessment unavailable", "error");
    for (const selector of ["#priority-list", "#evidence-list", "#finding-board", "#results-grid"]) {
      const parent = $(selector);
      if (!parent) continue;
      parent.replaceChildren();
      const box = add(parent, "div", "empty-state error-state");
      box.append(document.createTextNode(message));
      const button = add(box, "button", "", "Retry");
      button.type = "button";
      button.addEventListener("click", loadAssessment, { once: true });
    }
  }

  function showView(name) {
    if (!["overview", "evidence", "controls", "findings", "decision", "results"].includes(name)) return;
    state.view = name;
    $$(".view").forEach(section => {
      const active = section.id === `view-${name}`;
      section.hidden = !active;
      section.classList.toggle("active", active);
    });
    $$(".nav-item").forEach(button => {
      const active = button.dataset.view === name;
      button.classList.toggle("active", active);
      if (active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    const title = $(`#view-${name} h1`);
    if (title) title.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function renderOverview() {
    const data = state.data;
    const vendor = data.vendor || {};
    text("#sidebar-vendor", vendor.name);
    text("#sidebar-case", data.case_id);
    text("#breadcrumb-vendor", vendor.name);
    text("#page-title-overview", vendor.name);
    text("#case-date", asDate(data.assessment_date));
    text("#overview-subtitle", `${safe(vendor.service)} · ${safe(data.criticality?.tier, "Criticality pending")} proposed criticality`);
    text("#metric-owner", safe(vendor.business_owner, "Owner not assigned").replace(/\s*\(fictional role\)/i, ""));
    text("#overview-decision", data.recommendation?.status);
    text("#decision-status", data.recommendation?.status);
    text("#overview-rationale", data.recommendation?.rationale);
    text("#decision-rationale", data.recommendation?.rationale);
    text("#decision-owner", vendor.business_owner);
    text("#platform-name", data.platform?.name, "Platform not connected");
    text("#platform-status", data.platform?.status, "Not configured");
    text("#overview-scope", `Assessment scope · ${safe(vendor.service)} · ${safe(vendor.data_categories, "Data categories not recorded")}`);
    text("#lifecycle-intake", `${safe(vendor.service)} · ${safe(data.criticality?.tier, "Tier pending")} proposed tier`);
    const approval = safe(data.recommendation?.human_approval, "Pending");
    text("#overview-approval", approval === "Pending" ? "Human decision pending" : approval);
    text("#decision-review-state", approval === "Pending" ? "Awaiting authorized reviewer" : approval);
    text("#reviewer-state", approval === "Pending" ? "No reviewer decision recorded" : approval);
    text("#decision-status-pill", approval === "Pending" ? "Pending approval" : approval);

    const counts = data.metrics || {};
    const baselineGaps = allChecks("baseline").filter(check => check.result === "gap");
    const retestGaps = allChecks("retest").filter(check => check.result === "gap");
    const unresolved = retestGaps.length;
    const baselineGapCount = allChecks("baseline").length
      ? baselineGaps.length
      : metricActual(counts.seeded_gaps_detected);
    text("#metric-open-gaps", baselineGapCount);
    text("#metric-gap-sub", `${unresolved} remains unresolved`);
    text("#metric-evidence", evidence().length);
    const passed = metricPair(counts.retest_checks_passed);
    text("#metric-retest", passed.includes("/") ? `${passed.split("/")[0]}${"/"}${passed.split("/")[1]}` : passed);
    text("#evidence-count", evidence().length);
    text("#findings-count", findings().length);
    const retestReady = findings().filter(item => item.status === "Ready for review").length;
    const controlCount = state.data.control_review?.catalog?.controls?.length;
    text("#controls-count", controlCount ?? "—");
    const lifecycleRetest = $$(".lifecycle-step")[2];
    if (lifecycleRetest) {
      const stateLabel = $(".step-state", lifecycleRetest);
      if (stateLabel) stateLabel.textContent = retestReady ? `${retestReady} ready for review` : "Review needed";
    }
    renderPriorities();
  }

  function renderPriorities() {
    const list = $("#priority-list");
    if (!list) return;
    list.replaceChildren();
    const items = findings();
    if (!items.length) {
      add(list, "div", "empty-state", "No findings are present in the assessment data.");
      return;
    }
    items.slice(0, 4).forEach((finding, index) => {
      const row = add(list, "article", "priority-item");
      add(row, "span", "priority-index", String(index + 1).padStart(2, "0"));
      add(row, "strong", "priority-title", finding.title);
      add(row, "span", "priority-detail", finding.baseline_reason || finding.required_action);
      add(row, "span", "priority-owner", finding.owner);
    });
  }

  function evidenceStatus(item, stage) {
    const check = getCheck(item.evidence_id, stage);
    if (check) return check.result;
    return "unknown";
  }

  function renderEvidence() {
    const list = $("#evidence-list");
    if (!list) return;
    list.replaceChildren();
    const stage = state.evidenceStage;
    const records = evidence().filter(item => stage === "retest" || !item.supersedes);
    text("#evidence-stage-title", stage === "baseline" ? "Initial evidence set" : "Retest evidence set");
    text("#evidence-stage-note", `${records.length} records · ${stage === "baseline" ? "Initial assessment" : "Revised evidence with unresolved gaps retained"}`);
    $$("[data-stage]").forEach(button => {
      const active = button.dataset.stage === stage;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    if (!records.length) {
      add(list, "div", "empty-state", "No evidence records were supplied.");
      return;
    }
    records.forEach(item => {
      const button = add(list, "button", `evidence-card${state.selectedEvidence === item.evidence_id ? " selected" : ""}`);
      button.type = "button";
      button.setAttribute("aria-pressed", String(state.selectedEvidence === item.evidence_id));
      const icon = add(button, "span", "evidence-card-icon", "▤");
      icon.setAttribute("aria-hidden", "true");
      const copy = add(button, "span", "evidence-card-copy");
      add(copy, "strong", "", titleFor(item));
      add(copy, "small", "", `${item.evidence_id} · ${item.content_notice?.startsWith("Synthetic") || item.content_notice?.startsWith("SYNTHETIC") ? "Synthetic record" : "Fictional training record"}`);
      const status = evidenceStatus(item, stage);
      const statusNode = add(button, "span", `evidence-status ${resultClass(status)}`, resultText(status));
      button.addEventListener("click", () => {
        state.selectedEvidence = item.evidence_id;
        renderEvidence();
        renderEvidenceDetail(item);
      });
      if (state.selectedEvidence === item.evidence_id) renderEvidenceDetail(item);
    });
    if (!state.selectedEvidence || !records.some(item => item.evidence_id === state.selectedEvidence)) {
      state.selectedEvidence = records[0].evidence_id;
      renderEvidence();
      renderEvidenceDetail(records[0]);
    }
  }

  function renderEvidenceDetail(item) {
    const panel = $("#evidence-detail");
    if (!panel || !item) return;
    panel.replaceChildren();
    const header = add(panel, "div", "detail-header");
    add(header, "div", "eyebrow", `${item.evidence_id} · VERSION ${item.version ?? 1}`);
    add(header, "h2", "", titleFor(item));
    add(header, "p", "", item.evidence_type);
    const fields = add(panel, "div", "detail-fields");
    const entries = [
      ["Provided by", item.provided_by],
      ["Verification", item.verified === true ? "Verified by reviewer" : "Not independently verified"],
      ["Service scope", item.system_scope || item.service_scope || "Not stated"],
      ["Report period", item.report_period_start && item.report_period_end ? `${asDate(item.report_period_start)} – ${asDate(item.report_period_end)}` : null],
      ["Expiry date", item.expiry_date ? asDate(item.expiry_date) : null],
      ["Responsibility", item.responsibility_type],
      ["Control state", item.mock_state],
      ["Policy owner", item.policy_owner],
      ["Service in scope", item.scope_match === true ? "Yes, for selected fixture checks" : item.scope_match === false ? "No" : null],
      ["Evidence fingerprint", getCheck(item.evidence_id, state.evidenceStage)?.evidence_sha256],
    ].filter(([_, value]) => value !== undefined && value !== null && value !== "");
    entries.forEach(([label, value]) => {
      const field = add(fields, "div", "detail-field");
      add(field, "span", "", label);
      add(field, "strong", "", value);
    });
    const note = add(panel, "div", "detail-note");
    add(note, "strong", "", "Review note");
    add(note, "span", "", item.review_note || item.content_notice || "No review note supplied.");
    add(panel, "p", "stage-note", "The selected check covers only the facts stated in this record. Human review is required.");
  }

  function findingStatus(finding, stage) {
    if (stage === "baseline") return "Open";
    return finding.status === "Ready for review" ? "Ready for review" : "Open";
  }

  function renderFindings() {
    const board = $("#finding-board");
    if (!board) return;
    board.replaceChildren();
    const stage = state.findingsStage;
    $$("[data-findings-stage]").forEach(button => {
      const active = button.dataset.findingsStage === stage;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    const items = findings();
    const ready = stage === "retest" ? items.filter(item => findingStatus(item, stage) === "Ready for review").length : 0;
    text("#finding-count-label", stage === "baseline" ? `${items.length} findings` : `${ready} ready for review · ${items.length - ready} remain open`);
    const desc = $("#finding-count-label")?.nextElementSibling;
    if (desc) desc.textContent = stage === "baseline" ? "Initial evidence review" : "Evidence retest · reviewer decision pending";
    if (!items.length) {
      add(board, "div", "empty-state", "No findings are present in the assessment data.");
      return;
    }
    items.forEach((finding, index) => {
      const row = add(board, "article", "finding-row");
      add(row, "span", "finding-num", String(index + 1).padStart(2, "0"));
      const main = add(row, "div", "finding-main");
      add(main, "strong", "", finding.title);
      const evidenceCheck = allChecks(stage).find(check => check.evidence_id === (stage === "retest" ? finding.retest_evidence_id : finding.evidence_id));
      const fingerprint = evidenceCheck?.evidence_sha256;
      add(main, "small", "", `${finding.id}${finding.evidence_id ? ` · ${finding.evidence_id}` : ""}${fingerprint ? ` · SHA-256 ${fingerprint.slice(0, 12)}` : ""}`);
      const status = findingStatus(finding, stage);
      add(main, "span", `finding-status ${status === "Ready for review" ? "ready" : "open"}`, status === "Ready for review" ? "Ready for review · not closed" : "Open · reviewer decision required");
      const reasoning = add(row, "div", "finding-reason");
      add(reasoning, "p", "", stage === "baseline" ? finding.baseline_reason : finding.retest_reason || finding.baseline_reason);
      if (finding.required_action) add(reasoning, "small", "finding-action", `Next action: ${finding.required_action}`);
      const owner = add(row, "div", "finding-owner");
      add(owner, "span", "", "Owner");
      add(owner, "strong", "", finding.owner);
      add(row, "div", "finding-due", finding.due_date ? `Due ${asDate(finding.due_date)}` : "Due date not set");
    });
  }

  function renderDecision() {
    const items = findings();
    const list = $("#condition-list");
    if (!list) return;
    list.replaceChildren();
    if (!items.length) {
      add(list, "div", "empty-state", "No decision conditions were supplied.");
      return;
    }
    items.forEach((finding, index) => {
      const item = add(list, "article", "condition-item");
      add(item, "span", "condition-index", String(index + 1).padStart(2, "0"));
      const body = add(item, "div", "");
      add(body, "strong", "", finding.title);
      add(body, "p", "", finding.required_action);
      add(item, "span", "condition-owner", finding.owner);
    });
    const conditions = state.data.recommendation?.conditions;
    const rationaleNode = $("#decision-rationale");
    if (Array.isArray(conditions) && conditions.length && rationaleNode) {
      rationaleNode.textContent = state.data.recommendation.rationale || "Conditions are listed below for human review.";
    }
  }

  function renderResults() {
    const data = state.data;
    const metrics = data.metrics || {};
    const grid = $("#results-grid");
    grid.replaceChildren();
    const resultItems = [
      ["Seeded gaps identified", metricPair(metrics.seeded_gaps_detected), "Expected findings independently compared with evidence checks."],
      ["Findings on clean policy fixture", safe(metrics.clean_fixture_findings, "Not measured"), "Only stated policy presence, approval and service-scope checks."],
      ["Owner and due date coverage", metricPair(metrics.owner_due_date_coverage), "Open findings with an assigned role and follow-up date."],
      ["Retest checks ready", metricPair(metrics.retest_checks_passed), "Updated synthetic evidence reviewed against its seeded checks."],
      ["Reviewer closures", safe(metrics.reviewer_closures, "Not recorded"), "Closed findings with a human review record."],
      ["Unresolved evidence gap preserved", metrics.unresolved_evidence_gap_preserved === true ? "Yes" : metrics.unresolved_evidence_gap_preserved === false ? "No" : "Not measured", "Expired assurance evidence remains an open review item."],
    ];
    resultItems.forEach(([label, value, note]) => {
      const card = add(grid, "article", "result-card");
      add(card, "span", "", label);
      add(card, "div", "result-value", value);
      add(card, "p", "", note);
    });
    const baselineGaps = allChecks("baseline").filter(check => check.result === "gap");
    const cleanCheck = allChecks("baseline").find(check => check.evidence_id === "E04");
    text("#results-overview-title", `${baselineGaps.length} initial gaps · ${findings().filter(item => item.status === "Ready for review").length} findings ready for retest review`);
    text("#results-overview-note", `${safe(data.case_id)} · ${asDate(data.assessment_date)} · Reviewer closure count: ${safe(metrics.reviewer_closures, "not recorded")}.`);
    const oracle = $("#oracle-list");
    oracle.replaceChildren();
    const oracleRows = baselineGaps.map(check => [check.check_id, check.reason, "Gap expected"]);
    if (cleanCheck) oracleRows.push(["E04 clean policy fixture", cleanCheck.reason, cleanCheck.result === "pass" ? "Pass" : "Review"]);
    const retestGaps = allChecks("retest").filter(check => check.result === "gap");
    retestGaps.forEach(check => oracleRows.push([check.check_id, check.reason, "Remains open"]));
    if (!oracleRows.length) add(oracle, "div", "empty-state", "No expected check results were supplied.");
    oracleRows.forEach(([title, reason, result]) => {
      const row = add(oracle, "div", "oracle-row");
      add(row, "strong", "", title);
      add(row, "p", "", reason);
      add(row, "span", `oracle-result${result === "Pass" ? " pass" : ""}`, result);
    });
    const history = $("#history-list");
    history.replaceChildren();
    const events = data.history || [];
    if (!events.length) {
      add(history, "div", "empty-state", "No reviewer actions are recorded yet. Evidence checks are generated from the synthetic case file.");
    } else {
      events.forEach(event => {
        const row = add(history, "div", "history-row");
        add(row, "i", `history-dot${event.stage === "retest" ? " review" : ""}`);
        add(row, "strong", "", event.event);
        add(row, "p", "", `${safe(event.actor, "System-generated check")} · ${safe(event.reason)}`);
        add(row, "time", "", safe(event.stage, "Assessment"));
      });
    }
  }

  function controlStatusLabel(status) {
    return ({
      "Evidence needed": "Evidence needed",
      Documented: "Documented",
      "Control gap": "Control gap",
      "Retest ready": "Retest ready",
    })[status] || "Review status pending";
  }

  function renderControlCoverage() {
    const container = $("#control-coverage-summary");
    const review = state.data?.control_review;
    if (!container) return;
    container.replaceChildren();
    if (!review?.coverage?.length) {
      add(container, "div", "empty-state", "No vendor control coverage assessment is attached yet.");
      return;
    }
    const summary = add(container, "div", "control-coverage-head");
    const title = add(summary, "div", "");
    add(title, "span", "eyebrow", "SCOPED COVERAGE REVIEW");
    add(title, "strong", "", `${review.coverage.length} vendor control questions reviewed`);
    add(title, "p", "", "Evidence and coverage statuses describe this fictional service scope only.");
    const stats = add(summary, "div", "coverage-stat-list");
    const order = ["Evidence needed", "Documented", "Control gap", "Retest ready"];
    order.forEach(status => {
      const count = review.coverage.filter(item => item.status === status).length;
      const stat = add(stats, "div", `coverage-stat coverage-${status.toLowerCase().replaceAll(" ", "-")}`);
      add(stat, "strong", "", count);
      add(stat, "span", "", status);
    });
    container.append(summary);
    const note = add(container, "p", "coverage-note");
    note.textContent = "These counts classify evidence follow up; they are not compliance scores, certification claims or framework coverage percentages.";
  }

  function renderControlTests() {
    const container = $("#control-test-list");
    const metricBox = $("#control-test-metrics");
    const review = state.data?.control_review;
    if (!container) return;
    container.replaceChildren();
    const items = review?.tests?.controls || [];
    if (metricBox) {
      metricBox.replaceChildren();
      const metrics = review?.tests?.metrics || {};
      const sampleMetrics = [
        ["Seeded test failures", metrics.seeded_failures_detected?.actual, metrics.seeded_failures_detected?.expected === undefined ? null : `of ${metrics.seeded_failures_detected.expected} expected`],
        ["Clean rows flagged", metrics.clean_rows_flagged],
        ["Exceptions remaining after retest", metrics.retest_exceptions_remaining],
        ["Synthetic rows tested", metrics.baseline_population_rows, metrics.retest_population_rows === undefined ? null : `retest ${metrics.retest_population_rows}`],
      ].filter(([, value]) => value !== undefined && value !== null);
      if (sampleMetrics.length) {
        const heading = add(metricBox, "p", "control-metrics-label", "Fixture-level measures · three selected ITGC tests");
        heading.id = "control-test-metric-scope";
        const list = add(metricBox, "div", "control-test-metric-list");
        sampleMetrics.forEach(([label, value, note]) => {
          const card = add(list, "article", "control-test-metric");
          add(card, "span", "", label);
          add(card, "strong", "", value);
          if (note) add(card, "small", "", note);
        });
      }
    }
    $$("[data-control-stage]").forEach(button => {
      const active = button.dataset.controlStage === state.controlStage;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    if (!items.length) {
      add(container, "div", "empty-state", "No sample ITGC test results are attached yet.");
      return;
    }
    const stage = state.controlStage;
    items.forEach((item, index) => {
      const row = add(container, "article", "control-test-card");
      const header = add(row, "div", "control-test-header");
      const identity = add(header, "div", "control-test-title");
      add(identity, "span", "control-id", item.id);
      add(identity, "h3", "", item.title);
      add(identity, "p", "", item.objective);
      const mapped = add(row, "div", "framework-mappings control-test-mappings");
      add(mapped, "span", "framework-label", "Related NIST CSF 2.0");
      (item.nist_csf || []).forEach(reference => add(mapped, "span", "framework-code", reference));
      add(mapped, "span", "framework-label iso-label", "ISO/IEC 27001:2022");
      (item.iso_27001 || []).forEach(reference => add(mapped, "span", "framework-code", reference));
      if (item.framework_note) add(row, "p", "control-test-reason", item.framework_note);
      const activeExceptions = stage === "baseline" ? item.baseline_exceptions : item.retest_exceptions;
      const status = Array.isArray(activeExceptions)
        ? activeExceptions.length ? "gap" : "pass"
        : "pending";
      add(header, "span", `control-result result-${status}`, stage === "baseline" ? `Initial · ${status === "gap" ? "Gap" : status === "pass" ? "Pass" : "Review"}` : `Retest · ${status === "gap" ? "Gap" : status === "pass" ? "Pass" : "Review"}`);
      const compare = add(row, "div", "test-counts");
      const baseline = add(compare, "span", "");
      add(baseline, "b", "", item.baseline_count ?? item.baseline_exceptions?.length ?? "—");
      baseline.append(document.createTextNode(" initial exceptions"));
      const arrow = add(compare, "span", "test-arrow", "→");
      arrow.setAttribute("aria-label", "to retest");
      const retest = add(compare, "span", "");
      add(retest, "b", "", item.retest_count ?? item.retest_exceptions?.length ?? "—");
      retest.append(document.createTextNode(" retest exceptions"));
      const selected = stage === "baseline" ? item.baseline_exceptions : item.retest_exceptions;
      const disclosure = add(row, "details", "exception-details");
      add(disclosure, "summary", "", `${selected?.length ?? 0} ${stage === "baseline" ? "initial" : "retest"} exception records`);
      const list = add(disclosure, "ul", "exception-list");
      if (Array.isArray(selected) && selected.length) {
        selected.forEach(exception => {
          let label;
          if (typeof exception === "string") label = exception;
          else if (exception && typeof exception === "object") {
            const reasons = Array.isArray(exception.reasons) ? exception.reasons.join("; ") : exception.reasons;
            label = [exception.record_id, exception.user_id, exception.change_id, exception.job_id, exception.description, exception.exception_reason, reasons, exception.reason, exception.risk_rating].filter(Boolean).join(" · ") || JSON.stringify(exception);
          } else label = String(exception);
          add(list, "li", "", label);
        });
      } else add(list, "li", "exception-empty", "No exceptions are listed for this stage. Review the source fixture before interpreting this as a pass.");
      if (item.reason) add(row, "p", "control-test-reason", item.reason);
      const evidence = item.evidence_paths || [];
      if (evidence.length) {
        const refs = add(row, "div", "control-evidence-refs");
        add(refs, "strong", "", "Evidence records");
        evidence.forEach(path => add(refs, "code", "", path.replaceAll("\\", "/")));
      }
      add(row, "p", "control-owner", `Owner: ${item.owner || "Not assigned"}`);
    });
  }

  function controlMatches(item, coverage) {
    const query = state.controlQuery.trim().toLowerCase();
    if (!query) return true;
    return [item.id, item.title, item.question, item.objective, item.owner_role, item.nist_csf, item.iso_27001,
      item.expected_evidence, coverage?.status, coverage?.reason]
      .flat(Infinity).filter(Boolean).join(" ").toLowerCase().includes(query);
  }

  function renderControlCatalog() {
    const container = $("#control-catalog");
    const review = state.data?.control_review;
    if (!container) return;
    container.replaceChildren();
    const catalog = review?.catalog;
    const controls = catalog?.controls || [];
    text("#control-catalog-notice", catalog?.notice || "No catalog scope note was supplied.");
    if (!controls.length) {
      add(container, "div", "empty-state", "No vendor control review questions are attached yet.");
      return;
    }
    const coverageById = new Map((review.coverage || []).map(item => [item.control_id, item]));
    const visible = controls.filter(item => controlMatches(item, coverageById.get(item.id)));
    if (!visible.length) {
      add(container, "div", "empty-state", "No review questions match this filter.");
      return;
    }
    visible.forEach(item => {
      const coverage = coverageById.get(item.id);
      const card = add(container, "article", "control-card");
      const head = add(card, "div", "control-card-head");
      const identity = add(head, "div", "control-card-identity");
      add(identity, "span", "control-id", item.id);
      add(identity, "h3", "", item.title);
      const status = coverageStatusClass(coverage?.status);
      add(head, "span", `coverage-status ${status}`, controlStatusLabel(coverage?.status));
      const question = add(card, "p", "control-question");
      add(question, "strong", "", "Review question");
      question.append(document.createTextNode(item.question || "Question not supplied."));
      const objective = add(card, "p", "control-objective");
      add(objective, "strong", "", "Control objective");
      objective.append(document.createTextNode(item.objective || "Objective not supplied."));
      const refs = add(card, "div", "framework-mappings");
      add(refs, "span", "framework-label", "NIST CSF 2.0");
      (item.nist_csf || []).forEach(reference => add(refs, "span", "framework-code", reference));
      add(refs, "span", "framework-label iso-label", "ISO/IEC 27001:2022");
      (item.iso_27001 || []).forEach(reference => add(refs, "span", "framework-code", reference));
      const detail = add(card, "div", "control-card-details");
      const evidenceBox = add(detail, "div", "expected-evidence");
      add(evidenceBox, "strong", "", "Evidence to request");
      const evidenceList = add(evidenceBox, "ul", "");
      (item.expected_evidence || []).forEach(prompt => add(evidenceList, "li", "", prompt));
      const owner = add(detail, "div", "control-owner-block");
      add(owner, "strong", "", "Suggested owner");
      add(owner, "span", "", item.owner_role || "Owner to be assigned");
      if (item.mapping_rationale) {
        const rationale = add(card, "details", "mapping-rationale");
        add(rationale, "summary", "", "Why these framework references");
        add(rationale, "p", "", item.mapping_rationale);
      }
      if (coverage?.reason) add(card, "p", "coverage-reason", coverage.reason);
      if (coverage?.test_ids?.length) add(card, "p", "coverage-test-links", `Related sample tests: ${coverage.test_ids.join(", ")}`);
    });
  }

  function coverageStatusClass(status) {
    if (status === "Documented") return "documented";
    if (status === "Control gap") return "control-gap";
    if (status === "Retest ready") return "retest-ready";
    return "evidence-needed";
  }

  function renderControls() {
    renderControlCoverage();
    renderControlTests();
    renderControlCatalog();
  }

  function render() {
    renderOverview();
    renderEvidence();
    renderFindings();
    renderControls();
    renderDecision();
    renderResults();
    setLoadStatus("Assessment loaded", "ready");
  }

  async function loadAssessment() {
    setLoadStatus("Loading assessment", "loading");
    try {
      const response = await fetch("./output/assessment.json", { cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`Assessment endpoint returned ${response.status}`);
      const payload = await response.json();
      if (!payload || typeof payload !== "object" || !payload.vendor || !Array.isArray(payload.evidence) || !Array.isArray(payload.findings)) {
        throw new Error("Assessment data is missing required case, evidence or findings fields");
      }
      state.data = payload;
      render();
    } catch (error) {
      console.error("Unable to load assessment data", error);
      showError(`${error.message}. Start the local case server and try again.`);
    }
  }

  function announce(message) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.hidden = false;
    window.clearTimeout(announce.timer);
    announce.timer = window.setTimeout(() => { toast.hidden = true; }, 2600);
  }

  $$("[data-view]").forEach(button => button.addEventListener("click", () => showView(button.dataset.view)));
  $$("[data-go]").forEach(button => button.addEventListener("click", () => showView(button.dataset.go)));
  $$("[data-stage]").forEach(button => button.addEventListener("click", () => {
    state.evidenceStage = button.dataset.stage;
    state.selectedEvidence = null;
    renderEvidence();
  }));
  $$("[data-findings-stage]").forEach(button => button.addEventListener("click", () => {
    state.findingsStage = button.dataset.findingsStage;
    renderFindings();
  }));
  $$("[data-control-stage]").forEach(button => button.addEventListener("click", () => {
    state.controlStage = button.dataset.controlStage;
    renderControlTests();
  }));
  $("#control-search").addEventListener("input", event => {
    state.controlQuery = event.currentTarget.value;
    renderControlCatalog();
  });
  $("#refresh-button").addEventListener("click", loadAssessment);
  $("#presentation-toggle").addEventListener("click", event => {
    state.presentation = !state.presentation;
    document.body.classList.toggle("presentation", state.presentation);
    event.currentTarget.setAttribute("aria-pressed", String(state.presentation));
    announce(state.presentation ? "Presentation mode on. Navigation is hidden." : "Presentation mode off.");
  });
  window.addEventListener("keydown", event => {
    if (event.key === "Escape" && state.presentation) {
      state.presentation = false;
      document.body.classList.remove("presentation");
      $("#presentation-toggle").setAttribute("aria-pressed", "false");
    }
  });
  loadAssessment();
})();

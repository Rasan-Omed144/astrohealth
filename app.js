
// Fictional crew portraits. These are AI-generated images, not NASA astronaut photos.
// IDs map exactly to the five seeded demo crew members.
const crewPortraits = Object.freeze({
  "jordan-miller": "assets/crew/jordan-miller.jpg",
  "amara-kim": "assets/crew/amara-kim.jpg",
  "leo-santos": "assets/crew/leo-santos.jpg",
  "maya-chen": "assets/crew/maya-chen.jpg",
  "elias-okafor": "assets/crew/elias-okafor.jpg",
});
function applyCrewPortrait(element, crewId, name) {
  if (!element) return;
  const asset = crewPortraits[crewId];
  if (!asset) {
    element.classList.remove("has-crew-portrait");
    element.style.removeProperty("background-image");
    return;
  }
  element.classList.add("has-crew-portrait");
  element.style.backgroundImage = `url("${asset}")`;
  element.textContent = "";
  element.setAttribute("aria-label", `Illustrative AI-generated astronaut portrait for ${name}`);
}
function updateSelectedCrewPortraits(crew) {
  const nodes = [
    document.querySelector(".user-card .avatar"),
    document.querySelector(".topbar-actions > .avatar"),
    document.querySelector(".astronaut-photo"),
  ];
  for (const el of nodes) applyCrewPortrait(el, crew.id, crew.full_name);
}

const navigationButtons = document.querySelectorAll(".nav-item");
const views = document.querySelectorAll(".view");
const breadcrumb = document.getElementById("breadcrumb-view");
const checkinDialog = document.getElementById("checkin-dialog");
const emergencyDialog = document.getElementById("emergency-dialog");
const toast = document.getElementById("toast");
let toastTimer;
let currentCrewId = "jordan-miller";
let currentCrew = null;
let crewCatalog = [];
let currentProfileId = null;
let reviewSignals = [];
let selectedAlertFilter = "all";
let simulatedHeartRateTimer;
let emergencyDrillActive = false;

function showView(name) {
  if (name === "alerts") renderAlertsView();
  views.forEach((view) => {
    view.classList.toggle("active", view.id === `${name}-view`);
  });
  navigationButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.view === name);
  });
  const labels = {
    astronaut: "Mission health",
    control: "Mission control",
    timeline: "Health timeline",
    spacecraft: "Spacecraft",
    research: "NASA research data",
    alerts: "Alerts",
    profile: "Crew health report",
  };
  breadcrumb.textContent = labels[name] || labels.astronaut;
}

navigationButtons.forEach((button) => {
  button.addEventListener("click", () => showView(button.dataset.view));
});

document.querySelectorAll("[data-navigate]").forEach((button) => {
  button.addEventListener("click", () => showView(button.dataset.navigate));
});

document.querySelectorAll(".dashboard-stat-card[data-dataset]").forEach((button) => {
  button.addEventListener("click", async () => {
    const datasetId = button.dataset.dataset;
    if (!researchDatasets.some((dataset) => dataset.dataset_id === datasetId)) return;
    try {
      await selectResearchDataset(datasetId);
    } catch (error) {
      document.getElementById("research-result-status").textContent =
        `Could not load ${datasetId}: ${error.message}`;
    }
  });
});

function openCheckin() {
  const status = document.getElementById("checkin-save-status");
  status.textContent = "";
  const sleepField = document.getElementById("sleep-hours");
  sleepField.setCustomValidity("");
  if (typeof checkinDialog.showModal === "function" && !checkinDialog.open) {
    checkinDialog.showModal();
  }
}
document.getElementById("close-checkin").addEventListener("click", () => checkinDialog.close());
document.getElementById("cancel-checkin").addEventListener("click", () => checkinDialog.close());

document.getElementById("open-checkin").addEventListener("click", openCheckin);
document.getElementById("timeline-checkin").addEventListener("click", openCheckin);

const emergencyScenarios = {
  fire: {
    title: "Fire or smoke",
    guidance: "Use the vehicle's approved fire-response checklist and alert the crew using designated procedures. Follow trained crew direction; use response equipment only as trained and as the checklist directs.",
    drillPrompt: "You notice smoke in a module. What is the safest first response?",
  },
  pressure: {
    title: "Cabin pressure warning",
    guidance: "Treat an official pressure warning as urgent: alert the crew and follow the vehicle-specific pressure-loss checklist and commander/flight director instructions. Do not rely on this app to confirm cabin conditions.",
    drillPrompt: "A cabin pressure warning is announced. What should you do first?",
  },
  radiation: {
    title: "Radiation event",
    guidance: "Follow the mission's radiation-response plan and crew communications. Use only mission-approved shelter or exposure-mitigation actions as directed; this app has no radiation sensor or live space-weather feed.",
    drillPrompt: "Mission control announces a radiation event. What should guide your response?",
  },
  medical: {
    title: "Crew medical emergency",
    guidance: "Alert the crew and medical support using approved onboard communications. Follow the mission medical checklist and trained crew direction; this prototype cannot assess or treat a medical condition.",
    drillPrompt: "A crewmate appears to need urgent medical help. What should you do first?",
  },
  atmosphere: {
    title: "Air-quality or toxic-atmosphere warning",
    guidance: "Treat official atmosphere alerts seriously. Notify the crew and follow the vehicle-specific air-quality response checklist and trained instructions. Do not use this app to identify contaminants or decide equipment changes.",
    drillPrompt: "An official air-quality warning is issued. What is the safest response?",
  },
};

function renderEmergencyScenario() {
  const scenario = emergencyScenarios[document.getElementById("emergency-scenario").value];
  if (!scenario) return;
  document.getElementById("emergency-scenario-title").textContent = scenario.title;
  document.getElementById("emergency-scenario-guidance").textContent = scenario.guidance;
  if (emergencyDrillActive) startEmergencyDrill();
}

function startEmergencyDrill() {
  const scenario = emergencyScenarios[document.getElementById("emergency-scenario").value];
  if (!scenario) return;
  emergencyDrillActive = true;
  const content = document.getElementById("emergency-drill-content");
  content.replaceChildren();
  const prompt = document.createElement("p");
  prompt.className = "drill-prompt";
  prompt.textContent = `SIMULATION ONLY · ${scenario.drillPrompt}`;
  const answers = document.createElement("div");
  answers.className = "drill-answers";
  const choices = [
    { text: "Use the approved onboard alert and checklist; follow crew direction.", safe: true },
    { text: "Wait and see if the warning goes away before telling anyone.", safe: false },
    { text: "Try an unapproved action without checking the mission procedure.", safe: false },
  ];
  for (const choice of choices) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "drill-answer";
    button.textContent = choice.text;
    button.addEventListener("click", () => {
      answers.replaceChildren();
      const feedback = document.createElement("p");
      feedback.className = `drill-feedback ${choice.safe ? "correct" : "retry"}`;
      feedback.textContent = choice.safe
        ? "Correct. In a real event, use the vehicle-specific checklist and trained crew instructions."
        : "Not the safest choice. Practice using the approved alert procedure and following the mission-specific checklist.";
      answers.append(feedback);
      emergencyDrillActive = false;
    });
    answers.append(button);
  }
  content.append(prompt, answers);
}

document.getElementById("open-emergency").addEventListener("click", () => {
  renderEmergencyScenario();
  if (typeof emergencyDialog.showModal === "function") emergencyDialog.showModal();
});
document.getElementById("close-emergency").addEventListener("click", () => emergencyDialog.close());
emergencyDialog.addEventListener("close", () => {
  emergencyDrillActive = false;
});
document.getElementById("emergency-scenario").addEventListener("change", renderEmergencyScenario);
document.getElementById("start-emergency-drill").addEventListener("click", startEmergencyDrill);

document.querySelectorAll(".range-control input").forEach((range) => {
  range.addEventListener("input", () => {
    range.parentElement.querySelector("output").value = range.value;
  });
});

document.getElementById("checkin-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const saveButton = document.getElementById("save-checkin");
  const status = document.getElementById("checkin-save-status");
  if (saveButton.disabled) return;
  const sleep = Number(document.getElementById("sleep-hours").value);
  if (!Number.isFinite(sleep) || sleep < 0 || sleep > 24) {
    document.getElementById("sleep-hours").setCustomValidity("Enter sleep duration between 0 and 24 hours.");
    document.getElementById("sleep-hours").reportValidity();
    status.textContent = "Enter a valid sleep duration (0–24 hours).";
    return;
  }
  document.getElementById("sleep-hours").setCustomValidity("");
  const energy = document.getElementById("energy").value;
  const stress = document.getElementById("stress").value;
  const mood = document.getElementById("mood").value;
  saveButton.disabled = true;
  saveButton.textContent = "Saving…";
  status.textContent = "Saving to the local database…";
  try {
    await apiRequest(`/api/crew/${encodeURIComponent(currentCrewId)}/checkins`, {
      method: "POST",
      body: JSON.stringify({ energy: Number(energy), stress: Number(stress), mood, sleep_hours: sleep }),
    });
    document.getElementById("checkin-timestamp").textContent = `Today · ${new Date().toISOString().slice(11, 16)} UTC`;
    document.getElementById("checkin-energy").textContent = `${energy} / 5`;
    document.getElementById("checkin-stress").textContent = `${stress} / 5`;
    document.getElementById("checkin-mood").textContent = mood;
    document.getElementById("checkin-sleep").textContent = `${sleep.toFixed(1)} hrs`;
    document.getElementById("sleep-indicator-value").textContent = sleep.toFixed(1);
    const sleepStatus = document.getElementById("sleep-status");
    const sleepIsLow = sleep < 7;
    sleepStatus.classList.toggle("watch", sleepIsLow);
    sleepStatus.classList.toggle("good", !sleepIsLow);
    sleepStatus.lastChild.textContent = sleepIsLow ? " WATCH" : " NORMAL";
    status.textContent = "Check-in saved.";
    checkinDialog.close();
    showToast("Check-in saved to the local database.");
    await loadBackendData();
  } catch (error) {
    status.textContent = `Could not save: ${error.message}`;
    showToast(`Check-in could not be saved: ${error.message}`);
  } finally {
    saveButton.disabled = false;
    saveButton.textContent = "Save check-in";
  }
});

document.getElementById("sleep-hours").addEventListener("input", (event) => {
  event.currentTarget.setCustomValidity("");
});

document.getElementById("recommendation-toggle").addEventListener("click", (event) => {
  const details = document.getElementById("recommendation-details");
  const opening = details.hidden;
  details.hidden = !opening;
  event.currentTarget.querySelector("span").textContent = opening ? "−" : "＋";
  event.currentTarget.setAttribute("aria-expanded", String(opening));
});

document.getElementById("dismiss-banner").addEventListener("click", () => {
  document.querySelector("#astronaut-view .demo-banner").hidden = true;
});

document.querySelectorAll(".dismiss-view-banner").forEach((button) => {
  button.addEventListener("click", () => {
    button.closest(".demo-banner").hidden = true;
  });
});

document.getElementById("review-alert").addEventListener("click", () => {
  document.getElementById("recommendation-details").hidden = false;
  document.getElementById("recommendation-toggle").querySelector("span").textContent = "−";
  document.getElementById("recommendation-toggle").setAttribute("aria-expanded", "true");
  document.getElementById("recommendation-details").scrollIntoView({ behavior: "smooth", block: "nearest" });
});



let activeChartMetric = "Resting heart rate";
function setChartMetric(metricName) {
  if (!chartMetricKeys[metricName]) return;
  activeChartMetric = metricName;
  document.getElementById("timeline-metric-heading").textContent = metricName;
  document.querySelectorAll("#metric-select, #timeline-metric").forEach((select) => {
    select.value = metricName;
  });
}

const chartMetricKeys = {
  "Resting heart rate": "resting_heart_rate",
  "Blood oxygen": "blood_oxygen",
  "Sleep duration": "sleep_duration",
  Exercise: "exercise_minutes",
  "Heart rate variability": "heart_rate_variability",
  "Systolic blood pressure": "systolic_blood_pressure",
  "Body temperature": "body_temperature",
  Hydration: "hydration_liters",
  "Stress check-in": "stress_score",
  "Bone-loading exercise": "bone_loading_minutes",
};

async function loadMetricHistory(metricName) {
  const metricKey = chartMetricKeys[metricName];
  if (!metricKey || !currentCrewId) return;
  const records = await apiRequest(
    `/api/crew/${currentCrewId}/measurements?metric=${encodeURIComponent(metricKey)}&limit=30&daily=true`,
  );
  if (records.length < 2) {
    throw new Error(`Not enough saved readings to display a 30-day ${metricName.toLowerCase()} trend.`);
  }
  const points = records.slice().reverse();
  const values = points.map((record) => record.value);
  const lower = Math.min(...values, ...records.map((record) => record.baseline_min));
  const upper = Math.max(...values, ...records.map((record) => record.baseline_max));
  const padding = (upper - lower) * 0.15 || 1;
  const min = lower - padding;
  const max = upper + padding;
  const ySmall = (value) => 10 + ((max - value) / (max - min)) * 116;
  const yLarge = (value) => 14 + ((max - value) / (max - min)) * 198;
  const buildLine = (width, y) => points.map((point, index) =>
    `${index === 0 ? "M" : "L"}${(index * width) / (points.length - 1)},${y(point.value)}`,
  ).join(" ");
  const smallLine = buildLine(620, ySmall);
  const largeLine = buildLine(900, yLarge);
  document.getElementById("chart-line").setAttribute("d", smallLine);
  document.getElementById("chart-area").setAttribute("d", `${smallLine} L620,156 L0,156 Z`);
  document.getElementById("large-line").setAttribute("d", largeLine);
  document.getElementById("large-area").setAttribute("d", `${largeLine} L900,240 L0,240 Z`);
  document.querySelector(".trend-chart circle").setAttribute("cy", String(ySmall(points.at(-1).value)));
  document.querySelector(".large-chart circle").setAttribute("cy", String(yLarge(points.at(-1).value)));
  const baseline = (records[0].baseline_min + records[0].baseline_max) / 2;
  document.querySelectorAll(".baseline-line").forEach((line) => {
    const y = line.closest(".trend-chart") ? ySmall(baseline) : yLarge(baseline);
    line.setAttribute("y1", String(y));
    line.setAttribute("y2", String(y));
  });
  const latest = records[0];
  const latestValue = Number.isInteger(latest.value) ? latest.value : Number(latest.value.toFixed(1));
  document.getElementById("chart-current").innerHTML = `${latestValue} <small>${latest.unit}</small>`;
  document.getElementById("timeline-current").innerHTML = `${latestValue} <small>${latest.unit}</small>`;
  document.getElementById("timeline-baseline").innerHTML =
    `${latest.baseline_min}–${latest.baseline_max} <small>${latest.unit}</small>`;
  const average = values.reduce((total, value) => total + value, 0) / values.length;
  const formatMetric = (value) => Number.isInteger(value) ? String(value) : Number(value.toFixed(1)).toString();
  document.getElementById("timeline-average").textContent = `${formatMetric(average)} ${latest.unit}`;
  document.getElementById("timeline-minimum").textContent = `${formatMetric(Math.min(...values))} ${latest.unit}`;
  document.getElementById("timeline-maximum").textContent = `${formatMetric(Math.max(...values))} ${latest.unit}`;
  document.getElementById("timeline-reading-count").textContent = `${points.length} / 30`;
  const difference = latest.value - baseline;
  const deltaText = Math.abs(difference) < 0.05
    ? "At baseline"
    : `${difference > 0 ? "↑" : "↓"} ${Number(Math.abs(difference).toFixed(1))} ${latest.unit} from midpoint`;
  document.querySelectorAll(".chart-delta.positive").forEach((element) => {
    if (element.closest(".timeline-metrics")) {
      element.textContent = deltaText;
    } else {
      element.innerHTML = `${deltaText} <small>vs. reference midpoint</small>`;
    }
  });
  const yLabels = [max, max - (max - min) / 3, max - (2 * (max - min)) / 3, min];
  document.querySelectorAll(".chart-y-labels span, .chart-grid-labels span").forEach((label, labelIndex) => {
    const index = labelIndex % yLabels.length;
    const digits = latest.unit === "bpm" || latest.unit === "min" ? 0 : 1;
    label.textContent = Number(yLabels[index].toFixed(digits)).toString();
  });
  document.querySelectorAll(".chart-x-labels").forEach((labels) => {
    const spans = labels.querySelectorAll("span");
    const first = new Date(points[0].recorded_at);
    const last = new Date(points.at(-1).recorded_at);
    spans.forEach((span, index) => {
      const dayIndex = Math.round((index * (points.length - 1)) / (spans.length - 1));
      const date = new Date(points[dayIndex].recorded_at);
      span.textContent = new Intl.DateTimeFormat("en", {
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      }).format(date);
    });
    const markerGroup = document.getElementById("large-points");
    markerGroup.replaceChildren();
    points.forEach((point, index) => {
      const marker = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      const x = (index * 900) / (points.length - 1);
      const y = yLarge(point.value);
      marker.setAttribute("cx", String(x));
      marker.setAttribute("cy", String(y));
      marker.setAttribute("r", index === points.length - 1 ? "4.5" : "2.5");
      marker.setAttribute("class", "timeline-point");
      marker.setAttribute("aria-label", `${point.recorded_at.slice(0, 10)}: ${formatMetric(point.value)} ${latest.unit}`);
      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      title.textContent = `${point.recorded_at.slice(0, 10)} · ${formatMetric(point.value)} ${latest.unit}`;
      marker.append(title);
      markerGroup.append(marker);
    });
    labels.setAttribute("aria-label", `Dates ${first.toISOString().slice(0, 10)} to ${last.toISOString().slice(0, 10)}`);
  });
  const rangeLabel = `30-DAY TREND · ${points.length} READINGS`;
  document.querySelector(".timeline-main .eyebrow").textContent = rangeLabel;
  document.querySelector(".large-chart").setAttribute("aria-label", `${metricName} trend over the last ${points.length} days from saved demo measurements`);
  const inRange = latest.value >= latest.baseline_min && latest.value <= latest.baseline_max;
  document.querySelector(".trend-insight h3").textContent = inRange
    ? `${metricName} is within the saved reference range.`
    : `${metricName} is outside the saved reference range.`;
  document.querySelector(".trend-insight p").textContent =
    `The timeline shows ${points.length} saved readings over approximately 30 days. ` +
    `The reference range is ${latest.baseline_min}–${latest.baseline_max} ${latest.unit}; ` +
    `readings are illustrative demo data, not a medical assessment.`;
}

const spacecraftMetrics = {
  carbon_dioxide_ppm: { label: "Carbon dioxide", unit: "ppm", digits: 0 },
  cabin_temperature_c: { label: "Cabin temperature", unit: "°C", digits: 1 },
  relative_humidity_pct: { label: "Relative humidity", unit: "%", digits: 0 },
  accumulated_radiation_dose_msv: { label: "Accumulated radiation dose", unit: "mSv", digits: 2 },
};
let selectedSpacecraftMetric = "carbon_dioxide_ppm";

function formatSpacecraftValue(value, digits) {
  return Number(value).toFixed(digits);
}

function renderSpacecraftChart(records) {
  const metric = spacecraftMetrics[selectedSpacecraftMetric];
  if (!metric) return;
  const values = records.map((record) => record[selectedSpacecraftMetric]);
  const low = Math.min(...values);
  const high = Math.max(...values);
  const padding = (high - low) * 0.2 || Math.max(Math.abs(high) * 0.02, 0.1);
  const min = low - padding;
  const max = high + padding;
  const y = (value) => 14 + ((max - value) / (max - min)) * 198;
  const line = records.map((record, index) =>
    `${index === 0 ? "M" : "L"}${(index * 900) / (records.length - 1)},${y(record[selectedSpacecraftMetric])}`,
  ).join(" ");
  document.getElementById("spacecraft-chart-heading").textContent = metric.label;
  document.getElementById("spacecraft-chart-line").setAttribute("d", line);
  document.getElementById("spacecraft-chart-area").setAttribute("d", `${line} L900,240 L0,240 Z`);
  const points = document.getElementById("spacecraft-chart-points");
  points.replaceChildren();
  records.forEach((record, index) => {
    const marker = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    const value = record[selectedSpacecraftMetric];
    marker.setAttribute("cx", String((index * 900) / (records.length - 1)));
    marker.setAttribute("cy", String(y(value)));
    marker.setAttribute("r", index === records.length - 1 ? "4.5" : "2.5");
    marker.setAttribute("class", "spacecraft-point");
    marker.setAttribute("aria-label", `${record.recorded_at.slice(0, 10)}: ${formatSpacecraftValue(value, metric.digits)} ${metric.unit}`);
    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = `${record.recorded_at.slice(0, 10)} · ${formatSpacecraftValue(value, metric.digits)} ${metric.unit}`;
    marker.append(title);
    points.append(marker);
  });
  const average = values.reduce((total, value) => total + value, 0) / values.length;
  document.getElementById("spacecraft-chart-latest").textContent =
    `${formatSpacecraftValue(values.at(-1), metric.digits)} ${metric.unit}`;
  document.getElementById("spacecraft-chart-average").textContent =
    `${formatSpacecraftValue(average, metric.digits)} ${metric.unit}`;
  document.getElementById("spacecraft-chart-minimum").textContent =
    `${formatSpacecraftValue(low, metric.digits)} ${metric.unit}`;
  document.getElementById("spacecraft-chart-maximum").textContent =
    `${formatSpacecraftValue(high, metric.digits)} ${metric.unit}`;
  document.querySelectorAll("#spacecraft-y-labels span").forEach((label, index) => {
    label.textContent = formatSpacecraftValue(max - ((max - min) * index) / 3, metric.digits);
  });
  const dateLabels = document.querySelectorAll("#spacecraft-chart .chart-x-labels span");
  dateLabels.forEach((label, index) => {
    const pointIndex = Math.round((index * (records.length - 1)) / (dateLabels.length - 1));
    label.textContent = new Intl.DateTimeFormat("en", {
      month: "short",
      day: "numeric",
      timeZone: "UTC",
    }).format(new Date(records[pointIndex].recorded_at));
  });
  document.querySelector("#spacecraft-chart svg").setAttribute(
    "aria-label",
    `${metric.label} over ${records.length} daily illustrative spacecraft readings`,
  );
}

async function loadSpacecraftHistory() {
  const errorBanner = document.getElementById("spacecraft-api-error");
  try {
    const response = await apiRequest("/api/spacecraft/history?limit=30");
    if (!Array.isArray(response.items) || response.items.length !== 30) {
      throw new Error(`Expected 30 daily spacecraft readings; received ${response.items?.length ?? 0}.`);
    }
    const records = response.items;
    const latest = records.at(-1);
    document.getElementById("spacecraft-co2-value").textContent =
      formatSpacecraftValue(latest.carbon_dioxide_ppm, 0);
    document.getElementById("dashboard-co2-value").textContent =
      formatSpacecraftValue(latest.carbon_dioxide_ppm, 0);
    document.getElementById("spacecraft-temperature-value").textContent =
      formatSpacecraftValue(latest.cabin_temperature_c, 1);
    document.getElementById("spacecraft-humidity-value").textContent =
      formatSpacecraftValue(latest.relative_humidity_pct, 0);
    document.getElementById("spacecraft-dose-value").textContent =
      formatSpacecraftValue(latest.accumulated_radiation_dose_msv, 2);
    renderSpacecraftChart(records);
    errorBanner.hidden = true;
    errorBanner.textContent = "";
  } catch (error) {
    errorBanner.hidden = false;
    errorBanner.textContent = `Spacecraft readings could not be loaded: ${error.message}`;
  }
}

document.querySelectorAll(".spacecraft-metric-button").forEach((button) => {
  button.addEventListener("click", async () => {
    selectedSpacecraftMetric = button.dataset.spacecraftMetric;
    document.querySelectorAll(".spacecraft-metric-button").forEach((metricButton) => {
      const selected = metricButton === button;
      metricButton.classList.toggle("selected", selected);
      metricButton.setAttribute("aria-pressed", String(selected));
    });
    await loadSpacecraftHistory();
  });
});

document.querySelectorAll("#metric-select, #timeline-metric").forEach((select) => {
  // A real native dropdown, keyboard accessible and visible on click.
  for (const name of Object.keys(chartMetricKeys)) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    select.append(option);
  }
  select.value = activeChartMetric;
  select.addEventListener("change", async () => {
    setChartMetric(select.value);
    try {
      await loadMetricHistory(activeChartMetric);
    } catch (error) {
      showToast(`Could not load measurement history: ${error.message}`);
    }
  });
});

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("show"), 2800);
}

async function apiRequest(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : `Request failed (${response.status}).`);
  }
  return body;
}

const researchPageSize = 50;
let researchDatasets = [];
let selectedResearchDataset = null;
let researchOffset = 0;
let researchRequestId = 0;
let researchSearchTimer = null;

async function loadResearchData() {
  const status = document.getElementById("research-result-status");
  try {
    researchDatasets = await apiRequest("/api/research/datasets");
    renderResearchDatasets();
    if (researchDatasets.length === 0) {
      status.textContent = "No NASA research datasets are imported yet. Run the project data importer.";
      return;
    }
    status.textContent = "Choose one of the NASA studies above to explore its records.";
  } catch (error) {
    status.textContent = `Research datasets could not be loaded: ${error.message}`;
  }
}

function renderResearchDatasets() {
  const list = document.getElementById("research-dataset-list");
  list.replaceChildren();
  for (const dataset of researchDatasets) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "research-dataset-card";
    button.classList.toggle("selected", dataset.dataset_id === selectedResearchDataset);
    button.setAttribute("aria-pressed", String(dataset.dataset_id === selectedResearchDataset));
    button.addEventListener("click", async () => {
      try {
        await selectResearchDataset(dataset.dataset_id);
      } catch (error) {
        document.getElementById("research-result-status").textContent =
          `Could not load ${dataset.dataset_id}: ${error.message}`;
      }
    });

    const title = document.createElement("strong");
    title.textContent = dataset.title;
    const source = document.createElement("span");
    source.className = "research-dataset-id";
    source.textContent = `${dataset.dataset_id} · ${dataset.health_system}`;
    const details = document.createElement("small");
    const descriptions = {
      "OSD-569": "Complete blood count · whole-blood cell measurements",
      "OSD-575": "Cardiovascular biomarkers · serum measurements",
      "OSD-656": "Immune and inflammation markers · urine measurements",
    };
    const description = document.createElement("span");
    description.className = "research-dataset-description";
    description.textContent = descriptions[dataset.dataset_id] || dataset.health_system;
    details.textContent =
      `${dataset.measurement_count.toLocaleString()} measurements · ` +
      `${dataset.participant_count} participants · ${dataset.timepoint_count} timepoints`;
    const action = document.createElement("span");
    action.className = "research-card-action";
    action.textContent = "Explore records ↗";
    button.append(source, title, description, details, action);
    list.append(button);
  }
  const dashboardCounts = {
    "OSD-575": "dashboard-serum-count",
    "OSD-656": "dashboard-urine-count",
    "OSD-569": "dashboard-cbc-count",
  };
  for (const [datasetId, elementId] of Object.entries(dashboardCounts)) {
    const dataset = researchDatasets.find((item) => item.dataset_id === datasetId);
    const element = document.getElementById(elementId);
    if (dataset && element) element.textContent = dataset.measurement_count.toLocaleString();
  }
}

async function selectResearchDataset(datasetId) {
  const dataset = researchDatasets.find((item) => item.dataset_id === datasetId);
  if (!dataset) return;
  selectedResearchDataset = datasetId;
  researchOffset = 0;
  document.getElementById("research-search").value = "";
  document.getElementById("research-browser").hidden = false;
  document.getElementById("research-browser-heading").textContent = dataset.title;
  renderResearchDatasets();
  document.getElementById("research-results").replaceChildren();
  document.getElementById("research-result-status").textContent =
    `Loading ${dataset.title}…`;
  document.getElementById("research-source-file").textContent =
    `${dataset.mission} · Source file: ${dataset.source_file}`;
  const filters = await apiRequest(`/api/research/datasets/${encodeURIComponent(datasetId)}/filters`);
  setResearchFilterOptions("research-participant-filter", "All participants", filters.participant_id);
  setResearchFilterOptions("research-analyte-filter", "All measures", filters.analyte);
  setResearchFilterOptions("research-timepoint-filter", "All timepoints", filters.timepoint);
  await loadResearchMeasurements();
}

function setResearchFilterOptions(elementId, allLabel, values) {
  const select = document.getElementById(elementId);
  select.replaceChildren();
  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = allLabel;
  select.append(allOption);
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  }
}

function formatResearchNumber(value) {
  if (value == null) return "—";
  return new Intl.NumberFormat(undefined, { maximumSignificantDigits: 7 }).format(value);
}

async function loadResearchMeasurements() {
  const params = new URLSearchParams({
    dataset_id: selectedResearchDataset,
    limit: String(researchPageSize),
    offset: String(researchOffset),
  });
  for (const [field, elementId] of [
    ["participant_id", "research-participant-filter"],
    ["analyte", "research-analyte-filter"],
    ["timepoint", "research-timepoint-filter"],
  ]) {
    const value = document.getElementById(elementId).value;
    if (value) params.set(field, value);
  }

  const q = document.getElementById("research-search").value.trim();
  if (q) params.set("q", q);
  const tbody = document.getElementById("research-results");
  const status = document.getElementById("research-result-status");
  const requestId = ++researchRequestId;
  status.textContent = "Searching source measurements…";
  try {
    const response = await apiRequest(`/api/research/measurements?${params}`);
    if (requestId !== researchRequestId) return;
    tbody.replaceChildren();
    for (const record of response.items) {
      const row = document.createElement("tr");
      const range = record.reference_min == null && record.reference_max == null
        ? "—"
        : `${formatResearchNumber(record.reference_min)}–${formatResearchNumber(record.reference_max)}`;
      const secondary = record.secondary_value == null
        ? record.secondary_value_raw
          ? `${record.secondary_value_raw} (${record.secondary_value_basis})`
          : "—"
        : `${formatResearchNumber(record.secondary_value)} ${record.secondary_measure || ""} (${record.secondary_value_basis})`.trim();
      const cells = [
        record.analyte,
        record.participant_id,
        record.timepoint,
        record.phase || "—",
        formatResearchNumber(record.value),
        record.unit || "—",
      ];
      for (const value of cells) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      }
      const moreCell = document.createElement("td");
      const more = document.createElement("details");
      more.className = "research-row-detail";
      const summary = document.createElement("summary");
      summary.textContent = "Details";
      const detailBlock = document.createElement("div");
      detailBlock.className = "research-detail-block";
      const details = [
        ["Dataset", record.dataset_id],
        ["Mission", record.mission],
        ["Source file", record.source_file],
        ["Value basis", record.measurement_basis],
        ["Reference range (if supplied)", range],
        ["Secondary value", secondary],
        ["Assay", record.assay_type || "—"],
        ["Source row", String(record.source_row ?? "—")],
      ];
      for (const [label, value] of details) {
        const line = document.createElement("p");
        const key = document.createElement("strong");
        key.textContent = `${label}: `;
        line.append(key, document.createTextNode(value ?? "—"));
        detailBlock.append(line);
      }
      more.append(summary, detailBlock);
      moreCell.append(more);
      row.append(moreCell);
      tbody.append(row);
    }
    const end = Math.min(researchOffset + response.items.length, response.total);
    const start = response.total === 0 ? 0 : researchOffset + 1;
    status.textContent = `Showing ${start}–${end} of ${response.total.toLocaleString()} source records.`;
    document.getElementById("research-page-status").textContent =
      `${response.total.toLocaleString()} records · page ${response.total === 0 ? 0 : Math.floor(researchOffset / researchPageSize) + 1}`;
    document.getElementById("research-previous").disabled = researchOffset === 0;
    document.getElementById("research-next").disabled = researchOffset + researchPageSize >= response.total;
  } catch (error) {
    if (requestId !== researchRequestId) return;
    tbody.replaceChildren();
    status.textContent = `Research measurements could not be loaded: ${error.message}`;
    document.getElementById("research-page-status").textContent = "—";
    document.getElementById("research-previous").disabled = true;
    document.getElementById("research-next").disabled = true;
  }
}

for (const elementId of [
  "research-participant-filter",
  "research-analyte-filter",
  "research-timepoint-filter",
]) {
  document.getElementById(elementId).addEventListener("change", () => {
    researchOffset = 0;
    loadResearchMeasurements();
  });
}

document.getElementById("research-close").addEventListener("click", () => {
  selectedResearchDataset = null;
  researchRequestId += 1;
  document.getElementById("research-browser").hidden = true;
  document.getElementById("research-search").value = "";
  renderResearchDatasets();
});
document.getElementById("research-search").addEventListener("input", () => {
  window.clearTimeout(researchSearchTimer);
  researchSearchTimer = window.setTimeout(() => {
    researchOffset = 0;
    if (selectedResearchDataset) loadResearchMeasurements();
  }, 220);
});

document.getElementById("research-previous").addEventListener("click", () => {
  researchOffset = Math.max(0, researchOffset - researchPageSize);
  loadResearchMeasurements();
});
document.getElementById("research-next").addEventListener("click", () => {
  researchOffset += researchPageSize;
  loadResearchMeasurements();
});

function setApiStatus(connected, message = "") {
  document.getElementById("api-connection-title").textContent = connected ? "Local API connected" : "API unavailable";
  document.getElementById("api-connection-detail").textContent = connected ? "SQLite database ready" : "Start FastAPI to sync data";
  document.getElementById("api-connection-label").textContent = connected ? "DATABASE CONNECTED" : "API DISCONNECTED";
  for (const id of ["api-error-banner", "control-api-error-banner"]) {
    const banner = document.getElementById(id);
    banner.hidden = connected;
    banner.textContent = connected ? "" : `Backend connection failed: ${message}. Start the FastAPI server to load and save database records.`;
  }
}

function metricValue(crew, key) {
  return crew.latest_measurements?.[key] ?? null;
}

function renderIndicator(metricKey, measurement) {
  if (!measurement && metricKey !== "blood_pressure") return;
  const card = document.querySelector(`.indicator-card[data-metric="${metricKey}"]`);
  if (!card) return;
  const value = card.querySelector(".indicator-value");
  let inRange = false;
  if (metricKey === "blood_pressure") {
    const systolic = metricValue(currentCrew, "systolic_blood_pressure")?.value;
    const diastolic = metricValue(currentCrew, "diastolic_blood_pressure")?.value;
    if (systolic != null && diastolic != null) {
      value.innerHTML = `${Math.round(systolic)}/${Math.round(diastolic)} <small>mmHg</small>`;
      const systolicMeasurement = metricValue(currentCrew, "systolic_blood_pressure");
      const diastolicMeasurement = metricValue(currentCrew, "diastolic_blood_pressure");
      inRange = systolic >= systolicMeasurement.baseline_min &&
        systolic <= systolicMeasurement.baseline_max &&
        diastolic >= diastolicMeasurement.baseline_min &&
        diastolic <= diastolicMeasurement.baseline_max;
    }
  } else {
    const formatted = Number.isInteger(measurement.value) ? measurement.value : Number(measurement.value.toFixed(1));
    if (metricKey === "resting_heart_rate") {
      value.innerHTML = `<span id="heart-rate-live-value">${formatted}</span> <small>${measurement.unit}</small>`;
    } else if (metricKey === "sleep_duration") {
      value.innerHTML = `<span id="sleep-indicator-value">${formatted}</span> <small>${measurement.unit}</small>`;
    } else {
      value.innerHTML = `${formatted} <small>${measurement.unit}</small>`;
    }
    inRange = measurement.value >= measurement.baseline_min && measurement.value <= measurement.baseline_max;
    const [label, unit] = {
      resting_heart_rate: ["Baseline", "bpm"],
      blood_oxygen: ["Baseline", "%"],
      sleep_duration: ["Baseline", "hrs"],
      exercise_minutes: ["Daily target", "min"],
      heart_rate_variability: ["Baseline", "ms"],
      body_temperature: ["Baseline", "°C"],
      hydration_liters: ["Daily target", "L"],
      stress_score: ["Personal range", ""],
      bone_loading_minutes: ["Exercise plan", "min"],
    }[metricKey] ?? ["Baseline", measurement.unit];
    const baseline = card.querySelector(".indicator-baseline > span:first-child");
    baseline.textContent = metricKey === "stress_score"
      ? `${label} ${measurement.baseline_min}–${measurement.baseline_max}`
      : `${label} ${measurement.baseline_min}–${measurement.baseline_max} ${unit}`;
  }
  const status = card.querySelector(".status-pill");
  status.classList.toggle("watch", !inRange);
  status.classList.toggle("good", inRange);
  status.innerHTML = `<i></i> ${inRange ? "IN RANGE" : "REVIEW RANGE"}`;
}

function renderIndicatorSparkline(metricKey, records) {
  const card = document.querySelector(`.indicator-card[data-metric="${metricKey}"]`);
  const sparkline = card?.querySelector(".mini-sparkline");
  if (!sparkline || records.length === 0) return;
  const values = records.slice(0, 8).reverse().map((record) => record.value);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const levels = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"];
  sparkline.textContent = values.map((value) => {
    const level = maximum === minimum ? 3 : Math.round(((value - minimum) / (maximum - minimum)) * 7);
    return levels[level];
  }).join("");
  sparkline.setAttribute("aria-label", `Recent ${metricKey.replaceAll("_", " ")} readings`);
  sparkline.title = "Recent saved readings, oldest to newest";
}

function renderRangeSummary() {
  const metrics = [
    "resting_heart_rate", "blood_oxygen", "sleep_duration", "exercise_minutes",
    "heart_rate_variability", "systolic_blood_pressure", "body_temperature",
    "hydration_liters", "stress_score", "bone_loading_minutes",
  ];
  const available = metrics.map((key) => metricValue(currentCrew, key)).filter(Boolean);
  const withinRange = available.filter((measurement) =>
    measurement.value >= measurement.baseline_min && measurement.value <= measurement.baseline_max,
  ).length;
  const percentage = available.length ? Math.round((withinRange / available.length) * 100) : 0;
  document.getElementById("health-score-value").textContent = String(percentage);
  const overviewStatus = document.getElementById("overview-status-value");
  if (overviewStatus) overviewStatus.textContent = available.length ? `${withinRange} / ${available.length} in range` : "No readings";
  document.getElementById("health-score-description").textContent =
    `${withinRange} of ${available.length} available readings are within configured demo ranges.`;
  document.getElementById("health-score-count").textContent = `${available.length} readings · demo ranges`;
  document.querySelector(".score-ring").setAttribute(
    "aria-label",
    `${percentage}% of available readings are within configured demonstration ranges`,
  );
  document.querySelector(".ring-progress").style.strokeDashoffset =
    String(427.3 * (1 - percentage / 100));
  const status = document.getElementById("health-score-status");
  status.classList.toggle("watch", percentage < 100);
  status.classList.toggle("good", percentage === 100);
  status.innerHTML = `<i></i> ${percentage === 100 ? "ALL IN RANGE" : "RANGE SUMMARY"}`;
}

function renderSleepPattern(records) {
  const recent = records.slice(0, 3);
  const heading = document.querySelector(".alert-body h3");
  const description = document.querySelector(".alert-body p");
  const counter = document.querySelector(".alert-counter");
  const recommendation = document.getElementById("recommendation-toggle");
  const recommendationDetails = document.querySelector("#recommendation-details p");
  if (recent.length === 0) {
    heading.textContent = "No recent sleep readings";
    description.textContent = "A sleep trend will appear when saved measurements are available.";
    counter.textContent = "00";
    recommendation.hidden = true;
    return;
  }
  const average = recent.reduce((total, record) => total + record.value, 0) / recent.length;
  const minimum = recent[0].baseline_min;
  const belowRange = average < minimum;
  heading.textContent = belowRange ? "Recent sleep below configured range" : "Recent sleep within configured range";
  description.textContent =
    `Average ${average.toFixed(1)} hours across ${recent.length} recent readings; configured demo minimum is ${minimum} hours.`;
  counter.textContent = belowRange ? "01" : "00";
  recommendation.hidden = false;
  recommendation.childNodes[0].textContent = belowRange ? "See suggested next steps " : "About this summary ";
  recommendationDetails.textContent = belowRange
    ? "Consider reviewing your rest schedule and noting any changes in workload. If this pattern continues or you have concerns, discuss it with mission medical support."
    : "Recent saved readings are within the configured demo range. This informational summary is not a medical assessment.";
}

function renderCrewTable(crews) {
  const tbody = document.getElementById("crew-table-body");
  tbody.replaceChildren();
  for (const crew of crews) {
    const row = document.createElement("tr");
    const initials = crew.full_name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
    const sleep = metricValue(crew, "sleep_duration")?.value;
    const hr = metricValue(crew, "resting_heart_rate")?.value;
    const oxygen = metricValue(crew, "blood_oxygen")?.value;
    const systolic = metricValue(crew, "systolic_blood_pressure")?.value;
    const diastolic = metricValue(crew, "diastolic_blood_pressure")?.value;
    const hrv = metricValue(crew, "heart_rate_variability")?.value;
    const temperature = metricValue(crew, "body_temperature")?.value;
    const exercise = metricValue(crew, "exercise_minutes")?.value;
    const needsReview = Object.values(crew.latest_measurements || {}).some(m => !latestRangeStatus(m));
    const person = document.createElement("td");
    const personWrap = document.createElement("button");
    personWrap.type = "button";
    personWrap.className = "crew-person crew-profile-button";
    personWrap.setAttribute("aria-label", `Open health report for ${crew.full_name}`);
    personWrap.addEventListener("click", () => openCrewProfile(crew.id));
    const avatar = document.createElement("span");
    avatar.className = "avatar crew-avatar avatar-teal";
    avatar.textContent = initials;
    applyCrewPortrait(avatar, crew.id, crew.full_name);
    const details = document.createElement("span");
    const name = document.createElement("strong");
    const role = document.createElement("small");
    details.append(name, role);
    personWrap.append(avatar, details);
    person.append(personWrap);
    name.textContent = crew.full_name;
    role.textContent = crew.role;
    row.append(person);

    const statusCell = document.createElement("td");
    const status = document.createElement("span");
    status.className = `status-pill ${needsReview ? "watch" : "good"}`;
    status.innerHTML = "<i></i>";
    status.append(document.createTextNode(needsReview ? " REVIEW" : " STABLE"));
    statusCell.append(status);
    row.append(statusCell);

    const scoreCell = document.createElement("td");
    scoreCell.innerHTML = '<strong class="score-number"></strong><span class="score-denom"> / 100</span>';
    scoreCell.querySelector("strong").textContent = crew.health_score;
    row.append(scoreCell);
    const values = [
      hr == null ? "—" : `${Math.round(hr)} bpm`,
      oxygen == null ? "—" : `${Math.round(oxygen)}%`,
      systolic == null || diastolic == null ? "—" : `${Math.round(systolic)}/${Math.round(diastolic)}`,
      hrv == null ? "—" : `${Math.round(hrv)} ms`,
      temperature == null ? "—" : `${Number(temperature).toFixed(1)}°`,
      sleep == null ? "—" : `${Number(sleep).toFixed(1)} hrs`,
      exercise == null ? "—" : `${Math.round(exercise)} min`,
      crew.latest_checkin ? `Today, ${new Date(crew.latest_checkin.recorded_at).toISOString().slice(11, 16)}` : "No check-in",
    ];
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = value;
      if (needsReview && value === `${Number(sleep).toFixed(1)} hrs`) cell.classList.add("table-watch");
      row.append(cell);
    }
    const actions = document.createElement("td");
    const button = document.createElement("button");
    button.className = "row-arrow";
    button.type = "button";
    button.dataset.crew = crew.full_name;
    button.setAttribute("aria-label", `View ${crew.full_name}`);
    button.textContent = "↗";
    button.addEventListener("click", () => openCrewProfile(crew.id));
    actions.append(button);
    row.append(actions);
    tbody.append(row);
  }
}

async function loadBackendData() {
  try {
    const [mission, crews] = await Promise.all([
      apiRequest("/api/mission"),
      apiRequest("/api/crew"),
    ]);
    if (!Array.isArray(crews) || crews.length === 0) {
      throw new Error("No crew records were returned by the database.");
    }
    crewCatalog = crews;
    populateCrewPicker(crews);
    reviewSignals = buildReviewSignals(crews);
    renderAlertsView();
    renderControlFocus(reviewSignals);
    currentCrew = crews.find((crew) => crew.id === currentCrewId) ?? crews[0];
    currentCrewId = currentCrew.id;
    document.getElementById("crew-picker").value = currentCrewId;
    document.getElementById("health-score-name").textContent =
      currentCrew.full_name.split(/\s+/)[0];
    const initials = currentCrew.full_name
      .split(/\s+/)
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
    document.querySelector(".user-card").setAttribute(
      "aria-label",
      `Current user: ${currentCrew.full_name}`,
    );
    document.querySelector(".user-card .avatar").textContent = initials;
    document.querySelector(".user-card strong").textContent = currentCrew.full_name;
    document.querySelector(".user-card small").textContent = currentCrew.role;
    document.querySelector(".topbar-actions > .avatar").textContent = initials;
    updateSelectedCrewPortraits(currentCrew);
    for (const key of [
      "resting_heart_rate", "blood_oxygen", "sleep_duration", "exercise_minutes",
      "heart_rate_variability", "blood_pressure", "body_temperature",
      "hydration_liters", "stress_score", "bone_loading_minutes",
    ]) {
      const measurement = key === "blood_pressure"
        ? metricValue(currentCrew, "systolic_blood_pressure")
        : metricValue(currentCrew, key);
      renderIndicator(key, measurement);
    }
    renderRangeSummary();
    const historyMetrics = [
      "resting_heart_rate", "blood_oxygen", "sleep_duration", "exercise_minutes",
      "heart_rate_variability", "systolic_blood_pressure", "body_temperature",
      "hydration_liters", "stress_score", "bone_loading_minutes",
    ];
    const histories = await Promise.all(historyMetrics.map(async (metric) => [
      metric,
      await apiRequest(`/api/crew/${currentCrewId}/measurements?metric=${encodeURIComponent(metric)}&limit=8`),
    ]));
    for (const [metric, records] of histories) {
      renderIndicatorSparkline(metric === "systolic_blood_pressure" ? "blood_pressure" : metric, records);
    }
    const sleepHistory = histories.find(([metric]) => metric === "sleep_duration")?.[1] ?? [];
    renderSleepPattern(sleepHistory);
    const latestCheckin = currentCrew.latest_checkin;
    const selfReportCard = document.querySelector(".indicator-card[data-self-report]");
    if (latestCheckin && selfReportCard) {
      const mood = latestCheckin.mood;
      selfReportCard.querySelector(".indicator-value").textContent = mood;
      const status = selfReportCard.querySelector(".status-pill");
      status.classList.toggle("watch", mood.toLowerCase() === "low");
      status.classList.toggle("good", mood.toLowerCase() !== "low");
      status.innerHTML = `<i></i> ${mood.toUpperCase()} MOOD`;
    }
    document.querySelector(".crew-total").innerHTML = `${crews.length} CREW MEMBERS <i></i>`;
    document.querySelector(".nav-count").textContent = crews.length;
    document.getElementById("crew-total-count").textContent = crews.length;
    const reviewCrewIds = new Set(reviewSignals.filter(s => s.type === "review").map(s => s.crew.id));
    document.getElementById("crew-in-range-count").textContent =
      crews.filter(crew => !reviewCrewIds.has(crew.id)).length;
    document.getElementById("pattern-count").textContent = reviewCrewIds.size;
    document.getElementById("mission-name").textContent = mission.name;
    document.getElementById("breadcrumb-mission").textContent = mission.name;
    document.getElementById("mission-day").textContent = String(mission.mission_day).padStart(3, "0");
    for (const id of ["timeline-mission-day", "control-mission-day", "checkin-mission-day"]) {
      document.getElementById(id).textContent = String(mission.mission_day).padStart(3, "0");
    }
    document.getElementById("mission-phase").textContent = `${mission.phase} · Day ${String(mission.mission_day).padStart(3, "0")}`;
    document.getElementById("control-mission-phase").textContent = `${mission.phase} phase · ${mission.name}`;
    document.getElementById("radiation-context").innerHTML = `${mission.radiation_context} <small>mission context · illustrative</small>`;
    renderCrewTable(crews);
    // The overview and timeline show only the currently selected fictional astronaut.
    const displayName = currentCrew.full_name;
    const $ = (id) => document.getElementById(id);
    if ($("hero-crew-name")) $("hero-crew-name").textContent=displayName;
    if ($("current-crew-name")) $("current-crew-name").firstChild.textContent=displayName+" ";
    if ($("portrait-name")) $("portrait-name").textContent=displayName+" · simulated crew";
    const fmt = (metric, digits=0) => {const m=currentCrew.latest_measurements?.[metric];return m ? Number(m.value).toFixed(digits)+" "+m.unit : "—"};
    if ($("timeline-quick-hr")) $("timeline-quick-hr").textContent=fmt("resting_heart_rate");
    if ($("timeline-quick-oxygen")) $("timeline-quick-oxygen").textContent=fmt("blood_oxygen");
    if ($("timeline-quick-sleep")) $("timeline-quick-sleep").textContent=fmt("sleep_duration",1);
    if ($("timeline-quick-temp")) $("timeline-quick-temp").textContent=fmt("body_temperature",1);
    renderCrewRoster(crews);

    startSimulatedHeartRate(currentCrew.latest_measurements?.resting_heart_rate?.value);
    setChartMetric(activeChartMetric);
    await loadMetricHistory(activeChartMetric);
    if (latestCheckin) {
      document.getElementById("checkin-timestamp").textContent =
        `Today · ${new Date(latestCheckin.recorded_at).toISOString().slice(11, 16)} UTC`;
      document.getElementById("checkin-energy").textContent = `${latestCheckin.energy} / 5`;
      document.getElementById("checkin-stress").textContent = `${latestCheckin.stress} / 5`;
      document.getElementById("checkin-mood").textContent = latestCheckin.mood;
      document.getElementById("checkin-sleep").textContent = `${Number(latestCheckin.sleep_hours).toFixed(1)} hrs`;
      // Never overwrite values while a user is actively editing the open dialog.
      if (!checkinDialog.open) {
        document.getElementById("energy").value = latestCheckin.energy;
        document.getElementById("stress").value = latestCheckin.stress;
        document.getElementById("mood").value = latestCheckin.mood;
        document.getElementById("sleep-hours").value = latestCheckin.sleep_hours;
        document.querySelectorAll(".range-control input").forEach((range) => {
          range.parentElement.querySelector("output").value = range.value;
        });
      }
    }
    setApiStatus(true);
  } catch (error) {
    setApiStatus(false, error.message);
  }
}

function startSimulatedHeartRate(startValue) {
  if (!Number.isFinite(startValue)) return;
  window.clearInterval(simulatedHeartRateTimer);
  const sequence = [0, 1, 2, 1, 0, -1, 1, 3, 2, 0, -2, -1, 0, 2, 1, 0];
  const value = document.getElementById("heart-rate-live-value");
  const heart = document.querySelector('.indicator-card[data-metric="resting_heart_rate"] .indicator-icon');
  if (!value || !heart) return;
  let index = 0;
  const update = () => {
    const bpm = Math.max(45, Math.round(startValue + sequence[index]));
    value.textContent = bpm;
    value.setAttribute("aria-label", `${bpm} beats per minute, simulated`);
    heart.style.setProperty("--beat-duration", `${60 / bpm}s`);
    index = (index + 1) % sequence.length;
  };
  update();
  simulatedHeartRateTimer = window.setInterval(update, 2200);
}

function updateClock() {
  const now = new Date();
  document.getElementById("mission-time").textContent = `${now.toISOString().slice(11, 19)} UTC`;
}

updateClock();
window.setInterval(updateClock, 1000);
let activeDemoDate = new Date().toISOString().slice(0, 10);
async function refreshForNewDemoDay() {
  const today = new Date().toISOString().slice(0, 10);
  if (today === activeDemoDate) return;
  activeDemoDate = today;
  await loadBackendData();
  await loadSpacecraftHistory();
}

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refreshForNewDemoDay();
});
window.setInterval(refreshForNewDemoDay, 60_000);
loadBackendData().then(loadSpacecraftHistory);
loadResearchData();


// ---- Six-page experience: explicit crew context, detailed profiles, review signals ----
function populateCrewPicker(crews) {
  const picker = document.getElementById("crew-picker");
  const names = crews.map(c => c.id).join("|");
  if (picker.dataset.items === names) return;
  picker.dataset.items = names;
  picker.replaceChildren();
  for (const crew of crews) {
    const opt = document.createElement("option"); opt.value = crew.id;
    opt.textContent = `${crew.full_name} · ${crew.role}`;
    picker.append(opt);
  }
}
document.getElementById("crew-picker").addEventListener("change", async event => {
  currentCrewId = event.target.value;
  await loadBackendData();
});
document.getElementById("overview-full-report").addEventListener("click", () => openCrewProfile(currentCrewId));
document.getElementById("back-to-crew").addEventListener("click", () => showView("control"));
document.getElementById("profile-timeline-link").addEventListener("click", async () => {
  currentCrewId = currentProfileId ?? currentCrewId;
  await loadBackendData();
  showView("timeline");
});
document.getElementById("open-alerts").addEventListener("click", () => showView("alerts"));

const profileMetricLabels = {
  resting_heart_rate: "Resting heart rate", blood_oxygen: "Blood oxygen", sleep_duration:"Sleep duration",
  exercise_minutes:"Exercise", heart_rate_variability:"Heart-rate variability", systolic_blood_pressure:"Systolic blood pressure",
  diastolic_blood_pressure:"Diastolic blood pressure", body_temperature:"Body temperature", hydration_liters:"Hydration",
  stress_score:"Stress check-in", bone_loading_minutes:"Bone-loading exercise"
};
const profileMetricIcons = {resting_heart_rate:"♡",blood_oxygen:"◉",sleep_duration:"☾",exercise_minutes:"↗",heart_rate_variability:"⌁",systolic_blood_pressure:"◈",diastolic_blood_pressure:"◈",body_temperature:"♧",hydration_liters:"◌",stress_score:"◇",bone_loading_minutes:"✦"};
function latestRangeStatus(m) { return m && Number.isFinite(m.value) && Number.isFinite(m.baseline_min) && Number.isFinite(m.baseline_max) && m.value >= m.baseline_min && m.value <= m.baseline_max; }
function fullUTC(s) { try { return new Date(s).toLocaleString("en-GB",{timeZone:"UTC",day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit"})+" UTC"; }catch{return String(s || "Unknown time");} }

async function openCrewProfile(id) {
  if (!id) return;
  currentProfileId = id;
  showView("profile");
  const card = document.getElementById("profile-metrics");
  card.textContent = "Loading individual readings…";
  try {
    const person = await apiRequest(`/api/crew/${encodeURIComponent(id)}`);
    if (currentProfileId !== id) return;
    // Clicking a crew profile also selects that astronaut for the whole dashboard.
    currentCrewId = id;
    await loadBackendData();
    if (currentProfileId !== id) return;
    document.getElementById("profile-name").textContent = person.full_name;
    document.getElementById("profile-identity-name").textContent = person.full_name;
    document.getElementById("profile-role").textContent = `${person.role} · personal demo readings`;
    document.getElementById("profile-identity-role").textContent = person.role;
    document.getElementById("profile-avatar").textContent = person.full_name.split(/\s+/).map(x=>x[0]).join("").slice(0,2).toUpperCase();
    applyCrewPortrait(document.getElementById("profile-avatar"), person.id, person.full_name);
    const records = person.latest_measurements ?? {};
    const keys = Object.keys(profileMetricLabels).filter(k=>records[k]);
    document.getElementById("profile-indicator-count").textContent = String(keys.length);
    document.getElementById("profile-range-count").textContent = `${keys.filter(k=>latestRangeStatus(records[k])).length} / ${keys.length}`;
    card.replaceChildren();
    for (const key of keys) {
      const m = records[key]; const ok = latestRangeStatus(m);
      const el = document.createElement("article"); el.className = "panel profile-metric-card";
      const head = document.createElement("div");head.className="profile-metric-top";
      const icon = document.createElement("span");icon.className="profile-metric-icon";icon.textContent=profileMetricIcons[key]??"◈";
      const title = document.createElement("span");title.textContent=profileMetricLabels[key];head.append(icon,title);
      const value = document.createElement("strong");value.textContent=`${Number(m.value.toFixed(2))} ${m.unit}`;
      const foot = document.createElement("p");foot.textContent=`Demo range ${m.baseline_min}–${m.baseline_max} ${m.unit} · ${ok?"In range":"Review"}`;
      const source = document.createElement("small");source.textContent=`${m.source} · ${fullUTC(m.recorded_at)}`;
      el.append(head,value,foot,source);card.append(el);
    }
    const select=document.getElementById("profile-metric");select.replaceChildren();
    for(const key of keys){const opt=document.createElement("option");opt.value=key;opt.textContent=profileMetricLabels[key];select.append(opt)}
    select.value=keys.includes("resting_heart_rate")?"resting_heart_rate":(keys[0]??"");
    if (select.value) await loadProfileTrend(id,select.value);
    const checkins = await apiRequest(`/api/crew/${encodeURIComponent(id)}/checkins?limit=6`);
    const log=document.getElementById("profile-checkin-list");log.replaceChildren();
    if (!checkins.length) log.textContent="No check-ins have been saved for this crew member.";
    for(const c of checkins){const item=document.createElement("div");item.className="profile-checkin-row";
      const date=document.createElement("span");date.textContent=fullUTC(c.recorded_at);
      const status=document.createElement("strong");status.textContent=`${c.mood} · energy ${c.energy}/5 · stress ${c.stress}/5`;
      const foot=document.createElement("small");foot.textContent=`Sleep ${c.sleep_hours} hours · ${c.source}`;
      item.append(date,status,foot);log.append(item);
    }
  } catch(error){card.textContent=`Could not load this profile: ${error.message}`;}
}

document.getElementById("profile-metric").addEventListener("change",event=>loadProfileTrend(currentProfileId,event.target.value));
async function loadProfileTrend(id,key){
  const el=document.getElementById("profile-history-chart");el.textContent="Loading trend…";
  try {
    const pts=(await apiRequest(`/api/crew/${encodeURIComponent(id)}/measurements?metric=${encodeURIComponent(key)}&daily=true&limit=30`)).reverse();
    if (id!==currentProfileId || document.getElementById("profile-metric").value!==key) return;
    document.getElementById("profile-trend-title").textContent=profileMetricLabels[key];el.replaceChildren();
    if(pts.length<2){el.textContent="Not enough data to show a trend.";return;}
    const vals=pts.map(p=>p.value);const lo=Math.min(...vals,...pts.map(p=>p.baseline_min)),hi=Math.max(...vals,...pts.map(p=>p.baseline_max));
    const pad=(hi-lo)*.18 || 1;const bot=lo-pad, top=hi+pad;
    const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");svg.setAttribute("viewBox","0 0 700 230");svg.setAttribute("role","img");svg.setAttribute("aria-label",`${profileMetricLabels[key]} readings over ${pts.length} days`);
    for(const y of [26,82,138,194]){const line=document.createElementNS(svg.namespaceURI,"line");Object.entries({x1:"24",y1:String(y),x2:"682",y2:String(y),stroke:"#293d54","stroke-width":"1"}).forEach(([k,v])=>line.setAttribute(k,v));svg.append(line);}
    const xy=pts.map((p,i)=>[24+(i/(pts.length-1))*658,201-(p.value-bot)/(top-bot)*160]);
    const path=document.createElementNS(svg.namespaceURI,"path");path.setAttribute("d",xy.map(([x,y],i)=>`${i?'L':'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(" "));path.setAttribute("fill","none");path.setAttribute("stroke","#edbd6d");path.setAttribute("stroke-width","3");path.setAttribute("stroke-linecap","round");svg.append(path);
    for(const [i,[x,y]] of xy.entries()){if(i%5!==0&&i!==xy.length-1)continue;const dot=document.createElementNS(svg.namespaceURI,"circle");dot.setAttribute("cx",String(x));dot.setAttribute("cy",String(y));dot.setAttribute("r",i===xy.length-1?"5":"3");dot.setAttribute("fill","#edbd6d");const title=document.createElementNS(svg.namespaceURI,"title");title.textContent=`${pts[i].recorded_at.slice(0,10)} · ${pts[i].value} ${pts[i].unit}`;dot.append(title);svg.append(dot);}
    el.append(svg);const legend=document.createElement("div");legend.className="profile-chart-legend";legend.textContent=`${pts.length} saved daily readings · latest ${pts.at(-1).value} ${pts.at(-1).unit} · ${fullUTC(pts.at(-1).recorded_at)}`;el.append(legend);
  }catch(e){el.textContent=`History not available: ${e.message}`;}
}

function buildReviewSignals(crews){
  const signals=[];
  for(const c of crews){
    const m=c.latest_measurements ?? {};
    for(const [key,label] of Object.entries(profileMetricLabels)) {
      const reading=m[key];
      if(!reading){signals.push({type:"missing",crew:c,metric:key,label,reading:null});continue;}
      if(!latestRangeStatus(reading)) signals.push({type:"review",crew:c,metric:key,label,reading});
    }
  }
  return signals.sort((a,b)=>a.crew.full_name.localeCompare(b.crew.full_name));
}
function renderAlertsView() {
  const totalEl=document.getElementById("alert-count-total");
  if(totalEl)totalEl.textContent=String(reviewSignals.length);
  const list=document.getElementById("alert-list"); if(!list)return;
  const countReview=reviewSignals.filter(x=>x.type==="review").length;
  document.getElementById("alert-count-review").textContent=countReview;
  document.getElementById("alert-count-missing").textContent=reviewSignals.filter(x=>x.type==="missing").length;
  document.getElementById("alert-count-crew").textContent=crewCatalog.length||"—";
  const badge=document.getElementById("nav-alert-count");badge.textContent=countReview||"0";
  badge.hidden=countReview===0;
  document.querySelectorAll(".alert-filter").forEach(btn=>btn.classList.toggle("active",btn.dataset.filter===selectedAlertFilter));
  list.replaceChildren();
  const active=reviewSignals.filter(s=>selectedAlertFilter==="all"||s.type===selectedAlertFilter);
  if(!crewCatalog.length){list.innerHTML='<p class="empty-message">Crew records are unavailable. Check the API connection.</p>';return;}
  if(!active.length){list.innerHTML='<p class="empty-message">No matching signals from the latest saved demo readings.</p>';document.getElementById("alert-inspector").innerHTML='<span class="eyebrow">RECORD INSPECTOR</span><h2>No open signals</h2><p>Nothing matches this filter.</p>';return;}
  for(const s of active){const b=document.createElement("button");b.type="button";b.className="alert-row";
    const glyph=document.createElement("span");glyph.className=`alert-row-icon ${s.type}`;glyph.textContent=s.type==="review"?"!":"?";
    const body=document.createElement("span");body.className="alert-row-copy";
    const title=document.createElement("strong");title.textContent=s.type==="review"?`${s.label} · outside demo range`:`${s.label} · not reported`;
    const sub=document.createElement("small");sub.textContent=`${s.crew.full_name} · ${s.reading?fullUTC(s.reading.recorded_at):"No saved value"}`;
    body.append(title,sub);const arrow=document.createElement("span");arrow.textContent="↗";b.append(glyph,body,arrow);
    b.addEventListener("click",()=>{document.querySelectorAll(".alert-row").forEach(x=>x.classList.remove("selected"));b.classList.add("selected");inspectReviewSignal(s)});list.append(b);
  }
  const selected=list.firstElementChild;if(selected)selected.click();
}
function inspectReviewSignal(signal){
  const root=document.getElementById("alert-inspector");root.replaceChildren();
  const add=(tag,txt,cls)=>{const el=document.createElement(tag);if(cls)el.className=cls;el.textContent=txt;root.append(el);return el};
  add("span","EVIDENCE / RECORD INSPECTOR","eyebrow");add("h2",signal.label);add("p",signal.crew.full_name+" · "+signal.crew.role);
  if(signal.reading){const m=signal.reading;
    add("div",`${Number(m.value.toFixed(2))} ${m.unit}`,"alert-inspector-value");
    add("p",`Configured demo range: ${m.baseline_min}–${m.baseline_max} ${m.unit}`);
    add("p",`Recorded: ${fullUTC(m.recorded_at)}`);
    add("p",`Source: ${m.source} · endpoint /api/crew/${signal.crew.id}`);
    add("p","This is a numerical range comparison, not evidence of disease or an emergency.","alert-inspector-note");
  }else{add("p","No saved reading is available for this metric; no medical conclusion can be drawn.");}
  const btn=document.createElement("button");btn.className="primary-button";btn.textContent="Open crew profile ↗";btn.addEventListener("click",()=>openCrewProfile(signal.crew.id));root.append(btn);
}
document.querySelectorAll(".alert-filter").forEach(btn=>btn.addEventListener("click",()=>{selectedAlertFilter=btn.dataset.filter;renderAlertsView()}));

// Presentation-friendly crew roster; the detailed table remains available below.
function renderCrewRoster(crews) {
  const list=document.getElementById("crew-roster");
  if(!list) return;
  list.replaceChildren();
  for(const crew of crews){
    const b=document.createElement("button");b.type="button";b.className="roster-person";
    const vals=Object.values(crew.latest_measurements||{});
    const flagged=vals.some(m => m && !(m.value>=m.baseline_min && m.value<=m.baseline_max));
    const initials=crew.full_name.split(/\s+/).map(x=>x[0]).join("").slice(0,2).toUpperCase();
    const photo=document.createElement("span");photo.className="roster-avatar";photo.textContent=initials;applyCrewPortrait(photo,crew.id,crew.full_name);
    const info=document.createElement("span");info.className="roster-info";
    const nm=document.createElement("strong");nm.textContent=crew.full_name;
    const role=document.createElement("small");role.textContent=crew.role;info.append(nm,role);
    const flag=document.createElement("span");flag.className=`roster-badge ${flagged?"review":"ok"}`;
    flag.textContent=flagged?"Review":"In range";b.append(photo,info,flag);
    b.setAttribute("aria-label",`Open ${crew.full_name} individual health report`);
    b.addEventListener("click",()=>openCrewProfile(crew.id));list.append(b);
  }
}
for(const id of ["portrait-full-report","health-metrics-report"]) {
 const b=document.getElementById(id);
 if(b) b.addEventListener("click",()=>openCrewProfile(currentCrewId));
}

// Mission Control: turn the restored cinematic panel into a useful data-backed summary.
function renderControlFocus(signals) {
  const heading = document.getElementById("control-focus-heading");
  const description = document.getElementById("control-focus-description");
  if (!heading || !description) return;
  const flagged = signals.find((signal) => signal.type === "review");
  const missing = signals.find((signal) => signal.type === "missing");
  if (flagged) {
    heading.textContent = `${flagged.crew.full_name} · pattern to review`;
    const reading = flagged.reading;
    description.textContent = `${flagged.label}: ${reading.value} ${reading.unit}, compared with the configured demo range (${reading.baseline_min}–${reading.baseline_max} ${reading.unit}). Open Alerts for source details.`;
  } else if (missing) {
    heading.textContent = "A saved measurement is missing";
    description.textContent = `${missing.crew.full_name} · ${missing.label}. Review the locally saved observations in Alerts.`;
  } else {
    heading.textContent = "Crew measurements in demo range";
    description.textContent = "All available measurements fall inside their configured demonstration ranges. No live medical or spacecraft feed is connected.";
  }
}

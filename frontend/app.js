const form = document.querySelector("#search-form");
const queryInput = document.querySelector("#q");
const providerSelect = document.querySelector("#provider");
const qualitySelect = document.querySelector("#quality");
const durationSelect = document.querySelector("#duration");
const resultsEl = document.querySelector("#results");
const statusEl = document.querySelector("#status");
const clearBtn = document.querySelector("#clear");
const moreBtn = document.querySelector("#more");
const template = document.querySelector("#card-template");

const PAGE_SIZE = 40;
let nextOffset = 0;

function durationText(seconds) {
  if (!Number.isFinite(seconds)) return "";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

async function loadProviders() {
  try {
    const response = await fetch("/api/providers");
    if (!response.ok) return;
    const data = await response.json();
    for (const provider of data.providers || []) {
      const option = document.createElement("option");
      option.value = provider;
      option.textContent = provider;
      providerSelect.append(option);
    }
  } catch (_) {}
}

function buildSearchParams() {
  const params = new URLSearchParams();
  const query = queryInput.value.trim();
  if (query) params.set("q", query);

  if (providerSelect.value) params.set("provider", providerSelect.value);
  if (qualitySelect.value) params.set("quality", qualitySelect.value);

  if (durationSelect.value) {
    const [min, max] = durationSelect.value.split(":");
    if (min) params.set("min_duration", min);
    if (max) params.set("max_duration", max);
  }

  return params;
}

function persistState(params) {
  const query = params.toString();
  const next = query ? `${window.location.pathname}#${query}` : window.location.pathname;
  window.history.replaceState(null, "", next);
}

function restoreState() {
  const rawState = window.location.hash
    ? window.location.hash.slice(1)
    : window.location.search.slice(1);
  const params = new URLSearchParams(rawState);
  queryInput.value = params.get("q") || "";

  const provider = params.get("provider") || "";
  if ([...providerSelect.options].some((option) => option.value === provider)) {
    providerSelect.value = provider;
  }

  const quality = params.get("quality") || "";
  if ([...qualitySelect.options].some((option) => option.value === quality)) {
    qualitySelect.value = quality;
  }

  const min = params.get("min_duration") || "";
  const max = params.get("max_duration") || "";
  const duration = `${min}:${max}`;
  if ([...durationSelect.options].some((option) => option.value === duration)) {
    durationSelect.value = duration;
  }

  return [...params.keys()].length > 0;
}

function resultCard(item) {
  const card = template.content.firstElementChild.cloneNode(true);
  const thumb = card.querySelector(".thumb");
  const title = card.querySelector(".title");
  const preview = card.querySelector(".preview");
  const placeholder = card.querySelector(".placeholder");

  thumb.href = item.url;
  title.href = item.url;

  if (item.thumbnail) {
    preview.src = item.thumbnail;
    preview.hidden = false;
    placeholder.hidden = true;
    preview.addEventListener("error", () => {
      preview.hidden = true;
      placeholder.hidden = false;
    }, { once: true });
  }

  title.textContent = item.title;
  card.querySelector(".source").textContent = item.provider;
  card.querySelector(".quality").textContent = item.quality || "";
  card.querySelector(".duration").textContent = durationText(item.duration_seconds);

  const count = item.alternate_sources?.length || 0;
  card.querySelector(".alternates").textContent =
    count ? `+${count} source${count === 1 ? "" : "s"}` : "";

  return card;
}

function render(items, { append = false } = {}) {
  if (!append) resultsEl.replaceChildren();

  if (!items.length && !append) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No results";
    resultsEl.append(empty);
    return;
  }

  for (const item of items) {
    resultsEl.append(resultCard(item));
  }
}

async function search({ persist = true, append = false } = {}) {
  const stateParams = buildSearchParams();
  if (persist) persistState(stateParams);

  const offset = append ? nextOffset : 0;
  const payload = {
    q: stateParams.get("q") || "",
    offset,
    limit: PAGE_SIZE,
  };
  if (stateParams.has("provider")) payload.provider = stateParams.get("provider");
  if (stateParams.has("quality")) payload.quality = stateParams.get("quality");
  if (stateParams.has("min_duration")) {
    payload.min_duration = Number(stateParams.get("min_duration"));
  }
  if (stateParams.has("max_duration")) {
    payload.max_duration = Number(stateParams.get("max_duration"));
  }

  if (!append) {
    nextOffset = 0;
    moreBtn.hidden = true;
  }
  moreBtn.disabled = true;
  statusEl.textContent = append ? "Loading more…" : "Searching…";

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Search failed");

    const items = data.items || [];
    render(items, { append });

    nextOffset = offset + items.length;
    moreBtn.hidden = !data.has_more;
    moreBtn.disabled = false;

    statusEl.textContent =
      `${nextOffset} shown · ${data.providers.join(", ") || "no provider"}`;
  } catch (error) {
    if (!append) resultsEl.replaceChildren();
    moreBtn.hidden = true;
    moreBtn.disabled = false;
    statusEl.textContent = error.message || "Search failed";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  search();
});

for (const el of [providerSelect, qualitySelect, durationSelect]) {
  el.addEventListener("change", () => search());
}

moreBtn.addEventListener("click", () => {
  search({ persist: false, append: true });
});

clearBtn.addEventListener("click", () => {
  queryInput.value = "";
  providerSelect.value = "";
  qualitySelect.value = "";
  durationSelect.value = "";
  resultsEl.replaceChildren();
  nextOffset = 0;
  moreBtn.hidden = true;
  statusEl.textContent = "Ready";
  persistState(new URLSearchParams());
  queryInput.focus();
});

async function boot() {
  await loadProviders();
  const restored = restoreState();
  if (restored) {
    await search({ persist: false });
  }
}

boot();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () =>
    navigator.serviceWorker.register("/sw.js").catch(() => {})
  );
}

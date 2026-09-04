const form = document.querySelector("#search-form");
const queryInput = document.querySelector("#q");
const providerSelect = document.querySelector("#provider");
const qualitySelect = document.querySelector("#quality");
const durationSelect = document.querySelector("#duration");
const ageCheckSelect = document.querySelector("#age-check");
const resultsEl = document.querySelector("#results");
const statusEl = document.querySelector("#status");
const clearBtn = document.querySelector("#clear");
const moreBtn = document.querySelector("#more");
const template = document.querySelector("#card-template");

const PAGE_SIZE = 40;
let nextOffset = 0;
let searchGeneration = 0;
let seenIds = new Set();
let livePage = 0;
let liveHasMore = false;
let liveStatusText = "";
let localHasMore = false;
let prefetchedPage = null;
let prefetchPromise = null;
let activeMotionPreview = null;

function setPreviewToggle(toggle, playing) {
  if (!toggle) return;
  toggle.textContent = playing ? "■" : "▶";
  toggle.setAttribute("aria-label", playing ? "Stop preview" : "Play preview");
  toggle.setAttribute("aria-pressed", playing ? "true" : "false");
}

function stopMotionPreview(motion, still, toggle) {
  if (!motion) return;
  motion.pause();
  motion.hidden = true;
  if (still?.src) still.hidden = false;
  setPreviewToggle(toggle, false);
  if (activeMotionPreview?.motion === motion) activeMotionPreview = null;
}

function startMotionPreview(motion, still, url, toggle) {
  if (!motion || !url) return;
  if (activeMotionPreview?.motion && activeMotionPreview.motion !== motion) {
    stopMotionPreview(
      activeMotionPreview.motion,
      activeMotionPreview.still,
      activeMotionPreview.toggle,
    );
  }
  if (!motion.src) motion.src = url;
  motion.hidden = false;
  if (still) still.hidden = true;
  activeMotionPreview = { motion, still, toggle };
  motion.play().then(() => setPreviewToggle(toggle, true)).catch(() => {
    stopMotionPreview(motion, still, toggle);
  });
}

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
  if (ageCheckSelect.value) params.set("age_check", ageCheckSelect.value);

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

  const ageCheck = params.get("age_check") || "";
  if ([...ageCheckSelect.options].some((option) => option.value === ageCheck)) {
    ageCheckSelect.value = ageCheck;
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
  const motion = card.querySelector(".motion-preview");
  const placeholder = card.querySelector(".placeholder");
  const previewToggle = card.querySelector(".preview-toggle");

  thumb.href = item.url;
  title.href = item.url;

  if (item.thumbnail) {
    const resolvedThumb = item.thumbnail;
    preview.src = resolvedThumb;
    preview.hidden = false;
    placeholder.hidden = true;

    preview.addEventListener("error", () => {
      preview.hidden = true;
      placeholder.hidden = false;
    });
  }

  if (item.preview_url) {
    motion.dataset.previewUrl = item.preview_url;
    motion.preload = "none";
    motion.referrerPolicy = "no-referrer";
    if (item.thumbnail) motion.poster = preview.src;
    previewToggle.hidden = false;
    setPreviewToggle(previewToggle, false);
    motion.addEventListener("error", () => stopMotionPreview(motion, preview, previewToggle));
    previewToggle.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (activeMotionPreview?.motion === motion && !motion.paused) {
        stopMotionPreview(motion, preview, previewToggle);
      } else {
        startMotionPreview(motion, preview, item.preview_url, previewToggle);
      }
    });
  } else {
    previewToggle.hidden = true;
  }

  title.textContent = item.title;
  card.querySelector(".source").textContent = `✓ ${item.provider}`;
  card.querySelector(".age-check").textContent =
    item.age_check_status === "required"
      ? "18+ check (UK)"
      : item.age_check_status === "not_required"
        ? "no age check observed"
        : "";
  card.querySelector(".quality").textContent = item.quality || "";
  card.querySelector(".duration").textContent = durationText(item.duration_seconds);

  const count = item.alternate_sources?.length || 0;
  card.querySelector(".alternates").textContent =
    count ? `+${count} source${count === 1 ? "" : "s"}` : "";

  return card;
}

function render(items, { append = false } = {}) {
  if (!append) {
    resultsEl.replaceChildren();
    seenIds = new Set();
  }

  let added = 0;
  for (const item of items) {
    if (!item?.id || seenIds.has(item.id)) continue;
    seenIds.add(item.id);
    resultsEl.append(resultCard(item));
    added += 1;
  }

  if (!seenIds.size && !append) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No results";
    resultsEl.append(empty);
  }
  nextOffset = seenIds.size;
  return added;
}

function liveSummary(providers) {
  const parts = [];
  for (const item of providers || []) {
    if (item.error) continue;
    if (Number.isFinite(item.total)) {
      parts.push(`${item.provider} ${item.total.toLocaleString()}`);
    } else if (item.fetched) {
      parts.push(`${item.provider} +${item.fetched}`);
    }
  }
  return parts.join(" · ");
}

function upstreamHasMore(live, requestedLimit) {
  return (live.providers || []).some((item) => {
    if (item.error || !item.fetched) return false;
    if (Number.isFinite(item.total)) {
      return item.page * requestedLimit < item.total;
    }
    return item.fetched >= requestedLimit;
  });
}

function applyLiveState(live, page, requestedLimit = 24) {
  livePage = page;
  liveHasMore = upstreamHasMore(live, requestedLimit);
  liveStatusText = liveSummary(live.providers);
}

async function requestLive(payload, generation, page, { commit = true } = {}) {
  const requestedLimit = 24;
  const livePayload = {
    q: payload.q,
    page,
    limit_per_provider: requestedLimit,
  };
  if (payload.provider) livePayload.provider = payload.provider;
  if (payload.quality) livePayload.quality = payload.quality;
  if (payload.age_check) livePayload.age_check = payload.age_check;
  if (Number.isFinite(payload.min_duration)) livePayload.min_duration = payload.min_duration;
  if (Number.isFinite(payload.max_duration)) livePayload.max_duration = payload.max_duration;

  const response = await fetch("/api/live-refresh", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
    body: JSON.stringify(livePayload),
  });
  const live = await response.json();
  if (!response.ok) throw new Error(live.detail || "Live refresh failed");
  if (generation !== searchGeneration) return null;

  if (commit) applyLiveState(live, page, requestedLimit);
  return live;
}

function blendLiveAndLocal(liveItems, localItems, limit = PAGE_SIZE) {
  const out = [];
  const ids = new Set();
  let li = 0;
  let ci = 0;
  while (out.length < limit && (li < liveItems.length || ci < localItems.length)) {
    for (const [items, indexName] of [[liveItems, "live"], [localItems, "local"]]) {
      let index = indexName === "live" ? li : ci;
      while (index < items.length && ids.has(items[index]?.id)) index += 1;
      if (index < items.length && out.length < limit) {
        const item = items[index];
        if (item?.id) { ids.add(item.id); out.push(item); }
        index += 1;
      }
      if (indexName === "live") li = index; else ci = index;
    }
  }
  return out;
}

async function fetchLocal(payload, { limit = PAGE_SIZE, excludeSeen = false } = {}) {
  const body = { ...payload, offset: 0, limit };
  if (excludeSeen && seenIds.size) {
    body.exclude_ids = [...seenIds].slice(-800);
  }
  const response = await fetch("/api/search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Search failed");
  return data;
}

async function prepareNextPage(payload, generation) {
  if (generation !== searchGeneration || !(localHasMore || liveHasMore)) return null;

  const nextLivePage = livePage + 1;
  const livePromise = payload.q && liveHasMore
    ? requestLive(payload, generation, nextLivePage, { commit: false }).catch(() => null)
    : Promise.resolve(null);
  const localPromise = localHasMore
    ? fetchLocal(payload, { limit: PAGE_SIZE, excludeSeen: true })
    : Promise.resolve({ items: [], has_more: false });

  const [local, live] = await Promise.all([localPromise, livePromise]);
  if (generation !== searchGeneration) return null;

  const liveItems = (live?.items || []).filter((item) => item?.id && !seenIds.has(item.id));
  const localItems = (local.items || []).filter((item) => item?.id && !seenIds.has(item.id));

  return {
    items: blendLiveAndLocal(liveItems, localItems, PAGE_SIZE),
    localHasMore: Boolean(local.has_more),
    live,
    livePage: nextLivePage,
    requestedLimit: 24,
  };
}

function startPrefetch(payload, generation) {
  prefetchedPage = null;
  if (generation !== searchGeneration || !(localHasMore || liveHasMore)) {
    prefetchPromise = null;
    return;
  }

  prefetchPromise = prepareNextPage(payload, generation)
    .then((page) => {
      if (generation === searchGeneration) prefetchedPage = page;
      return page;
    })
    .catch(() => {
      if (generation === searchGeneration) prefetchedPage = null;
      return null;
    })
    .finally(() => {
      if (generation === searchGeneration) prefetchPromise = null;
    });
}

async function refreshLive(payload, generation) {
  try {
    const live = await requestLive(payload, generation, 1);
    if (!live || generation !== searchGeneration) return;

    const data = await fetchLocal(payload);
    if (generation !== searchGeneration) return;
    const merged = blendLiveAndLocal(live.items || [], data.items || []);
    render(merged);
    localHasMore = Boolean(data.has_more);

    moreBtn.hidden = !(localHasMore || liveHasMore);
    moreBtn.disabled = false;
    const total = Number.isFinite(data.total) ? data.total : nextOffset;
    statusEl.textContent = liveStatusText
      ? `${nextOffset} shown · ${total} cached matches · live: ${liveStatusText}`
      : `${nextOffset} shown · ${total} cached matches`;
    if (!prefetchedPage && !prefetchPromise) startPrefetch(payload, generation);
  } catch (_) {
    if (generation !== searchGeneration) return;
    moreBtn.disabled = false;
    if (!prefetchedPage && !prefetchPromise) startPrefetch(payload, generation);
  }
}

async function loadMore() {
  const generation = searchGeneration;
  const stateParams = buildSearchParams();
  const payload = { q: stateParams.get("q") || "" };
  if (stateParams.has("provider")) payload.provider = stateParams.get("provider");
  if (stateParams.has("quality")) payload.quality = stateParams.get("quality");
  if (stateParams.has("age_check")) payload.age_check = stateParams.get("age_check");
  if (stateParams.has("min_duration")) payload.min_duration = Number(stateParams.get("min_duration"));
  if (stateParams.has("max_duration")) payload.max_duration = Number(stateParams.get("max_duration"));

  moreBtn.disabled = true;
  moreBtn.textContent = prefetchedPage ? "Showing…" : "Loading…";
  statusEl.textContent = prefetchedPage ? "Showing prepared results…" : "Finishing next page…";

  try {
    let page = prefetchedPage;
    if (!page) {
      if (!prefetchPromise) startPrefetch(payload, generation);
      page = prefetchedPage || (prefetchPromise ? await prefetchPromise : null);
    }
    if (!page || generation !== searchGeneration) return;

    prefetchedPage = null;
    prefetchPromise = null;

    if (page.live) {
      applyLiveState(page.live, page.livePage, page.requestedLimit);
    }
    localHasMore = page.localHasMore;

    render(page.items || [], { append: true });

    moreBtn.hidden = !(localHasMore || liveHasMore);
    moreBtn.disabled = false;
    moreBtn.textContent = "Show more";
    statusEl.textContent = liveStatusText
      ? `${nextOffset} shown · live: ${liveStatusText}`
      : `${nextOffset} shown`;

    startPrefetch(payload, generation);
  } catch (error) {
    moreBtn.disabled = false;
    moreBtn.textContent = "Show more";
    statusEl.textContent = error.message || "Loading more failed";
  }
}

async function search({ persist = true, append = false } = {}) {
  if (append) return loadMore();

  const generation = ++searchGeneration;
  const stateParams = buildSearchParams();
  if (persist) persistState(stateParams);

  const payload = { q: stateParams.get("q") || "" };
  if (stateParams.has("provider")) payload.provider = stateParams.get("provider");
  if (stateParams.has("quality")) payload.quality = stateParams.get("quality");
  if (stateParams.has("age_check")) payload.age_check = stateParams.get("age_check");
  if (stateParams.has("min_duration")) payload.min_duration = Number(stateParams.get("min_duration"));
  if (stateParams.has("max_duration")) payload.max_duration = Number(stateParams.get("max_duration"));

  nextOffset = 0;
  seenIds = new Set();
  livePage = 0;
  liveHasMore = false;
  liveStatusText = "";
  localHasMore = false;
  prefetchedPage = null;
  prefetchPromise = null;
  moreBtn.hidden = true;
  moreBtn.disabled = true;
  statusEl.textContent = "Searching…";

  try {
    const data = await fetchLocal(payload);
    if (generation !== searchGeneration) return;
    render(data.items || []);
    localHasMore = Boolean(data.has_more);

    const total = Number.isFinite(data.total) ? data.total : nextOffset;
    startPrefetch(payload, generation);
    const shouldRefreshLive = Boolean(payload.q);
    moreBtn.hidden = !localHasMore;
    moreBtn.disabled = shouldRefreshLive;
    statusEl.textContent = shouldRefreshLive
      ? `${nextOffset} shown · ${total} cached matches · refreshing live…`
      : `${nextOffset} shown · ${total} matches · ${data.providers.join(", ") || "no provider"}`;

    if (shouldRefreshLive) {
      await refreshLive(payload, generation);
    } else {
      moreBtn.disabled = false;
      startPrefetch(payload, generation);
    }
  } catch (error) {
    resultsEl.replaceChildren();
    seenIds = new Set();
    nextOffset = 0;
    moreBtn.hidden = true;
    moreBtn.disabled = false;
    statusEl.textContent = error.message || "Search failed";
  }
}

document.addEventListener("visibilitychange", () => {
  if (document.hidden && activeMotionPreview?.motion) {
    stopMotionPreview(activeMotionPreview.motion, activeMotionPreview.still, activeMotionPreview.toggle);
  }
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  search();
});

for (const el of [providerSelect, qualitySelect, durationSelect, ageCheckSelect]) {
  el.addEventListener("change", () => search());
}

moreBtn.addEventListener("click", () => {
  search({ persist: false, append: true });
});

clearBtn.addEventListener("click", () => {
  searchGeneration += 1;
  queryInput.value = "";
  providerSelect.value = "";
  qualitySelect.value = "";
  durationSelect.value = "";
  ageCheckSelect.value = "";
  resultsEl.replaceChildren();
  seenIds = new Set();
  nextOffset = 0;
  livePage = 0;
  liveHasMore = false;
  liveStatusText = "";
  localHasMore = false;
  prefetchedPage = null;
  prefetchPromise = null;
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
  let reloadingForWorker = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (reloadingForWorker) return;
    reloadingForWorker = true;
    window.location.reload();
  });
  window.addEventListener("load", async () => {
    try {
      const registration = await navigator.serviceWorker.register("/sw.js?v=18", { updateViaCache: "none" });
      await registration.update();
    } catch (_) {}
  });
}

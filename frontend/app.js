const form = document.querySelector("#search-form");
const queryInput = document.querySelector("#q");
const sortSelect = document.querySelector("#sort");
const contentClassInput = document.querySelector("#content-class");
const contentClassButtons = [...document.querySelectorAll("[data-content-class]")];
const providerSelect = document.querySelector("#provider");
const qualitySelect = document.querySelector("#quality");
const durationSelect = document.querySelector("#duration");
const ageCheckSelect = document.querySelector("#age-check");
const resultsEl = document.querySelector("#results");
const statusEl = document.querySelector("#status");
const liveDetailEl = document.querySelector("#live-detail");
const clearBtn = document.querySelector("#clear");
const moreBtn = document.querySelector("#more");
const template = document.querySelector("#card-template");
const filtersOpenBtn = document.querySelector("#filters-open");
const filterSheet = document.querySelector("#filter-sheet");
const filtersCloseBtn = document.querySelector("#filters-close");
const filtersResetBtn = document.querySelector("#filters-reset");
const filtersApplyBtn = document.querySelector("#filters-apply");
const filterCountEl = document.querySelector("#filter-count");
const filterSheetPanel = document.querySelector(".filter-sheet-panel");
let filterSheetOpen = false;

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
let renderedItems = [];
const resolvedPreviewCache = new Map();
const PREVIEW_CACHE_LIMIT = 200;
const fineHoverQuery = window.matchMedia("(hover: hover) and (pointer: fine)");

function setPrimaryStatus(text) {
  statusEl.textContent = text;
}

function setLiveDetail(text) {
  if (!liveDetailEl) return;
  liveDetailEl.textContent = text || "";
}

function openFilterSheet() {
  if (filterSheetOpen) return;
  filterSheetOpen = true;
  filterSheet.hidden = false;
  filtersOpenBtn.setAttribute("aria-expanded", "true");
  document.body.classList.add("filter-sheet-open");
  window.requestAnimationFrame(() => filterSheetPanel.focus());
}

function closeFilterSheet({ returnFocus = true } = {}) {
  if (!filterSheetOpen) return;
  filterSheetOpen = false;
  filterSheet.hidden = true;
  filtersOpenBtn.setAttribute("aria-expanded", "false");
  document.body.classList.remove("filter-sheet-open");
  if (returnFocus) filtersOpenBtn.focus();
}

function activeSecondaryFilterCount() {
  return [providerSelect, qualitySelect, durationSelect, ageCheckSelect]
    .filter((control) => Boolean(control.value))
    .length;
}

function updateFilterCount() {
  const count = activeSecondaryFilterCount();
  filterCountEl.hidden = count === 0;
  filterCountEl.textContent = String(count);
}

function applyFilterSheet() {
  updateFilterCount();
  closeFilterSheet();
  search({ resetScroll: true });
}

function resetSecondaryFilters() {
  providerSelect.value = "";
  qualitySelect.value = "";
  durationSelect.value = "";
  ageCheckSelect.value = "";
  updateFilterCount();
}

function trapFilterSheetFocus(event) {
  if (!filterSheetOpen) return;
  if (event.key === "Escape") {
    event.preventDefault();
    closeFilterSheet();
    return;
  }
  if (event.key !== "Tab") return;
  const focusable = [...filterSheetPanel.querySelectorAll(
    'button:not([disabled]), select:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )].filter((node) => !node.hidden);
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (document.activeElement === filterSheetPanel || !filterSheetPanel.contains(document.activeElement)) {
    event.preventDefault();
    if (event.shiftKey) last.focus();
    else first.focus();
    return;
  }
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}
const providerMediaPolicies = new Map();
const failedPreviewIds = new Set();
const FAILED_PREVIEW_STORAGE_KEY = "search.failedPreviewIds.v2";
const FAILED_PREVIEW_LIMIT = 100;
const RETURN_POSITION_KEY = "search.returnPosition.v1";
const RETURN_SNAPSHOT_LIMIT = 120;

try {
  const saved = JSON.parse(sessionStorage.getItem(FAILED_PREVIEW_STORAGE_KEY) || "[]");
  if (Array.isArray(saved)) {
    for (const id of saved.slice(-FAILED_PREVIEW_LIMIT)) {
      if (typeof id === "string" && id) failedPreviewIds.add(id);
    }
  }
} catch (_) {}

function persistFailedPreviewIds() {
  try {
    const ids = [...failedPreviewIds].slice(-FAILED_PREVIEW_LIMIT);
    sessionStorage.setItem(FAILED_PREVIEW_STORAGE_KEY, JSON.stringify(ids));
  } catch (_) {}
}

function mediaPolicyFor(provider) {
  return providerMediaPolicies.get(provider) || {
    thumbnail_mode: "direct",
    preview_mode: "disabled",
    thumbnail_host_suffixes: [],
    preview_host_suffixes: [],
    preview_resolution_mode: "stored",
    preview_storage_mode: "stable",
  };
}

function hostMatchesSuffix(host, suffix) {
  const root = String(suffix || "").toLowerCase().replace(/^\./, "");
  return Boolean(root) && (host === root || host.endsWith(`.${root}`));
}

function resolveThumbnailUrl(item) {
  if (!item?.thumbnail) return "";
  const policy = mediaPolicyFor(item.provider);
  if (policy.thumbnail_mode === "proxy") {
    return `/api/thumb-proxy?provider=${encodeURIComponent(item.provider)}&url=${encodeURIComponent(item.thumbnail)}`;
  }
  return item.thumbnail;
}

function previewEligible(item) {
  if (!item?.id || failedPreviewIds.has(item.id)) return false;
  const policy = mediaPolicyFor(item.provider);
  if (!["direct", "proxy"].includes(policy.preview_mode)) return false;
  const needsOnDemand = policy.preview_resolution_mode === "on_demand" && (policy.preview_storage_mode === "ephemeral" || !item.preview_url);
  if (needsOnDemand) return true;
  if (!item.preview_url) return false;
  try {
    const parsed = new URL(item.preview_url);
    if (parsed.protocol !== "https:") return false;
    const host = parsed.hostname.toLowerCase();
    return (policy.preview_host_suffixes || []).some((suffix) => hostMatchesSuffix(host, suffix));
  } catch (_) {
    return false;
  }
}

function resolvePreviewUrl(item, previewUrl = item.preview_url) {
  const policy = mediaPolicyFor(item.provider);
  if (policy.preview_mode === "proxy") {
    return "/api/preview-proxy?provider=" + encodeURIComponent(item.provider) + "&url=" + encodeURIComponent(previewUrl);
  }
  return previewUrl;
}

function rememberResolvedPreview(itemId, url) {
  if (!itemId || !url) return;
  if (resolvedPreviewCache.has(itemId)) resolvedPreviewCache.delete(itemId);
  resolvedPreviewCache.set(itemId, url);
  while (resolvedPreviewCache.size > PREVIEW_CACHE_LIMIT) {
    resolvedPreviewCache.delete(resolvedPreviewCache.keys().next().value);
  }
}

async function resolvePreviewForPlayback(item) {
  const cached = resolvedPreviewCache.get(item.id);
  if (cached) return cached;
  const policy = mediaPolicyFor(item.provider);
  const needsFresh = policy.preview_resolution_mode === "on_demand" && (!item.preview_url || policy.preview_storage_mode === "ephemeral");
  let previewUrl = item.preview_url || "";
  if (needsFresh) {
    const response = await fetch("/api/preview/" + encodeURIComponent(item.id), { cache: "no-store", headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("preview resolution failed: " + response.status);
    const payload = await response.json();
    previewUrl = String(payload?.preview_url || "");
  }
  if (!previewUrl) throw new Error("preview unavailable");
  const resolved = resolvePreviewUrl(item, previewUrl);
  rememberResolvedPreview(item.id, resolved);
  return resolved;
}

function setPreviewToggle(toggle, playing) {
  if (!toggle) return;
  toggle.textContent = playing ? "■" : "▶";
  toggle.setAttribute("aria-label", playing ? "Stop preview" : "Play preview");
  toggle.setAttribute("aria-pressed", playing ? "true" : "false");
}

function stopMotionPreview(motion, still, toggle) {
  if (!motion) return;
  if (motion._previewStartTimer) {
    window.clearTimeout(motion._previewStartTimer);
    motion._previewStartTimer = null;
  }
  motion.pause();
  motion.hidden = true;
  if (still?.src) still.hidden = false;
  setPreviewToggle(toggle, false);
  if (activeMotionPreview?.motion === motion) activeMotionPreview = null;
}

function failMotionPreview(itemId, motion, still, toggle) {
  if (itemId) {
    failedPreviewIds.add(itemId);
    persistFailedPreviewIds();
  }
  stopMotionPreview(motion, still, toggle);
  motion.removeAttribute("src");
  motion.load();
  toggle.closest(".media-frame")?.classList.add("preview-failed");
  toggle.hidden = true;
}

function startMotionPreview(motion, still, url, toggle, itemId) {
  if (!motion || !url) return;
  toggle.closest(".media-frame")?.classList.remove("preview-failed");
  if (activeMotionPreview?.motion && activeMotionPreview.motion !== motion) {
    stopMotionPreview(
      activeMotionPreview.motion,
      activeMotionPreview.still,
      activeMotionPreview.toggle,
    );
  }
  if (motion.src !== url) motion.src = url;
  motion.hidden = false;
  if (still?.src) still.hidden = false;
  activeMotionPreview = { motion, still, toggle, itemId };
  motion._previewStartTimer = window.setTimeout(
    () => failMotionPreview(itemId, motion, still, toggle),
    4000,
  );
  motion.play().catch(() => failMotionPreview(itemId, motion, still, toggle));
}

function durationText(seconds) {
  if (!Number.isFinite(seconds)) return "";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

function publishedText(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function viewsText(value) {
  if (!Number.isFinite(value)) return "";
  return `${Math.trunc(value).toLocaleString()} views`;
}

function ratingText(percent, count) {
  if (!Number.isFinite(percent)) return "";
  const votes = Number.isFinite(count) ? ` (${Math.trunc(count).toLocaleString()})` : "";
  return `${Math.round(percent)}%${votes}`;
}

async function loadProviders() {
  try {
    const response = await fetch("/api/providers");
    if (!response.ok) return;
    const data = await response.json();
    providerMediaPolicies.clear();
    for (const row of data.media_policies || []) {
      if (row?.name) providerMediaPolicies.set(row.name, row);
    }
    for (const provider of data.providers || []) {
      const option = document.createElement("option");
      option.value = provider;
      option.textContent = provider;
      providerSelect.append(option);
    }
  } catch (_) {}
}

function getContentClassValue() {
  return contentClassInput.value;
}

function setContentClassValue(value) {
  const safeValue = ["", "amateur", "studio"].includes(value) ? value : "";
  contentClassInput.value = safeValue;
  for (const button of contentClassButtons) {
    const active = button.dataset.contentClass === safeValue;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(button.dataset.contentClass === safeValue));
  }
}

function buildSearchParams() {
  const params = new URLSearchParams();
  const query = queryInput.value.trim();
  if (query) params.set("q", query);

  if (sortSelect.value !== "relevance") params.set("sort", sortSelect.value);
  if (getContentClassValue()) params.set("content_class", getContentClassValue());
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

  const sort = params.get("sort") || "relevance";
  sortSelect.value = [...sortSelect.options].some((option) => option.value === sort) ? sort : "relevance";

  setContentClassValue(params.get("content_class") || "");

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

  updateFilterCount();
  return [...params.keys()].length > 0;
}

function setOptionalText(node, value) {
  const text = String(value || "").trim();
  node.textContent = text;
  node.hidden = !text;
}

function resultCard(item) {
  const card = template.content.firstElementChild.cloneNode(true);
  const thumb = card.querySelector(".thumb");
  const title = card.querySelector(".title");
  const preview = card.querySelector(".preview");
  const motion = card.querySelector(".motion-preview");
  const placeholder = card.querySelector(".placeholder");
  const previewToggle = card.querySelector(".preview-toggle");
  const mediaFrame = card.querySelector(".media-frame");

  card.dataset.itemId = item.id;
  thumb.href = item.url;
  thumb.setAttribute("aria-label", `View ${item.title}`);
  title.href = item.url;

  if (item.thumbnail) {
    preview.src = resolveThumbnailUrl(item);
    preview.hidden = false;
    placeholder.hidden = true;

    preview.addEventListener("error", () => {
      const policy = mediaPolicyFor(item.provider);
      const attempt = Number(preview.dataset.healAttempt || "0");
      if (policy.thumbnail_mode === "refresh" && attempt < 2) {
        preview.dataset.healAttempt = String(attempt + 1);
        const retry = () => {
          preview.src = `/api/thumb/${encodeURIComponent(item.id)}?refresh=true&_=${Date.now()}`;
          if (item.preview_url) motion.poster = preview.src;
        };
        if (attempt === 0) retry();
        else window.setTimeout(retry, 700);
        return;
      }
      preview.hidden = true;
      placeholder.hidden = false;
    });
  }

  if (previewEligible(item)) {
    motion.preload = "none";
    motion.referrerPolicy = "no-referrer";
    if (item.thumbnail) motion.poster = preview.src;
    previewToggle.hidden = false;
    setPreviewToggle(previewToggle, false);
    motion.addEventListener("playing", () => {
      if (motion._previewStartTimer) {
        window.clearTimeout(motion._previewStartTimer);
        motion._previewStartTimer = null;
      }
      if (preview?.src) preview.hidden = true;
      setPreviewToggle(previewToggle, true);
    });
    motion.addEventListener("error", () => {
      failMotionPreview(item.id, motion, preview, previewToggle);
    });
    previewToggle.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (activeMotionPreview?.motion === motion && !motion.paused) {
        stopMotionPreview(motion, preview, previewToggle);
        return;
      }
      previewToggle.disabled = true;
      previewToggle.setAttribute("aria-busy", "true");
      try {
        const resolvedPreview = await resolvePreviewForPlayback(item);
        motion.dataset.previewUrl = resolvedPreview;
        startMotionPreview(motion, preview, resolvedPreview, previewToggle, item.id);
      } catch (_) {
        failMotionPreview(item.id, motion, preview, previewToggle);
      } finally {
        previewToggle.disabled = false;
        previewToggle.removeAttribute("aria-busy");
      }
    });
    if (fineHoverQuery.matches) {
      let hoverIntent = 0;
      mediaFrame.addEventListener("pointerenter", () => {
        const intent = ++hoverIntent;
        window.setTimeout(async () => {
          if (intent !== hoverIntent || !mediaFrame.matches(":hover")) return;
          try {
            const resolvedPreview = await resolvePreviewForPlayback(item);
            if (intent !== hoverIntent || !mediaFrame.matches(":hover")) return;
            motion.dataset.previewUrl = resolvedPreview;
            startMotionPreview(motion, preview, resolvedPreview, previewToggle, item.id);
          } catch (_) {
            failMotionPreview(item.id, motion, preview, previewToggle);
          }
        }, 280);
      });
      mediaFrame.addEventListener("pointerleave", () => {
        hoverIntent += 1;
        if (activeMotionPreview?.motion === motion) {
          stopMotionPreview(motion, preview, previewToggle);
        }
      });
    }
  } else {
    previewToggle.hidden = true;
  }

  title.textContent = item.title;
  card.querySelector(".source").textContent = item.provider;
  setOptionalText(card.querySelector(".published"), publishedText(item.published_at));
  setOptionalText(card.querySelector(".views"), viewsText(item.views));
  setOptionalText(card.querySelector(".rating"), ratingText(item.rating_percent, item.rating_count));
  setOptionalText(card.querySelector(".content-class"), item.content_class === "amateur" ? "Amateur" : "");
  setOptionalText(card.querySelector(".studio"), item.studio || "");
  setOptionalText(
    card.querySelector(".age-check"),
    item.age_check_status === "required" ? "18+" : "",
  );
  card.querySelector(".quality").textContent = item.quality || "";
  card.querySelector(".duration").textContent = durationText(item.duration_seconds);

  const count = item.alternate_sources?.length || 0;
  setOptionalText(
    card.querySelector(".alternates"),
    count ? `+${count} source${count === 1 ? "" : "s"}` : "",
  );

  return card;
}

function renderSkeletons(count = 6, { append = false } = {}) {
  if (!append) resultsEl.replaceChildren();
  for (let index = 0; index < count; index += 1) {
    const skeleton = document.createElement("article");
    skeleton.className = "card skeleton-card";
    skeleton.dataset.uiState = "skeleton";
    skeleton.innerHTML = `
      <div class="skeleton-media"></div>
      <div class="skeleton-copy">
        <span></span><span></span>
      </div>`;
    resultsEl.append(skeleton);
  }
}

function clearSkeletons() {
  for (const node of resultsEl.querySelectorAll('[data-ui-state="skeleton"]')) node.remove();
}

function hasActiveFilters() {
  return Boolean(
    getContentClassValue() ||
    providerSelect.value ||
    qualitySelect.value ||
    durationSelect.value ||
    ageCheckSelect.value
  );
}

function renderEmptyState({ filtered = hasActiveFilters() } = {}) {
  resultsEl.replaceChildren();
  const state = document.createElement("div");
  state.className = "state-panel";
  state.innerHTML = filtered
    ? '<strong>No results match these filters.</strong><button type="button" data-action="clear-filters">Clear filters</button>'
    : '<strong>No results found.</strong><span>Try a different search.</span>';
  resultsEl.append(state);
}

function renderErrorState(message) {
  resultsEl.replaceChildren();
  const state = document.createElement("div");
  state.className = "state-panel state-error";
  const copy = document.createElement("strong");
  copy.textContent = message || "Search failed";
  const retry = document.createElement("button");
  retry.type = "button";
  retry.dataset.action = "retry-search";
  retry.textContent = "Retry";
  state.append(copy, retry);
  resultsEl.append(state);
}

function render(items, { append = false } = {}) {
  if (!append) {
    resultsEl.replaceChildren();
    seenIds = new Set();
    renderedItems = [];
  }

  let added = 0;
  for (const item of items) {
    if (!item?.id || seenIds.has(item.id)) continue;
    seenIds.add(item.id);
    renderedItems.push(item);
    resultsEl.append(resultCard(item));
    added += 1;
  }

  nextOffset = seenIds.size;
  return added;
}

function liveSummary(providers) {
  const available = (providers || []).filter(
    (item) => !item.error,
  );
  if (!available.length) return "";
  return `${available.length} live source${available.length === 1 ? "" : "s"}`;
}

function liveFailureCount(providers) {
  return (providers || []).filter((item) => Boolean(item?.error)).length;
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
  const summary = liveSummary(live.providers);
  const failures = liveFailureCount(live.providers);
  const unavailable = failures
    ? `${failures} live source${failures === 1 ? "" : "s"} unavailable`
    : "";
  liveStatusText = [summary, unavailable].filter(Boolean).join(" · ");
  setLiveDetail(liveStatusText);
}

async function requestLive(payload, generation, page, { commit = true } = {}) {
  const requestedLimit = 24;
  const livePayload = {
    q: payload.q,
    page,
    limit_per_provider: requestedLimit,
  };
  if (payload.sort) livePayload.sort = payload.sort;
  if (payload.content_class) livePayload.content_class = payload.content_class;
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

function collapseDuplicateResults(items, limit = PAGE_SIZE) {
  const rows = [];
  const byKey = new Map();
  const ids = new Set();

  for (const item of items || []) {
    if (!item?.id || ids.has(item.id)) continue;
    ids.add(item.id);
    const titleKey = String(item.title || "")
      .toLocaleLowerCase()
      .replace(/[^\p{L}\p{N}]+/gu, " ")
      .trim()
      .replace(/\s+/g, " ");
    const durationBucket = Math.round((Number(item.duration_seconds) || 0) / 15);
    const key = `${titleKey}|${durationBucket}`;
    const primary = byKey.get(key);

    if (primary) {
      const alternate = {
        provider: item.provider,
        url: item.url,
        quality: item.quality || null,
      };
      const alternates = primary.alternate_sources || (primary.alternate_sources = []);
      if (!alternates.some((row) => row.provider === alternate.provider && row.url === alternate.url)) {
        alternates.push(alternate);
      }
      continue;
    }

    const clone = { ...item, alternate_sources: [...(item.alternate_sources || [])] };
    byKey.set(key, clone);
    rows.push(clone);
    if (rows.length >= limit) break;
  }
  return rows;
}

function compareOptionalNumber(a, b, ascending = false) {
  const aKnown = Number.isFinite(a);
  const bKnown = Number.isFinite(b);
  if (aKnown !== bKnown) return aKnown ? -1 : 1;
  if (!aKnown) return 0;
  return ascending ? a - b : b - a;
}

function sortVisibleItems(items, sort) {
  const rows = [...items];
  if (sort === "relevance") return rows;
  return rows.sort((a, b) => {
    if (sort === "newest") return compareOptionalNumber(Date.parse(a.published_at || ""), Date.parse(b.published_at || ""));
    if (sort === "views") return compareOptionalNumber(a.views, b.views);
    if (sort === "rating") {
      const rating = compareOptionalNumber(a.rating_percent, b.rating_percent);
      return rating || compareOptionalNumber(a.rating_count, b.rating_count);
    }
    if (sort === "longest") return compareOptionalNumber(a.duration_seconds, b.duration_seconds);
    if (sort === "shortest") return compareOptionalNumber(a.duration_seconds, b.duration_seconds, true);
    return 0;
  });
}

function mergeLiveAndLocal(liveItems, localItems, sort, limit = PAGE_SIZE) {
  if (sort === "relevance") {
    const candidates = blendLiveAndLocal(liveItems, localItems, limit * 3);
    return collapseDuplicateResults(candidates, limit);
  }
  const unique = [];
  const ids = new Set();
  for (const item of [...liveItems, ...localItems]) {
    if (!item?.id || ids.has(item.id)) continue;
    ids.add(item.id);
    unique.push(item);
  }
  return collapseDuplicateResults(sortVisibleItems(unique, sort), limit);
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
    items: mergeLiveAndLocal(liveItems, localItems, payload.sort || "relevance", PAGE_SIZE),
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

async function refreshLive(payload, generation, localData) {
  try {
    const live = await requestLive(payload, generation, 1);
    if (!live || generation !== searchGeneration) return;

    const merged = mergeLiveAndLocal(live.items || [], localData.items || [], payload.sort || "relevance");
    render(merged);
    localHasMore = Boolean(localData.has_more);

    moreBtn.hidden = !(localHasMore || liveHasMore);
    moreBtn.disabled = false;
    const total = Number.isFinite(localData.total) ? localData.total : nextOffset;
    const totalText = localData.total_capped ? `${total.toLocaleString()}+` : total.toLocaleString();
    setPrimaryStatus(`${nextOffset} shown · ${totalText} cached matches`);
    setLiveDetail(liveStatusText);
    if (!prefetchedPage && !prefetchPromise) startPrefetch(payload, generation);
  } catch (_) {
    if (generation !== searchGeneration) return;
    moreBtn.disabled = false;
    setLiveDetail("Live sources unavailable — showing cached results.");
    if (!prefetchedPage && !prefetchPromise) startPrefetch(payload, generation);
  }
}

async function loadMore() {
  const generation = searchGeneration;
  const stateParams = buildSearchParams();
  const payload = { q: stateParams.get("q") || "" };
  if (stateParams.has("sort")) payload.sort = stateParams.get("sort");
  if (stateParams.has("content_class")) payload.content_class = stateParams.get("content_class");
  if (stateParams.has("provider")) payload.provider = stateParams.get("provider");
  if (stateParams.has("quality")) payload.quality = stateParams.get("quality");
  if (stateParams.has("age_check")) payload.age_check = stateParams.get("age_check");
  if (stateParams.has("min_duration")) payload.min_duration = Number(stateParams.get("min_duration"));
  if (stateParams.has("max_duration")) payload.max_duration = Number(stateParams.get("max_duration"));

  moreBtn.disabled = true;
  moreBtn.textContent = prefetchedPage ? "Showing…" : "Loading…";
  setPrimaryStatus(prefetchedPage ? "Showing prepared results…" : "Finishing next page…");
  renderSkeletons(3, { append: true });

  try {
    let page = prefetchedPage;
    if (!page) {
      if (!prefetchPromise) startPrefetch(payload, generation);
      page = prefetchedPage || (prefetchPromise ? await prefetchPromise : null);
    }
    if (generation !== searchGeneration) return;
    if (!page) {
      clearSkeletons();
      moreBtn.disabled = false;
      moreBtn.textContent = "Show more";
      return;
    }

    prefetchedPage = null;
    prefetchPromise = null;

    if (page.live) {
      applyLiveState(page.live, page.livePage, page.requestedLimit);
    }
    localHasMore = page.localHasMore;

    clearSkeletons();
    render(page.items || [], { append: true });

    moreBtn.hidden = !(localHasMore || liveHasMore);
    moreBtn.disabled = false;
    moreBtn.textContent = "Show more";
    setPrimaryStatus(`${nextOffset} shown`);
    setLiveDetail(liveStatusText);

    startPrefetch(payload, generation);
  } catch (error) {
    clearSkeletons();
    moreBtn.disabled = false;
    moreBtn.textContent = "Show more";
    setPrimaryStatus(error.message || "Loading more failed");
  }
}

async function search({ persist = true, append = false, resetScroll = false } = {}) {
  if (append) return loadMore();
  if (resetScroll) window.scrollTo({ top: 0, left: 0, behavior: "auto" });

  const generation = ++searchGeneration;
  const stateParams = buildSearchParams();
  if (persist) persistState(stateParams);

  const payload = { q: stateParams.get("q") || "" };
  if (stateParams.has("sort")) payload.sort = stateParams.get("sort");
  if (stateParams.has("content_class")) payload.content_class = stateParams.get("content_class");
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
  setLiveDetail("");
  localHasMore = false;
  prefetchedPage = null;
  prefetchPromise = null;
  moreBtn.hidden = true;
  moreBtn.disabled = true;
  setPrimaryStatus("Searching…");
  renderSkeletons();

  try {
    const data = await fetchLocal(payload);
    if (generation !== searchGeneration) return;
    clearSkeletons();
    render(data.items || []);
    if (!seenIds.size) renderEmptyState();
    localHasMore = Boolean(data.has_more);

    const total = Number.isFinite(data.total) ? data.total : nextOffset;
    const totalText = data.total_capped ? `${total.toLocaleString()}+` : total.toLocaleString();
    const shouldRefreshLive = Boolean(payload.q);
    moreBtn.hidden = !localHasMore;
    moreBtn.disabled = shouldRefreshLive;
    if (shouldRefreshLive) {
      setPrimaryStatus(`${nextOffset} shown · ${totalText} cached matches`);
      setLiveDetail("Refreshing live sources…");
    } else {
      setPrimaryStatus(`${nextOffset} shown · ${totalText} matches`);
      setLiveDetail(data.providers.length ? `Sources: ${data.providers.join(", ")}` : "");
    }

    if (shouldRefreshLive) {
      await refreshLive(payload, generation, data);
    } else {
      moreBtn.disabled = false;
      startPrefetch(payload, generation);
    }
  } catch (error) {
    clearSkeletons();
    seenIds = new Set();
    nextOffset = 0;
    moreBtn.hidden = true;
    moreBtn.disabled = false;
    renderErrorState(error.message || "Search failed");
    setPrimaryStatus("Search unavailable");
    setLiveDetail("");
  }
}

function saveBrowsePosition(itemId) {
  if (!itemId) return;
  try {
    sessionStorage.setItem(RETURN_POSITION_KEY, JSON.stringify({
      href: window.location.href,
      itemId,
      scrollY: window.scrollY,
      loadedCount: nextOffset,
      items: renderedItems.slice(0, RETURN_SNAPSHOT_LIMIT),
      query: queryInput.value,
      sort: sortSelect.value,
      contentClass: getContentClassValue(),
      provider: providerSelect.value,
      quality: qualitySelect.value,
      duration: durationSelect.value,
      ageCheck: ageCheckSelect.value,
      localHasMore,
      liveHasMore,
      livePage,
      liveStatusText,
      primaryStatus: statusEl.textContent,
      liveDetail: liveDetailEl.textContent,
    }));
  } catch (_) {}
}

function readBrowsePosition() {
  try {
    const raw = sessionStorage.getItem(RETURN_POSITION_KEY);
    if (!raw) return null;
    const saved = JSON.parse(raw);
    if (!saved || saved.href !== window.location.href || !saved.itemId) return null;
    const scrollY = Number(saved.scrollY);
    const loadedCount = Number(saved.loadedCount);
    if (!Number.isFinite(scrollY) || !Number.isFinite(loadedCount)) return null;
    const items = Array.isArray(saved.items)
      ? saved.items.filter((item) => item?.id).slice(0, RETURN_SNAPSHOT_LIMIT)
      : [];
    return { ...saved, scrollY, loadedCount, items };
  } catch (_) {
    return null;
  }
}

function restoreBrowseSnapshot(saved) {
  if (!saved?.items?.length) return false;
  if (!saved.items.some((item) => item.id === saved.itemId)) return false;

  queryInput.value = String(saved.query || "");
  sortSelect.value = [...sortSelect.options].some((option) => option.value === saved.sort)
    ? saved.sort
    : "relevance";
  setContentClassValue(String(saved.contentClass || ""));
  qualitySelect.value = String(saved.quality || "");
  durationSelect.value = String(saved.duration || "");
  ageCheckSelect.value = String(saved.ageCheck || "");

  render(saved.items);
  localHasMore = Boolean(saved.localHasMore);
  liveHasMore = Boolean(saved.liveHasMore);
  livePage = Number.isFinite(Number(saved.livePage)) ? Number(saved.livePage) : 0;
  liveStatusText = String(saved.liveStatusText || "");
  moreBtn.hidden = !(localHasMore || liveHasMore);
  moreBtn.disabled = false;
  setPrimaryStatus(String(saved.primaryStatus || `${nextOffset} shown`));
  setLiveDetail(String(saved.liveDetail || liveStatusText));

  window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
    window.scrollTo({ top: saved.scrollY, left: 0, behavior: "auto" });
  }));

  try { sessionStorage.removeItem(RETURN_POSITION_KEY); } catch (_) {}
  return true;
}

async function restoreBrowsePosition() {
  const saved = readBrowsePosition();
  if (!saved) return;
  try {
    let target = document.querySelector(`[data-item-id="${CSS.escape(saved.itemId)}"]`);
    let previousOffset = -1;
    while (nextOffset < saved.loadedCount && (localHasMore || liveHasMore)) {
      if (target) break;
      if (nextOffset === previousOffset) break;
      previousOffset = nextOffset;
      await loadMore();
      target = document.querySelector(`[data-item-id="${CSS.escape(saved.itemId)}"]`);
    }
    await new Promise((resolve) => window.requestAnimationFrame(() => window.requestAnimationFrame(resolve)));
    target = document.querySelector(`[data-item-id="${CSS.escape(saved.itemId)}"]`);
    if (target) target.scrollIntoView({ block: "center", behavior: "auto" });
    else window.scrollTo({ top: saved.scrollY, left: 0, behavior: "auto" });
  } finally {
    try { sessionStorage.removeItem(RETURN_POSITION_KEY); } catch (_) {}
  }
}

resultsEl.addEventListener("click", (event) => {
  const outbound = event.target.closest("a.thumb, a.title");
  if (outbound && event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
    saveBrowsePosition(outbound.closest(".card")?.dataset.itemId || "");
  }
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action === "retry-search") {
    search({ persist: false });
  } else if (action === "clear-filters") {
    setContentClassValue("");
    providerSelect.value = "";
    qualitySelect.value = "";
    durationSelect.value = "";
    ageCheckSelect.value = "";
    search({ resetScroll: true });
  }
});

document.addEventListener("visibilitychange", () => {
  if (document.hidden && activeMotionPreview?.motion) {
    stopMotionPreview(activeMotionPreview.motion, activeMotionPreview.still, activeMotionPreview.toggle);
  }
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  search({ resetScroll: true });
});

sortSelect.addEventListener("change", () => search({ resetScroll: true }));
for (const button of contentClassButtons) {
  button.addEventListener("click", () => {
    setContentClassValue(button.dataset.contentClass || "");
    search({ resetScroll: true });
  });
}

for (const el of [providerSelect, qualitySelect, durationSelect, ageCheckSelect]) {
  el.addEventListener("change", updateFilterCount);
}

filtersOpenBtn.addEventListener("click", openFilterSheet);
filtersCloseBtn.addEventListener("click", () => closeFilterSheet());
filtersResetBtn.addEventListener("click", resetSecondaryFilters);
filtersApplyBtn.addEventListener("click", applyFilterSheet);
filterSheet.querySelector("[data-filter-close]").addEventListener("click", () => closeFilterSheet());
filterSheet.addEventListener("keydown", trapFilterSheetFocus);

moreBtn.addEventListener("click", () => {
  search({ persist: false, append: true });
});

const moreRow = document.querySelector(".more-row");
const moreObserver = "IntersectionObserver" in window
  ? new IntersectionObserver((entries) => {
      if (
        entries.some((entry) => entry.isIntersecting) &&
        !moreBtn.hidden &&
        !moreBtn.disabled
      ) {
        loadMore();
      }
    }, { rootMargin: "900px 0px" })
  : null;
if (moreObserver && moreRow) moreObserver.observe(moreRow);

clearBtn.addEventListener("click", () => {
  searchGeneration += 1;
  queryInput.value = "";
  sortSelect.value = "relevance";
  setContentClassValue("");
  providerSelect.value = "";
  qualitySelect.value = "";
  durationSelect.value = "";
  ageCheckSelect.value = "";
  updateFilterCount();
  resultsEl.replaceChildren();
  seenIds = new Set();
  renderedItems = [];
  nextOffset = 0;
  livePage = 0;
  liveHasMore = false;
  liveStatusText = "";
  setLiveDetail("");
  localHasMore = false;
  prefetchedPage = null;
  prefetchPromise = null;
  moreBtn.hidden = true;
  setPrimaryStatus("Ready");
  persistState(new URLSearchParams());
  queryInput.focus();
});

async function boot() {
  const saved = readBrowsePosition();
  const snapshotRestored = restoreBrowseSnapshot(saved);
  await loadProviders();
  const restored = restoreState();
  if (snapshotRestored) {
    return;
  }
  if (restored) {
    await search({ persist: false });
    await restoreBrowsePosition();
  }
}

if ("scrollRestoration" in window.history) window.history.scrollRestoration = "manual";
window.addEventListener("pageshow", (event) => {
  if (!event.persisted) return;
  const saved = readBrowsePosition();
  if (!saved) return;
  window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
    window.scrollTo({ top: saved.scrollY, left: 0, behavior: "auto" });
    try { sessionStorage.removeItem(RETURN_POSITION_KEY); } catch (_) {}
  }));
});

boot();

if ("serviceWorker" in navigator) {
  const SW_RELOAD_GUARD = "search.swReload.v32";

  navigator.serviceWorker.addEventListener("controllerchange", () => {
    try {
      if (sessionStorage.getItem(SW_RELOAD_GUARD) === "1") return;
      sessionStorage.setItem(SW_RELOAD_GUARD, "1");
    } catch (_) {}
    window.location.reload();
  });

  window.setTimeout(() => {
    try {
      sessionStorage.removeItem(SW_RELOAD_GUARD);
    } catch (_) {}
  }, 5000);

  window.addEventListener("load", async () => {
    try {
      const registration = await navigator.serviceWorker.register("/sw.js?v=32", { updateViaCache: "none" });
      await registration.update();
    } catch (_) {}
  });
}

const form = document.querySelector("#search-form");
const qInput = document.querySelector("#q");
const providerSelect = document.querySelector("#provider");
const limitSelect = document.querySelector("#limit");
const results = document.querySelector("#results");
const statusEl = document.querySelector("#status");
const counters = {
  current: document.querySelector("#count-current"),
  candidate: document.querySelector("#count-candidate"),
  none: document.querySelector("#count-none"),
  error: document.querySelector("#count-error"),
};

const TEST_PROVIDERS = [
  "xvideos",
  "xnxx",
  "xgroovy",
  "mypornhere",
  "pussyspace",
  "porndig",
  "sexvid",
  "pornid",
  "zbporn",
];

function thumbnailDirectoryPreview(thumbnail) {
  try {
    const u = new URL(thumbnail);
    const parts = u.pathname.split("/");
    parts[parts.length - 1] = "preview.mp4";
    u.pathname = parts.join("/");
    u.search = "";
    u.hash = "";
    return u.toString();
  } catch (_) {
    return null;
  }
}

function inferPreviewCandidate(item) {
  const provider = String(item.provider || "").toLowerCase();
  const thumbnail = String(item.thumbnail || "");
  const page = String(item.url || "");

  if (["xvideos", "xnxx", "pussyspace"].includes(provider) && thumbnail) {
    return thumbnailDirectoryPreview(thumbnail);
  }

  if (provider === "sexvid" || provider === "pornid" || provider === "zbporn") {
    const m = thumbnail.match(/\/contents\/videos_screenshots\/(\d+)\/(\d+)\//);
    if (!m) return null;
    const [, bucket, id] = m;
    if (provider === "sexvid") return `https://pr1.sexvid.xxx/contents/videos/${bucket}/${id}/${id}_short_preview.mp4`;
    if (provider === "pornid") return `https://pr1.pornid.xxx/contents/videos/${bucket}/${id}/${id}_short_preview_480x270.mp4`;
    return `https://pr1.zbporn.com/contents/videos/${bucket}/${id}/${id}_short_preview.mp4`;
  }
  if (provider === "xgroovy") {
    const m = page.match(/\/videos\/(\d+)(?:\/|$)/);
    if (!m) return null;
    const id = Number(m[1]);
    const bucket = Math.floor(id / 1000) * 1000;
    return `https://preview.xgroovy.com/videos/${bucket}/${id}/${id}_pr640.mp4`;
  }

  if (provider === "mypornhere") {
    const m = page.match(/\/videos\/(\d+)(?:\/|$)/);
    if (!m) return null;
    const id = Number(m[1]);
    const bucket = Math.floor(id / 1000) * 1000;
    return `https://www.mypornhere.com/contents/videos/${bucket}/${id}/${id}_preview.mp4`;
  }

  if (provider === "porndig") {
    const m = thumbnail.match(/\/thumbs\/(\d{4})\/(\d{2})\/(\d+)\//);
    if (!m) return null;
    const [, year, month, id] = m;
    return `https://image-cdn.porndig.com/previewclips/${year}/${month}/${id}/${id}_1.mp4`;
  }

  return null;
}

async function resolveCurrentPreview(item) {
  if (item.preview_url) return { url: item.preview_url, source: "current" };
  try {
    const response = await fetch(`/test-api/preview/${encodeURIComponent(item.id)}`, { cache: "no-store" });
    if (!response.ok) return null;
    const payload = await response.json();
    if (payload.preview_url) return { url: payload.preview_url, source: "current" };
  } catch (_) {}
  return null;
}

function badge(text, type) {
  const el = document.createElement("span");
  el.className = `badge ${type}`;
  el.textContent = text;
  return el;
}

function buildCard(item, preview) {
  const card = document.createElement("article");
  card.className = "card";

  const media = document.createElement("div");
  media.className = "media";

  const img = document.createElement("img");
  img.loading = "lazy";
  img.alt = "";
  img.src = item.thumbnail || "";
  media.appendChild(img);

  let video = null;
  if (preview?.url) {
    video = document.createElement("video");
    video.muted = true;
    video.loop = true;
    video.playsInline = true;
    video.preload = "metadata";
    video.src = preview.url;
    media.appendChild(video);

    const playButton = document.createElement("button");
    playButton.type = "button";
    playButton.className = "preview-play";
    playButton.textContent = "▶";
    playButton.setAttribute("aria-label", "Play preview");
    media.appendChild(playButton);

    const start = () => {
      media.classList.add("playing");
      playButton.textContent = "❚❚";
      playButton.setAttribute("aria-label", "Stop preview");
      video.play().catch(() => {
        playButton.textContent = "▶";
        playButton.setAttribute("aria-label", "Play preview");
        media.classList.remove("playing");
      });
    };
    const stop = () => {
      video.pause();
      video.currentTime = 0;
      media.classList.remove("playing");
      playButton.textContent = "▶";
      playButton.setAttribute("aria-label", "Play preview");
    };
    const canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    if (canHover) {
      media.addEventListener("mouseenter", start);
      media.addEventListener("mouseleave", stop);
    }
    playButton.addEventListener("click", (event) => {
      event.stopPropagation();
      video.paused ? start() : stop();
    });
    media.addEventListener("click", () => video.paused ? start() : stop());
    video.addEventListener("error", () => {
      playButton.hidden = true;
      card.dataset.previewError = "1";
      const sourceBadge = card.querySelector(".badge.current, .badge.candidate");
      if (sourceBadge) {
        sourceBadge.textContent = "Preview error";
        sourceBadge.className = "badge error";
      }
      recount();
    });
  }

  const body = document.createElement("div");
  body.className = "body";
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.appendChild(badge(item.provider || "unknown", "provider"));
  if (preview?.source === "current") meta.appendChild(badge("Current preview", "current"));
  else if (preview?.source === "candidate") meta.appendChild(badge("Lab candidate", "candidate"));
  else if (preview?.source === "proxy") meta.appendChild(badge("Proxy required", "none"));
  else meta.appendChild(badge("No preview", "none"));

  const title = document.createElement("h2");
  title.textContent = item.title || "Untitled";
  const link = document.createElement("a");
  link.href = item.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = "Open source";

  body.append(meta, title, link);
  card.append(media, body);
  return card;
}

function recount() {
  const cards = [...results.querySelectorAll(".card")];
  const count = (selector) => cards.filter((card) => card.querySelector(selector) && !card.dataset.previewError).length;
  counters.current.textContent = count(".badge.current");
  counters.candidate.textContent = count(".badge.candidate");
  counters.none.textContent = count(".badge.none");
  counters.error.textContent = cards.filter((card) => card.dataset.previewError).length;
}

async function fetchProviderSearch(provider, sampleLimit) {
  const params = new URLSearchParams();
  params.set("q", qInput.value.trim());
  params.set("limit", String(sampleLimit));
  params.set("offset", "0");
  params.set("provider", provider);

  const response = await fetch(`/test-api/search?${params.toString()}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${provider}: HTTP ${response.status}`);
  return response.json();
}

function roundRobinSamples(payloads, sampleLimit) {
  const queues = payloads.map((payload) => [...(Array.isArray(payload.items) ? payload.items : [])]);
  const items = [];
  while (items.length < sampleLimit && queues.some((queue) => queue.length)) {
    for (const queue of queues) {
      if (queue.length && items.length < sampleLimit) items.push(queue.shift());
    }
  }
  return items;
}

async function runSearch() {
  const sampleLimit = Number(limitSelect.value);

  statusEl.textContent = "Loading…";
  results.replaceChildren();
  Object.values(counters).forEach((el) => { el.textContent = "0"; });

  if (!providerSelect.value) {
    statusEl.textContent = "Select provider";
    return;
  }

  try {
    const payload = await fetchProviderSearch(providerSelect.value, sampleLimit);
    const items = Array.isArray(payload.items) ? payload.items : [];
    const total = Number(payload.total || 0);

    for (const item of items) {
      let preview = await resolveCurrentPreview(item);
      if (!preview && String(item.provider || "").toLowerCase() === "xgroovy") {
        preview = { source: "proxy" };
      }
      if (!preview) {
        const candidate = inferPreviewCandidate(item);
        if (candidate) preview = { url: candidate, source: "candidate" };
      }
      results.appendChild(buildCard(item, preview));
    }
    recount();
    statusEl.textContent = `${items.length} samples · total ${total}`;
  } catch (error) {
    statusEl.textContent = `Error: ${error.message}`;
  }
}

function loadProviders() {
  for (const name of TEST_PROVIDERS) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    providerSelect.appendChild(option);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  runSearch();
});

loadProviders();
runSearch();

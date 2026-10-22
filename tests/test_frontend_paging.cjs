const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const app = fs.readFileSync(path.join(__dirname, "../frontend/app.js"), "utf8");

function purePagingContext() {
  const start = app.indexOf("function blendLiveAndLocal(");
  const end = app.indexOf("async function fetchLocal(", start);
  assert.ok(start >= 0 && end > start);
  const context = vm.createContext({});
  vm.runInContext(`const PAGE_SIZE = 40;\n${app.slice(start, end)}`, context);
  return context;
}

test("merged page keeps every unused live and cached hit for subsequent pages", () => {
  const context = purePagingContext();
  const live = Array.from({ length: 120 }, (_, i) => ({ id: `live-${i}` }));
  const local = Array.from({ length: 40 }, (_, i) => ({ id: `local-${i}` }));
  const page = context.partitionMergedPage(live, local, "relevance");
  assert.equal(page.items.length, 40);
  assert.equal(page.liveRemaining.length + page.localRemaining.length, 120);
  const ids = [
    ...page.items,
    ...page.liveRemaining,
    ...page.localRemaining,
  ].map((item) => item.id);
  assert.equal(new Set(ids).size, 160);
});

test("cross-stream duplicate is not put back into either buffer", () => {
  const context = purePagingContext();
  const page = context.partitionMergedPage(
    [{ id: "shared" }, { id: "live-only" }],
    [{ id: "shared" }, { id: "local-only" }],
    "relevance",
    1,
  );
  assert.equal(page.items[0].id, "shared");
  assert.deepEqual(
    [...page.liveRemaining, ...page.localRemaining].map((item) => item.id).sort(),
    ["live-only", "local-only"],
  );
});

test("cached fetch advances to a caller-provided offset", async () => {
  const start = app.indexOf("async function apiJson(");
  const end = app.indexOf("async function prepareNextPage(", start);
  assert.ok(start >= 0 && end > start);
  let sent;
  const context = vm.createContext({
    fetch: async (_url, options) => {
      sent = JSON.parse(options.body);
      return { ok: true, json: async () => ({ items: [], has_more: false }) };
    },
  });
  vm.runInContext(`const PAGE_SIZE = 40;\n${app.slice(start, end)}`, context);
  await context.fetchLocal({ q: "4k" }, { offset: 6000, limit: 40 });
  assert.equal(sent.offset, 6000);
  assert.equal(sent.limit, 40);
  assert.equal(sent.exclude_ids, undefined);
});

test("non-JSON gateway failure shows a recoverable search message", async () => {
  const start = app.indexOf("async function apiJson(");
  const end = app.indexOf("async function prepareNextPage(", start);
  const context = vm.createContext({
    fetch: async () => ({
      ok: false,
      json: async () => { throw new SyntaxError("Unexpected token '<'"); },
    }),
  });
  vm.runInContext(`const PAGE_SIZE = 40;\n${app.slice(start, end)}`, context);
  await assert.rejects(
    () => context.fetchLocal({ q: "4k" }),
    /Search temporarily unavailable/,
  );
});

test("next page drains live buffer before requesting another provider page", async () => {
  const pureStart = app.indexOf("function blendLiveAndLocal(");
  const prepareStart = app.indexOf("async function prepareNextPage(");
  const prepareEnd = app.indexOf("function startPrefetch(", prepareStart);
  let liveCalls = 0;
  let localOffsetRequested;
  const context = vm.createContext({
    searchGeneration: 1,
    localHasMore: true,
    liveHasMore: true,
    localBuffer: Array.from({ length: 10 }, (_, i) => ({ id: `local-${i}` })),
    liveBuffer: Array.from({ length: 80 }, (_, i) => ({ id: `live-${i}` })),
    localSourceHasMore: true,
    liveSourceHasMore: true,
    localOffset: 40,
    livePage: 1,
    seenIds: new Set(),
    requestLive: async () => { liveCalls += 1; throw new Error("should not fetch live"); },
    fetchLocal: async (_payload, options) => {
      localOffsetRequested = options.offset;
      return {
        items: Array.from({ length: 40 }, (_, i) => ({ id: `new-local-${i}` })),
        has_more: true,
      };
    },
    upstreamHasMore: () => true,
  });
  vm.runInContext(
    `const PAGE_SIZE = 40;\n${app.slice(pureStart, app.indexOf("async function fetchLocal(", pureStart))}\n${app.slice(prepareStart, prepareEnd)}`,
    context,
  );
  const page = await context.prepareNextPage({ q: "4k" }, 1);
  assert.equal(liveCalls, 0);
  assert.equal(localOffsetRequested, 40);
  assert.equal(page.livePage, 1);
  assert.equal(page.localOffset, 80);
  assert.equal(page.items.length, 40);
  assert.equal(page.liveBuffer.length + page.localBuffer.length, 90);
});

test("browse snapshot never resumes beyond its saved result rows", () => {
  const start = app.indexOf("function restoreBrowseSnapshot(");
  const end = app.indexOf("async function restoreBrowsePosition(", start);
  const context = vm.createContext({
    welcomeEl: { hidden: false },
    queryInput: { value: "" },
    sortSelect: { options: [{ value: "relevance" }], value: "relevance" },
    setContentClassValue() {},
    qualitySelect: { value: "" },
    durationSelect: { value: "" },
    ageCheckSelect: { value: "" },
    render() {},
    nextOffset: 120,
    localHasMore: true,
    liveHasMore: false,
    visibleResultCount: 120,
    updatePagingFlags() {},
    moreBtn: {},
    setPrimaryStatus() {},
    setLiveDetail() {},
    window: { requestAnimationFrame() {} },
    sessionStorage: { removeItem() {} },
    RETURN_POSITION_KEY: "return-position",
  });
  vm.runInContext(app.slice(start, end), context);
  const saved = {
    itemId: "local-10",
    loadedCount: 200,
    localOffset: 200,
    items: Array.from({ length: 120 }, (_, i) => ({ id: `local-${i}` })),
  };
  assert.equal(context.restoreBrowseSnapshot(saved), false);
});

test("saving a deep browse position falls back to replay instead of truncating rows", () => {
  const start = app.indexOf("function saveBrowsePosition(");
  const end = app.indexOf("function readBrowsePosition(", start);
  let saved;
  const context = vm.createContext({
    sessionStorage: { setItem: (_key, value) => { saved = JSON.parse(value); } },
    RETURN_POSITION_KEY: "return-position",
    window: { location: { href: "https://test.example/?q=4k" }, scrollY: 900 },
    nextOffset: 200,
    renderedItems: Array.from({ length: 200 }, (_, i) => ({ id: `local-${i}` })),
    RETURN_SNAPSHOT_LIMIT: 120,
    queryInput: { value: "4k" },
    sortSelect: { value: "relevance" },
    getContentClassValue: () => "",
    providerSelect: { value: "" },
    qualitySelect: { value: "" },
    durationSelect: { value: "" },
    ageCheckSelect: { value: "" },
    localHasMore: false,
    localOffset: 200,
    localBuffer: [],
    localSourceHasMore: false,
    liveHasMore: false,
    liveBuffer: [],
    liveSourceHasMore: false,
    livePage: 0,
    liveStatusText: "",
    statusEl: { textContent: "200 shown" },
    liveDetailEl: { textContent: "" },
  });
  vm.runInContext(app.slice(start, end), context);
  context.saveBrowsePosition("local-10");
  assert.equal(saved.loadedCount, 200);
  assert.equal(saved.items.length, 0);
});

test("return navigation replays every previously loaded page even when target is on page one", async () => {
  const start = app.indexOf("async function restoreBrowsePosition(");
  const end = app.indexOf("resultsEl.addEventListener(", start);
  const target = { scrollIntoView() {} };
  let loadedPages = 0;
  const context = vm.createContext({
    readBrowsePosition: () => ({ itemId: "local-10", loadedCount: 120, scrollY: 0 }),
    document: { querySelector: () => target },
    CSS: { escape: (value) => value },
    window: { requestAnimationFrame: (callback) => callback() },
    sessionStorage: { removeItem() {} },
    RETURN_POSITION_KEY: "return-position",
    nextOffset: 40,
    localHasMore: true,
    liveHasMore: false,
    loadMore: async () => {
      loadedPages += 1;
      vm.runInContext("nextOffset += 40", context);
    },
  });
  vm.runInContext(app.slice(start, end), context);
  await context.restoreBrowsePosition();
  assert.equal(loadedPages, 2);
  assert.equal(vm.runInContext("nextOffset", context), 120);
});

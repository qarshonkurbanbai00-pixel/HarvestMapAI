"use strict";
/* HarvestMap AI · no build tooling, no remote runtime dependencies except OSM tiles. */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const money = (v) =>
  new Intl.NumberFormat("kk-KZ", { maximumFractionDigits: 2 }).format(v);
const date = (v) => new Date(v).toLocaleDateString("kk-KZ");
const cats = {
  farm: "Шаруашылық",
  shop: "Дүкен",
  market: "Базар",
  service: "Қызмет",
  vegetables: "Көкөніс",
  fruit: "Жеміс",
  dairy: "Сүт өнімдері",
  grain: "Астық",
  honey: "Бал",
  meat: "Ет",
};
const icons = {
  farm: "🌱",
  shop: "🏡",
  market: "🧺",
  service: "🚚",
  vegetables: "🥕",
  fruit: "🍎",
  dairy: "🥛",
  grain: "🌾",
  honey: "🍯",
  meat: "🥩",
};
const productIcons = {
  Қызанақ: "🍅",
  Қияр: "🥒",
  Алма: "🍎",
  Алмұрт: "🍐",
  Сәбіз: "🥕",
  Картоп: "🥔",
  Сүт: "🥛",
  Ірімшік: "🧀",
  Бал: "🍯",
  Қарбыз: "🍉",
  Бидай: "🌾",
  Ұн: "🌾",
};
const colors = {
  vegetables: "#edf0db",
  fruit: "#f3e8d5",
  dairy: "#e6ecea",
  grain: "#f0ebd7",
  honey: "#f3e7c5",
  meat: "#f0dfd9",
  farm: "#e2ebd8",
  shop: "#eee8d5",
  market: "#e7ebdf",
  service: "#e0e9e8",
};
const months = [
  "Қаң",
  "Ақп",
  "Нау",
  "Сәу",
  "Мам",
  "Мау",
  "Шіл",
  "Там",
  "Қыр",
  "Қаз",
  "Қар",
  "Жел",
];
const statusLabel = {
  approved: "Жарияланған",
  pending: "Тексерілуде",
  rejected: "Қабылданбады",
};
const roleLabel = { user: "Пайдаланушы", owner: "Кәсіп иесі", admin: "Әкімші" };
const state = {
  user: null,
  locations: [],
  map: null,
  charts: [],
  routeId: 0,
  catalog: null,
  compare: new Map(),
  listPage: 1,
  listFilters: {},
  mapTimer: null,
};
let toastTimer;
function toast(message, error = false) {
  const el = $("#toast");
  el.textContent = message;
  el.className = "show" + (error ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.className = ""), 4500);
}
async function api(path, options = {}) {
  const csrf = document.cookie
    .split("; ")
    .find((c) => c.startsWith("harvest_csrf="))
    ?.split("=")[1];
  const headers = {
    "Content-Type": "application/json",
    ...(csrf ? { "X-CSRF-Token": decodeURIComponent(csrf) } : {}),
    ...options.headers,
  };
  let response;
  try {
    response = await fetch("/api" + path, {
      ...options,
      headers,
      credentials: "same-origin",
    });
  } catch {
    throw new Error(
      "Сервермен байланыс жоқ. Интернетті немесе серверді тексеріңіз.",
    );
  }
  const data = await response
    .json()
    .catch(() => ({ detail: "Сервер жауабы оқылмады" }));
  if (!response.ok) {
    const e = new Error(
      (typeof data.detail === "string"
        ? data.detail
        : "Сұрауды орындау мүмкін болмады") +
        (data.errors ? " · " + data.errors.map((x) => x.field).join(", ") : ""),
    );
    e.status = response.status;
    throw e;
  }
  return data;
}
const send = (path, body, method = "POST") =>
  api(path, { method, body: JSON.stringify(body) });
const badge = (x) =>
  x.is_demo
    ? '<span class="badge demo">Демо дерек</span>'
    : '<span class="badge">Пайдаланушы дерегі</span>';
const status = (x) =>
  `<span class="badge ${esc(x.status)}">${statusLabel[x.status] || esc(x.status)}</span>`;
const options = (keys, selected = "", label = "Барлық санат") =>
  `<option value="">${label}</option>` +
  keys
    .map(
      (k) =>
        `<option value="${k}" ${k === selected ? "selected" : ""}>${cats[k]}</option>`,
    )
    .join("");
const locationOptions = (selected = "") =>
  '<option value="">Барлық елді мекен</option>' +
  state.locations
    .map(
      (l) =>
        `<option value="${l.id}" ${String(l.id) === String(selected) ? "selected" : ""}>${esc(l.name)}</option>`,
    )
    .join("");
function empty(
  title = "Ештеңе табылмады",
  text = "Іздеу сөзін немесе сүзгілерді өзгертіп көріңіз.",
  link = "",
) {
  return `<div class="empty"><div class="empty-icon">⌕</div><h3>${title}</h3><p>${text}</p>${link}</div>`;
}
function pageTitle(eyebrow, title, subtitle, action = "") {
  return `<div class="page-title"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${subtitle}</p></div>${action}</div>`;
}
function notice() {
  return '<div class="notice warn">Демо жазбалар — оқу үлгілері. Бағалар, мекенжайлар мен қорлар нақты сатылым ұсынысы немесе расталған экономикалық статистика емес.</div>';
}
function productCard(p) {
  const selected = state.compare.has(p.id);
  return `<article class="card"><a href="#/product/${p.id}" aria-label="${esc(p.name)} туралы"><div class="card-art" style="--art:${colors[p.category] || "#eaf0e0"}">${productIcons[p.name] || icons[p.category] || "🌿"}${badge(p)}<span class="arrow-circle">↗</span></div></a><div class="card-body"><a href="#/product/${p.id}"><h3>${esc(p.name)}</h3></a><div class="meta"><span>⌖ ${esc(p.location_name)}</span><span>${p.in_season ? "● Маусымда" : "Маусымнан тыс"}</span></div><div class="price-row"><span class="price">${money(p.price)} ₸ <small>/ ${esc(p.unit)}</small></span><button class="compare-toggle ${selected ? "selected" : ""}" data-action="compare-add" data-id="${p.id}" data-product="${esc(JSON.stringify(p))}" aria-pressed="${selected}">${selected ? "✓ Қосылды" : "+ Салыстыру"}</button></div></div></article>`;
}
function businessCard(b) {
  return `<article class="card business"><a href="#/business/${b.id}"><div class="card-art" style="--art:${colors[b.category]}">${icons[b.category]}${badge(b)}<span class="arrow-circle">↗</span></div><div class="card-body"><div class="meta"><span>${cats[b.category]}</span><span>⌖ ${esc(b.location.name)}</span></div><h3 class="space-top">${esc(b.name)}</h3><p>${esc(b.description)}</p></div></a></article>`;
}
function drawChart(id, type, data, options = {}) {
  if (!window.Chart) return;
  const el = $("#" + id);
  if (!el) return;
  const chart = new Chart(el, {
    type,
    data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: type === "doughnut",
          position: "bottom",
          labels: { boxWidth: 10, font: { size: 10 } },
        },
      },
      ...options,
    },
  });
  state.charts.push(chart);
}
function authNav() {
  const el = $("#auth-nav");
  el.innerHTML = state.user
    ? `<a class="btn secondary" href="#/account">${esc(state.user.name.split(" ")[0])} ↗</a>`
    : '<a class="btn text" href="#/login">Кіру</a><a class="btn register-link" href="#/register">Тіркелу ↗</a>';
}
function cleanup() {
  clearTimeout(state.mapTimer);
  if (state.map) {
    state.map.stop();
    state.map.remove();
    state.map = null;
  }
  state.charts.forEach((c) => c.destroy());
  state.charts = [];
  $("#modal").close();
  $(".compare-tray")?.remove();
}
async function route() {
  const id = ++state.routeId;
  cleanup();
  const hash = location.hash.slice(1) || "/";
  const [path, queryString = ""] = hash.split("?");
  const query = new URLSearchParams(queryString);
  const parts = path.split("/").filter(Boolean);
  const section = parts[0] || "home";
  $$("nav a").forEach((a) =>
    a.classList.toggle("active", a.hash.split("/")[1] === section),
  );
  $("#navigation").classList.remove("open");
  $(".mobile-toggle").setAttribute("aria-expanded", "false");
  $("#main").innerHTML =
    '<div class="container loading"><span class="spinner"></span>Деректер жүктелуде…</div>';
  window.scrollTo(0, 0);
  try {
    let html = "";
    let after = () => {};
    if (section === "home") {
      const [stats, ps, bs] = await Promise.all([
        api("/statistics"),
        api("/products?size=4"),
        api("/businesses?size=4"),
      ]);
      html = home(stats, ps.items, bs.items);
    } else if (section === "products" || section === "businesses") {
      state.listPage = 1;
      state.listFilters = Object.fromEntries(query);
      html = listing(section);
      after = () => loadListing(section, id);
    } else if (section === "map") {
      html = mapPage(query);
      after = () => initMap(query, id);
    } else if (section === "dashboard") {
      const stats = await api("/statistics");
      html = dashboard(stats);
      after = () => dashboardCharts(stats);
    } else if (section === "product") {
      const p = await api("/products/" + Number(parts[1]));
      html = productDetail(p);
      after = () => {
        drawChart("price-history", "line", {
          labels: p.history.map((h) => date(h.recorded_at)),
          datasets: [
            {
              label: `Баға, ₸/${p.unit}`,
              data: p.history.map((h) => h.price),
              borderColor: "#256a50",
              backgroundColor: "#d9f39755",
              fill: true,
              tension: 0.3,
              pointRadius: 4,
            },
          ],
        });
      };
    } else if (section === "business") {
      const b = await api("/businesses/" + Number(parts[1]));
      html = businessDetail(b);
      after = () => miniMap(b);
    } else if (section === "login" || section === "register") {
      if (state.user) {
        location.hash = "/account";
        return;
      }
      html = authPage(section);
    } else if (section === "account") {
      if (!state.user) {
        location.hash = "/login";
        return;
      }
      html = accountPage();
    } else if (section === "owner") {
      if (!requireRole(["owner", "admin"])) return;
      state.catalog = await api("/owner/catalog");
      html = ownerPage();
    } else if (section === "admin") {
      if (!requireRole(["admin"])) return;
      const [queue, users] = await Promise.all([
        api("/admin/queue"),
        api("/admin/users"),
      ]);
      html = adminPage(queue, users);
    } else if (section === "assistant") {
      html = assistantPage();
    } else {
      html = `<section class="container page">${empty("Бет табылмады", "Мекенжайды тексеріңіз немесе басты бетке оралыңыз.", '<a class="btn" href="#/">Басты бет</a>')}</section>`;
    }
    if (id !== state.routeId) return;
    $("#main").innerHTML = html;
    await after();
    if (id === state.routeId) updateCompareTray();
  } catch (e) {
    if (id !== state.routeId) return;
    $("#main").innerHTML =
      `<section class="container page">${empty("Деректерді жүктеу мүмкін болмады", esc(e.message), '<button class="btn" data-action="retry">Қайта жүктеу</button>')}</section>`;
  }
}
function requireRole(roles) {
  if (!state.user) {
    location.hash = "/login";
    return false;
  }
  if (!roles.includes(state.user.role)) {
    $("#main").innerHTML =
      `<section class="container page">${empty("Рұқсат шектеулі", "Бұл бөлімді ашуға рөліңіз сәйкес келмейді.", '<a class="btn" href="#/account">Жеке кабинет</a>')}</section>`;
    return false;
  }
  return true;
}
function home(s, ps, bs) {
  return `<div class="container"><section class="hero"><div><div class="eyebrow">Өңіріңізбен байланыста болыңыз</div><h1>Жергілікті өнім.<br><em>Жаңа мүмкіндік.</em></h1><p>Жақын маңдағы кәсіптерді табыңыз, маусымдық өнімдерді таңдаңыз және бағаларды бір жерден салыстырыңыз.</p><div class="hero-actions"><a href="#/map" class="btn">Картаны ашу <span>↗</span></a><a href="#/products" class="btn secondary">Өнімдерді көру →</a></div><div class="hero-note"><div class="avatars"><span>🌾</span><span>🍎</span><span>🌱</span></div><span>Өндіруші мен тұтынушыны жақындастырамыз</span></div></div><div class="hero-visual" aria-label="Жергілікті өнімдер мен карта туралы сәндік көрініс"><span class="visual-tag">ӨҢІРІҢІЗДІ ЖАҢАША ТАНЫҢЫЗ</span><div class="visual-ring"></div><div class="visual-center">🌱</div><div class="floating-card one"><span class="emoji">🍎</span><div><strong>Маусымның дәмі</strong><small>Жергілікті өнімді таңдаңыз</small></div></div><div class="floating-card two"><span class="emoji">⌖</span><div><strong>Барлығы бір картада</strong><small>Іздеңіз. Табыңыз. Танысыңыз.</small></div></div><div class="floating-card three"><div class="mini-graph"><i style="height:9px"></i><i style="height:17px"></i><i style="height:13px"></i><i style="height:23px"></i><i style="height:28px"></i></div><div><strong>Деректерге сүйеніңіз</strong><small>Бағаны ашық салыстырыңыз</small></div></div></div></section><form class="search-bar" id="home-search"><input name="q" type="search" placeholder="Өнім немесе кәсіп атауы…" aria-label="Өнім немесе кәсіп іздеу"><select name="location_id" aria-label="Елді мекен">${locationOptions()}</select><button class="btn" type="submit">Іздеу ⌕</button></form><section class="stats-strip" aria-label="Платформа көрсеткіштері"><div><strong>${s.businesses}</strong><span>Жарияланған кәсіп · демо: ${s.demo_businesses}</span></div><div><strong>${s.products}</strong><span>Өнім ұсынысы · демо: ${s.demo_products}</span></div><div><strong>${s.seasonal_products}</strong><span>Осы айда маусымда</span></div><div><strong>${s.regions}</strong><span>Платформадағы өңір</span></div></section><section class="section"><div class="section-heading"><div><div class="eyebrow">Жерден — дастарқанға</div><h2>Өңірдің өнімдері</h2><p>Ұсыныстарды зерттеп, бағаларды салыстырыңыз.</p></div><a class="link-arrow" href="#/products">Барлық өнім →</a></div><div class="grid">${ps.map(productCard).join("") || empty()}</div></section><section class="section"><div class="map-feature"><div class="map-feature-content"><div class="eyebrow">Жақыннан іздеңіз</div><h2>Мүмкіндіктер<br>сіз ойлағаннан жақын.</h2><p>Кәсіптер мен өнімдерді картадан қараңыз. Орналасқан жері бойынша сүзгілеп, өзіңізге ыңғайлысын табыңыз.</p><a href="#/map" class="btn lime">Картадан зерттеу ↗</a></div><a href="#/map" class="map-teaser" aria-label="Интерактивті картаға өту"><div class="teaser-grid"></div><span class="teaser-dot" style="left:23%;top:25%">🌱</span><span class="teaser-dot" style="left:65%;top:16%">🍎</span><span class="teaser-dot" style="left:55%;top:57%">🧺</span><span class="teaser-dot" style="left:80%;top:66%">🌾</span><div class="teaser-label">⌖ Елді мекеніңізді таңдаңыз <strong>↗</strong></div></a></div></section><section class="section"><div class="section-heading"><div><div class="eyebrow">Өңір экономикасын таныңыз</div><h2>Жергілікті кәсіптер</h2><p>Шаруашылықтар, дүкендер, базарлар және қызметтер.</p></div><a class="link-arrow" href="#/businesses">Барлық кәсіп →</a></div><div class="grid">${bs.map(businessCard).join("") || empty()}</div></section><section class="section"><div class="values"><div><div class="value-icon">⌖</div><h3>Жақыннан табыңыз</h3><p>Өз өңіріңіздегі кәсіптерді картадан ашып, орналасуын және өнімдерін көріңіз.</p></div><div><div class="value-icon">⇄</div><h3>Саналы салыстырыңыз</h3><p>Өлшем бірліктерін ескере отырып, ұсыныстар мен баға тарихын салыстырыңыз.</p></div><div><div class="value-icon">✧</div><h3>Деректен жауап алыңыз</h3><p>Көмекші платформаның жария деректерінен іздейді. API кілтінсіз де жұмыс істейді.</p></div></div></section><section class="section"><div class="cta"><div><h2>Кәсібіңізді картаға қосыңыз.</h2><p>Өнімдеріңізді таныстырып, жергілікті тұтынушыларға жақындай түсіңіз.</p></div><a href="${state.user ? (state.user.role === "user" ? "#/account" : "#/owner") : "#/register"}" class="btn">${state.user?.role === "user" ? "Кабинетке өту" : "Бастау"} ↗</a></div></section></div>`;
}
function listing(kind) {
  const isP = kind === "products";
  const f = state.listFilters;
  return `<section class="container page">${pageTitle(isP ? "Жергілікті өнімді таңдаңыз" : "Өңіріңіздің мүмкіндіктері", isP ? "Өнімдер нарығы" : "Кәсіптер каталогы", isP ? "Ұсыныстар, маусымдық өнімдер және ашық бағалар." : "Жергілікті өндірушілер мен қызметтерді бір жерден табыңыз.", `<a href="#/map" class="btn secondary">⌖ Картада көру</a>`)}${notice()}<form id="catalog-filter" class="filters" data-kind="${kind}"><input type="search" name="q" aria-label="Атауы бойынша іздеу" placeholder="Атауы бойынша іздеу…" value="${esc(f.q || "")}"><select name="category" aria-label="Санат">${options(isP ? ["vegetables", "fruit", "dairy", "grain", "honey", "meat"] : ["farm", "shop", "market", "service"], f.category)}</select><select name="location_id" aria-label="Елді мекен">${locationOptions(f.location_id)}</select><select name="sort" aria-label="Сұрыптау"><option value="name">Атауы бойынша</option>${isP ? '<option value="price_asc">Алдымен арзаны</option><option value="price_desc">Алдымен қымбаты</option>' : ""}<option value="newest">Алдымен жаңасы</option></select>${isP ? `<input type="number" name="min_price" min="0" placeholder="Ең төмен баға" aria-label="Ең төмен баға"><input type="number" name="max_price" min="0" placeholder="Ең жоғары баға" aria-label="Ең жоғары баға"><select name="unit" aria-label="Өлшем бірлігі"><option value="">Барлық өлшем</option><option>кг</option><option>л</option><option>дана</option><option>қап</option></select><label class="check"><input type="checkbox" name="seasonal" value="true"> Маусымдық өнімдер</label>` : ""}<button class="btn" type="submit">Іздеу</button><button class="btn text" type="button" data-action="reset-filters">Тазарту</button></form><div id="catalog-results"><div class="loading"><span class="spinner"></span>Іздеу жүріп жатыр…</div></div></section>`;
}
async function loadListing(kind, id = state.routeId) {
  const form = $("#catalog-filter");
  if (!form) return;
  const params = new URLSearchParams();
  for (const [key, value] of new FormData(form)) {
    if (value) params.set(key, value);
  }
  params.set("page", state.listPage);
  params.set("size", 12);
  const box = $("#catalog-results");
  box.innerHTML =
    '<div class="loading"><span class="spinner"></span>Деректер жүктелуде…</div>';
  try {
    const result = await api("/" + kind + "?" + params);
    if (id !== state.routeId || !box.isConnected) return;
    box.innerHTML = `<div class="result-count">${result.total} ${kind === "products" ? "өнім" : "кәсіп"} табылды</div><div class="grid">${result.items.map(kind === "products" ? productCard : businessCard).join("") || empty()}</div>${result.pages > 1 ? `<div class="pagination"><button class="btn secondary small" data-action="page" data-page="${result.page - 1}" ${result.page <= 1 ? "disabled" : ""}>← Алдыңғы</button><span>${result.page} / ${result.pages}</span><button class="btn secondary small" data-action="page" data-page="${result.page + 1}" ${result.page >= result.pages ? "disabled" : ""}>Келесі →</button></div>` : ""}`;
  } catch (e) {
    if (box.isConnected)
      box.innerHTML = empty(
        "Іздеу орындалмады",
        esc(e.message),
        '<button class="btn" data-action="retry-list">Қайталау</button>',
      );
  }
}
function mapPage(q) {
  return `<section class="container page">${pageTitle("Мүмкіндіктер картасы", "Өңіріңізді зерттеңіз", "Кәсіптер мен өнімдерді картадан табыңыз. Нүктені таңдап, мәліметін ашыңыз.")}<div class="map-layout"><aside class="panel map-sidebar"><form id="map-filter" class="map-controls"><div class="field full"><label for="map-q">Атауы немесе елді мекен</label><input id="map-q" name="q" type="search" value="${esc(q.get("q") || "")}" placeholder="Алматы, алма…"></div><div class="field"><label for="map-kind">Карта қабаты</label><select id="map-kind" name="kind"><option value="all">Барлық нүкте</option><option value="business">Кәсіптер</option><option value="product">Өнімдер</option></select></div><div class="field"><label for="map-category">Санат</label><select id="map-category" name="category">${options(Object.keys(cats))}</select></div><div class="field full"><label for="map-location">Елді мекен</label><select id="map-location" name="location_id">${locationOptions(q.get("location_id"))}</select></div><div class="field"><label for="map-radius">Жақын маң радиусы, км</label><input id="map-radius" name="radius_km" type="number" min="1" max="20000" value="50"></div><label class="check field"><span>Көрінетін аумақ</span><input id="map-bounds" type="checkbox" name="viewport" value="true"></label><button class="btn full" type="submit">Сүзгіні қолдану</button></form><button class="btn secondary" data-action="nearby">◎ Маған жақын жерлер</button><button class="btn text" data-action="map-reset">Шектеулерді тазарту</button><div class="notice">🌱 Кәсіптер · 🟡 Өнімдер<br>Демо нүктелер — расталған мекенжайлар емес.</div><div id="map-results" class="map-results"></div></aside><div class="map-shell"><div id="map" class="map-canvas" aria-label="Интерактивті карта"></div><div id="map-status" class="map-status" role="status">Карта жүктелуде…</div></div></div></section>`;
}
let mapSequence = 0,
  mapNear = null,
  mapMarkers = null,
  mapBusinesses = null,
  mapProducts = null,
  mapById = new Map();
async function initMap(query, id) {
  if (!window.L) {
    $("#map-status").textContent =
      "Карта кітапханасы табылмады. Бетті жаңартыңыз.";
    return;
  }
  mapNear = null;
  const map = L.map("map", {
    zoomControl: true,
    zoomAnimation: false,
    markerZoomAnimation: false,
  }).setView([44.1, 73.7], 5);
  state.map = map;
  const base = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      maxZoom: 19,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap қатысушылары</a>',
    },
  ).addTo(map);
  base.on("tileerror", () => {
    if ($("#map-status"))
      $("#map-status").textContent =
        "Карта фоны қолжетімсіз. Нүктелер мен іздеу жұмыс істей береді.";
  });
  mapBusinesses = L.layerGroup().addTo(map);
  mapProducts = L.layerGroup().addTo(map);
  L.control
    .layers(
      { OpenStreetMap: base },
      { Кәсіптер: mapBusinesses, Өнімдер: mapProducts },
      { collapsed: true },
    )
    .addTo(map);
  mapById = new Map();
  map.on("moveend", () => {
    if ($("#map-bounds")?.checked) {
      clearTimeout(state.mapTimer);
      state.mapTimer = setTimeout(() => loadMap(false, id), 300);
    }
  });
  const lat = Number(query.get("lat")),
    lon = Number(query.get("lon"));
  if (
    query.has("lat") &&
    query.has("lon") &&
    Number.isFinite(lat) &&
    Number.isFinite(lon)
  )
    map.setView([lat, lon], 12);
  await loadMap(!query.has("lat"), id);
}
async function loadMap(fit = false, id = state.routeId) {
  const form = $("#map-filter");
  if (!form || !state.map) return;
  const seq = ++mapSequence,
    params = new URLSearchParams();
  for (const [k, v] of new FormData(form))
    if (v && k !== "viewport") params.set(k, v);
  if (mapNear) {
    params.set("lat", mapNear.lat);
    params.set("lon", mapNear.lon);
  }
  if ($("#map-bounds").checked) {
    const b = state.map.getBounds();
    params.set(
      "bbox",
      [
        Math.max(-180, b.getWest()),
        Math.max(-90, b.getSouth()),
        Math.min(180, b.getEast()),
        Math.min(90, b.getNorth()),
      ].join(","),
    );
  }
  $("#map-status").textContent = "Нүктелер жүктелуде…";
  try {
    const data = await api("/map?" + params);
    if (id !== state.routeId || seq !== mapSequence || !state.map) return;
    mapBusinesses.clearLayers();
    mapProducts.clearLayers();
    mapById.clear();
    const points = [];
    for (const feature of data.features) {
      const p = feature.properties;
      const [lon, lat] = feature.geometry.coordinates;
      points.push([lat, lon]);
      const typ = p.kind;
      const icon = L.divIcon({
        className: "map-pin",
        html: `<div class="pin-inner ${typ === "product" ? "product-pin" : ""}"><span>${typ === "product" ? productIcons[p.name] || icons[p.category] : icons[p.category]}</span></div>`,
        iconSize: [34, 40],
        iconAnchor: [17, 36],
      });
      const marker = L.marker([lat, lon], { icon, title: p.name }).addTo(
        typ === "business" ? mapBusinesses : mapProducts,
      );
      marker.bindPopup(
        `${badge(p)}<br><strong>${esc(p.name)}</strong><br>${typ === "product" ? `${money(p.price)} ₸/${esc(p.unit)}` : esc(p.address)}<br><a href="#/${typ}/${p.id}">Толығырақ →</a>`,
      );
      mapById.set(feature.id, marker);
    }
    if (fit && points.length)
      state.map.fitBounds(points, { padding: [40, 40], maxZoom: 11 });
    $("#map-status").textContent =
      `${data.total} нүкте${data.truncated ? " · Алғашқы 1000 нүкте көрсетілді" : ""}`;
    $("#map-results").innerHTML =
      data.features
        .slice(0, 40)
        .map(
          (f) =>
            `<div class="map-item" role="button" tabindex="0" data-action="map-focus" data-id="${f.id}"><strong>${esc(f.properties.name)}</strong><small>${cats[f.properties.category]}${f.properties.distance_km !== null ? " · " + f.properties.distance_km + " км" : ""} · ${f.properties.is_demo ? "Демо" : "Пайдаланушы дерегі"}</small></div>`,
        )
        .join("") ||
      '<p class="subtle">Нүкте табылмады. Сүзгіні өзгертіңіз.</p>';
  } catch (e) {
    if ($("#map-status")) $("#map-status").textContent = e.message;
  }
}
function miniMap(b) {
  if (!window.L) return;
  state.map = L.map("detail-map", {
    scrollWheelZoom: false,
    zoomAnimation: false,
    markerZoomAnimation: false,
  }).setView([b.latitude, b.longitude], 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution:
      '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap қатысушылары</a>',
  }).addTo(state.map);
  L.marker([b.latitude, b.longitude], {
    icon: L.divIcon({
      className: "map-pin",
      html: '<div class="pin-inner"><span>🌱</span></div>',
      iconSize: [34, 40],
    }),
  })
    .addTo(state.map)
    .bindPopup(esc(b.name));
}
function productDetail(p) {
  const season = (m) =>
    p.season_start <= p.season_end
      ? m >= p.season_start && m <= p.season_end
      : m >= p.season_start || m <= p.season_end;
  return `<section class="container page"><div class="breadcrumbs"><a href="#/products">Өнімдер</a> / ${esc(p.name)}</div><div class="detail-grid"><div><div class="card-art detail-art" style="--art:${colors[p.category]}">${productIcons[p.name] || icons[p.category]}${badge(p)}</div><div class="panel space-top"><h2>Баға тарихы</h2><p class="subtle">₸/${esc(p.unit)} · ${p.is_demo ? "Демо баға нүктелері" : "Иесі енгізген бағалар"}</p><div class="chart-wrap"><canvas id="price-history" aria-label="Өнім бағасының тарихы" role="img"></canvas></div><details><summary class="subtle">Баға деректерін кестеден көру</summary><div class="table-wrap"><table><thead><tr><th>Күні</th><th>Баға</th></tr></thead><tbody>${p.history.map((h) => `<tr><td>${date(h.recorded_at)}</td><td>${money(h.price)} ₸/${esc(p.unit)}</td></tr>`).join("")}</tbody></table></div></details></div></div><div class="detail-content"><span class="badge">${cats[p.category]}</span><h1>${esc(p.name)}</h1><p>${esc(p.description)}</p><span class="price">${money(p.price)} ₸ <small>/ ${esc(p.unit)}</small></span><div class="inline-actions"><button class="btn" data-action="compare-add" data-id="${p.id}" data-product="${esc(JSON.stringify(p))}">⇄ Салыстыруға қосу</button><a class="btn secondary" href="#/map?lat=${p.latitude}&lon=${p.longitude}">⌖ Картада</a></div><div class="space-top"><div class="detail-row"><span>Сатушы</span><a href="#/business/${p.business_id}">${esc(p.business_name)} ↗</a></div><div class="detail-row"><span>Елді мекен</span><span>${esc(p.location_name)}</span></div><div class="detail-row"><span>Қор</span><span>${money(p.stock)} ${esc(p.unit)}</span></div><div class="detail-row"><span>Маусым</span><span>${p.in_season ? "Қазір маусымда" : "Қазір маусымнан тыс"}</span></div></div><div class="season-calendar" aria-label="Өнім маусымының айлары">${months.map((m, i) => `<span class="${season(i + 1) ? "on" : ""}">${m}</span>`).join("")}</div>${p.is_demo ? notice() : '<div class="notice">Баға мен қорды сатушыдан нақтылаңыз. Платформа төлем қабылдамайды.</div>'}<a class="link-arrow" href="#/assistant">✧ Өнім туралы көмекшіден сұраңыз →</a></div></div></section>`;
}
function businessDetail(b) {
  return `<section class="container page"><div class="breadcrumbs"><a href="#/businesses">Кәсіптер</a> / ${esc(b.name)}</div><div class="detail-grid"><div><div class="card-art detail-art" style="--art:${colors[b.category]}">${icons[b.category]}${badge(b)}</div><div id="detail-map" class="detail-map" aria-label="Кәсіптің орналасқан жері"></div></div><div class="detail-content"><span class="badge">${cats[b.category]}</span><h1>${esc(b.name)}</h1><p>${esc(b.description)}</p><div class="space-top"><div class="detail-row"><span>Елді мекен</span><span>${esc(b.location.name)}</span></div><div class="detail-row"><span>Мекенжай</span><span>${esc(b.address)}</span></div><div class="detail-row"><span>Телефон</span><span>${b.phone ? esc(b.phone) : "Көрсетілмеген"}</span></div><div class="detail-row"><span>Координаттар</span><span>${b.latitude.toFixed(4)}, ${b.longitude.toFixed(4)}</span></div>${b.website ? `<div class="detail-row"><span>Веб-сайт</span><a href="${esc(b.website)}" target="_blank" rel="noopener noreferrer">Сайтқа өту ↗</a></div>` : ""}</div><a class="btn space-top" href="#/map?lat=${b.latitude}&lon=${b.longitude}">Картада ашу ↗</a><div class="space-top">${b.is_demo ? notice() : ""}</div></div></div><section class="section space-top"><div class="section-heading"><h2>Кәсіп өнімдері</h2><span class="subtle">${b.products.length} ұсыныс</span></div><div class="grid">${b.products.map(productCard).join("") || empty("Әзірге өнім жоқ", "Кәсіптің жарияланған өнімі әлі жоқ.")}</div></section></section>`;
}
function dashboard(s) {
  return `<section class="container page">${pageTitle("Деректерге сүйенген шешім", "Өңірлік шолу", "Көрсеткіштер тек платформаның жарияланған жазбаларынан есептеледі.")}<div class="notice warn">${esc(s.notice)} Демо кәсіптер: ${s.demo_businesses}; демо өнімдер: ${s.demo_products}. Жаңартылған уақыты: ${date(s.generated_at)}.</div><div class="dashboard-stats">${[
    ["Кәсіптер", s.businesses, "Жарияланған жазбалар", "⌖"],
    ["Өнімдер", s.products, "Барлық жария ұсыныс", "🧺"],
    ["Маусымдық өнім", s.seasonal_products, "Осы айдағы маусым", "🌱"],
    ["Өңірлер", s.regions, "Платформа қамтуы", "↗"],
  ]
    .map(
      ([label, n, sub, icon]) =>
        `<div class="stat-card"><div class="stat-top"><span>${label}</span><span>${icon}</span></div><strong>${n}</strong><small>${sub}</small></div>`,
    )
    .join(
      "",
    )}</div><div class="chart-grid"><div class="panel"><h2>Кәсіптер санаттары</h2><div class="chart-wrap"><canvas id="categories-chart" role="img" aria-label="Санаттар бойынша кәсіп саны"></canvas></div></div><div class="panel"><h2>Өңірлердегі кәсіп саны</h2><div class="chart-wrap"><canvas id="regions-chart" role="img" aria-label="Өңір бойынша кәсіп саны"></canvas></div></div></div><div class="panel"><div class="owner-heading"><h2>Өнім бағаларын салыстыру</h2><span class="subtle">Валюта: KZT (₸)</span></div><p class="subtle">Атауы мен өлшем бірлігі бірдей ұсыныстар ғана біріктірілген. Сапасы мен сорты әртүрлі болуы мүмкін.</p><div class="table-wrap space-top"><table><thead><tr><th>Өнім</th><th>Өлшем</th><th>Ең төмен</th><th>Ең жоғары</th><th>Орташа</th><th>Ұсыныс саны</th></tr></thead><tbody>${s.price_comparison.map((p) => `<tr><td>${esc(p.name)}</td><td>${esc(p.unit)}</td><td>${money(p.min)} ₸</td><td>${money(p.max)} ₸</td><td>${money(p.average)} ₸</td><td>${p.offers}</td></tr>`).join("") || '<tr><td colspan="6" class="table-empty">Дерек жоқ</td></tr>'}</tbody></table></div></div><div class="panel"><h2>Көрсеткіштердің негізі</h2><div class="table-wrap"><table><thead><tr><th>Кәсіп санаты</th><th>Саны</th></tr></thead><tbody>${Object.entries(
    s.business_categories,
  )
    .map(([k, v]) => `<tr><td>${cats[k]}</td><td>${v}</td></tr>`)
    .join(
      "",
    )}</tbody></table><table><thead><tr><th>Өңір</th><th>Кәсіп саны</th></tr></thead><tbody>${Object.entries(
    s.businesses_by_region,
  )
    .map(([k, v]) => `<tr><td>${esc(k)}</td><td>${v}</td></tr>`)
    .join("")}</tbody></table></div></div></section>`;
}
function dashboardCharts(s) {
  drawChart(
    "categories-chart",
    "doughnut",
    {
      labels: Object.keys(s.business_categories).map((k) => cats[k]),
      datasets: [
        {
          data: Object.values(s.business_categories),
          backgroundColor: ["#163f32", "#90b874", "#d9f397", "#e9b66b"],
          borderWidth: 4,
          borderColor: "#fff",
        },
      ],
    },
    { cutout: "70%" },
  );
  drawChart(
    "regions-chart",
    "bar",
    {
      labels: Object.keys(s.businesses_by_region),
      datasets: [
        {
          label: "Кәсіп саны",
          data: Object.values(s.businesses_by_region),
          backgroundColor: "#90b874",
          borderRadius: 6,
        },
      ],
    },
    {
      indexAxis: "y",
      scales: {
        x: { beginAtZero: true, ticks: { precision: 0 } },
        y: { grid: { display: false }, ticks: { font: { size: 10 } } },
      },
    },
  );
}
function authPage(kind) {
  const register = kind === "register";
  return `<section class="container page"><div class="auth-layout"><div class="auth-side"><div><div class="eyebrow" style="color:var(--lime)">Бірге өсейік</div><h2>Өз өңіріңізбен<br>жақындай түсіңіз.</h2><p>Жергілікті кәсіптерді зерттеңіз немесе өз өніміңізді таныстырыңыз.</p></div><div class="sprout">🌱</div><small>HarvestMap AI · Жергілікті мүмкіндіктер картасы</small></div><div class="auth-form"><h1>${register ? "Тіркелгі жасау" : "Қайта қош келдіңіз"}</h1><p>${register ? "Жергілікті мүмкіндіктерге алғашқы қадам." : "Жеке кабинетіңізге кіріңіз."}</p><form id="auth-form" data-kind="${kind}">${register ? '<div class="field"><label for="name">Аты-жөніңіз</label><input id="name" name="name" required minlength="2" maxlength="100" autocomplete="name"></div>' : ""}<div class="field"><label for="email">Электрондық пошта</label><input id="email" name="email" type="email" required maxlength="254" autocomplete="email" placeholder="siz@mysal.kz"></div><div class="field"><label for="password">Құпиясөз</label><input id="password" name="password" type="password" required minlength="${register ? 10 : 1}" maxlength="128" autocomplete="${register ? "new-password" : "current-password"}">${register ? "<small>Кемінде 10 таңба. Басқа сайттағы құпиясөзді қолданбаңыз.</small>" : ""}</div>${register ? '<div class="field"><label for="role">Тіркелгі түрі</label><select id="role" name="role"><option value="user">Өнім іздеймін</option><option value="owner">Кәсіп иесімін</option></select></div>' : ""}<div class="form-error" role="alert"></div><button class="btn" type="submit">${register ? "Тіркелу" : "Кіру"} →</button></form><div class="auth-switch">${register ? 'Тіркелгіңіз бар ма? <a href="#/login">Кіріңіз</a>' : 'Әлі тіркелмедіңіз бе? <a href="#/register">Тіркеліңіз</a>'}</div></div></div></section>`;
}
function accountPage() {
  const u = state.user;
  return `<section class="container page">${pageTitle("Сіздің кеңістігіңіз", "Жеке кабинет", "Тіркелгіңіз бен қауіпсіздік параметрлерін басқарыңыз.")}<div class="account-grid"><aside class="panel account-card"><div class="account-avatar">${esc(u.name[0].toUpperCase())}</div><h3>${esc(u.name)}</h3><p>${esc(u.email)}</p><span class="badge">${roleLabel[u.role]}</span>${u.role !== "user" ? '<a href="#/owner" class="btn">Кәсіптерімді басқару ↗</a>' : '<p class="space-top subtle">Кәсіп қосу үшін әкімшіден кәсіп иесі рөлін сұраңыз.</p>'}${u.role === "admin" ? '<a href="#/admin" class="btn secondary">Әкімші панелі</a>' : ""}<button class="btn secondary" data-action="logout">Жүйеден шығу</button></aside><div><div class="panel"><h2>Жеке мәліметтер</h2><form id="profile-form"><div class="field"><label for="profile-name">Аты-жөніңіз</label><input id="profile-name" name="name" value="${esc(u.name)}" required minlength="2" maxlength="100"></div><p class="form-note">Электрондық пошта: ${esc(u.email)}. Бұл нұсқада пошта мекенжайын өзгерту қолжетімсіз.</p><div class="form-error" role="alert"></div><button class="btn" type="submit">Өзгерістерді сақтау</button></form></div><div class="panel"><h2>Құпиясөзді жаңарту</h2><form id="password-form"><div class="form-grid"><div class="field"><label for="current-password">Қазіргі құпиясөз</label><input id="current-password" name="current_password" type="password" required maxlength="128" autocomplete="current-password"></div><div class="field"><label for="new-password">Жаңа құпиясөз</label><input id="new-password" name="new_password" type="password" required minlength="10" maxlength="128" autocomplete="new-password"></div></div><p class="form-note">Өзгерткеннен кейін басқа құрылғылардағы сессиялар аяқталады.</p><div class="form-error" role="alert"></div><button class="btn secondary" type="submit">Құпиясөзді жаңарту</button></form></div></div></div></section>`;
}
function ownerPage() {
  const c = state.catalog;
  return `<section class="container page">${pageTitle("Кәсіп иесінің кабинеті", "Кәсібіңізді дамытыңыз", "Кәсіп пен өнімдерді қосыңыз, бағалар мен қорды жаңартыңыз.", '<a href="#/account" class="btn secondary">Жеке кабинет</a>')}<div class="notice">Жаңа жазба және өңделген мәліметтер жарияланбас бұрын әкімші тексеруінен өтеді.</div><div class="panel"><div class="owner-heading"><h2>Кәсіптерім</h2><button class="btn small" data-action="business-form">+ Кәсіп қосу</button></div>${c.businesses.length ? `<div class="table-wrap"><table><thead><tr><th>Кәсіп атауы</th><th>Елді мекен</th><th>Мәртебе</th><th>Әрекеттер</th></tr></thead><tbody>${c.businesses.map((b) => `<tr><td>${esc(b.name)}</td><td>${esc(b.location.name)}</td><td>${status(b)}</td><td class="actions"><button class="btn secondary small" data-action="business-form" data-id="${b.id}">Өңдеу</button><button class="btn danger small" data-action="delete" data-kind="businesses" data-id="${b.id}">Жою</button></td></tr>`).join("")}</tbody></table></div>` : empty("Алғашқы кәсібіңізді қосыңыз", "Жариялау үшін мәліметтерді толтырып, тексеруге жіберіңіз.")} </div><div class="panel"><div class="owner-heading"><h2>Өнімдерім</h2><button class="btn small" data-action="product-form" ${!c.businesses.length ? "disabled" : ""}>+ Өнім қосу</button></div>${c.products.length ? `<div class="table-wrap"><table><thead><tr><th>Өнім</th><th>Баға</th><th>Кәсіп</th><th>Мәртебе</th><th>Әрекеттер</th></tr></thead><tbody>${c.products.map((p) => `<tr><td>${esc(p.name)}</td><td>${money(p.price)} ₸/${esc(p.unit)}</td><td>${esc(p.business_name)}</td><td>${status(p)}</td><td class="actions"><button class="btn secondary small" data-action="product-form" data-id="${p.id}">Өңдеу</button><button class="btn danger small" data-action="delete" data-kind="products" data-id="${p.id}">Жою</button></td></tr>`).join("")}</tbody></table></div>` : empty("Әзірге өнім жоқ", "Кәсіпті қосқаннан кейін өнімдеріңізді енгізе аласыз.")}</div></section>`;
}
function openModal(title, content) {
  $("#modal-title").textContent = title;
  $("#modal-content").innerHTML = content;
  $("#modal").showModal();
}
function field(name, label, value = "", type = "text", attrs = "") {
  return `<div class="field"><label for="f-${name}">${label}</label><input id="f-${name}" type="${type}" name="${name}" value="${esc(value)}" ${attrs}></div>`;
}
function businessForm(id) {
  const b = state.catalog.businesses.find((x) => x.id === Number(id)) || {};
  openModal(
    b.id ? "Кәсіпті өңдеу" : "Кәсіп қосу",
    `<form id="business-form" data-id="${b.id || ""}"><div class="form-grid">${field("name", "Кәсіп атауы", b.name, "text", 'required minlength="2" maxlength="150"')}<div class="field"><label for="f-category">Санат</label><select id="f-category" name="category" required>${options(["farm", "shop", "market", "service"], b.category, "Санатты таңдаңыз")}</select></div><div class="field full"><label for="f-description">Сипаттама</label><textarea id="f-description" name="description" required minlength="10" maxlength="6000">${esc(b.description || "")}</textarea></div><div class="field"><label for="f-location">Елді мекен</label><select id="f-location" name="location_id" required><option value="">Елді мекенді таңдаңыз</option>${state.locations.map((l) => `<option value="${l.id}" ${b.location_id === l.id ? "selected" : ""}>${esc(l.name)}</option>`).join("")}</select></div>${field("address", "Мекенжай", b.address, "text", 'required minlength="3" maxlength="250"')}${field("phone", "Телефон", b.phone, "tel", 'maxlength="40"')}${field("website", "Веб-сайт (міндетті емес)", b.website, "url", 'maxlength="300"')}${field("latitude", "Ендік (−90…90)", b.latitude ?? 43.2389, "number", 'required min="-90" max="90" step="any"')}${field("longitude", "Бойлық (−180…180)", b.longitude ?? 76.8897, "number", 'required min="-180" max="180" step="any"')}</div><p class="form-note">Координаттарды картадан анықтаңыз. Елді мекен таңдалғанда оның орталығы ұсынылады. Өзгерістер қайта тексеріледі.</p><div class="form-error" role="alert"></div><button class="btn" type="submit">Сақтау және тексеруге жіберу</button></form>`,
  );
}
function productForm(id) {
  const p = state.catalog.products.find((x) => x.id === Number(id)) || {};
  openModal(
    p.id ? "Өнімді өңдеу" : "Өнім қосу",
    `<form id="product-form" data-id="${p.id || ""}"><div class="form-grid">${field("name", "Өнім атауы", p.name, "text", 'required minlength="2" maxlength="150"')}<div class="field"><label for="f-category">Санат</label><select id="f-category" name="category" required>${options(["vegetables", "fruit", "dairy", "grain", "honey", "meat"], p.category, "Санатты таңдаңыз")}</select></div><div class="field full"><label for="f-business">Кәсіп</label><select id="f-business" name="business_id" required>${state.catalog.businesses.map((b) => `<option value="${b.id}" ${p.business_id === b.id ? "selected" : ""}>${esc(b.name)}</option>`).join("")}</select></div><div class="field full"><label for="f-description">Сипаттама</label><textarea id="f-description" name="description" required minlength="10" maxlength="6000">${esc(p.description || "")}</textarea></div>${field("price", "Бағасы, ₸", p.price ?? "", "number", 'required min="0.01" max="1000000000" step="0.01"')}<div class="field"><label for="f-unit">Өлшем бірлігі</label><select id="f-unit" name="unit">${["кг", "л", "дана", "қап"].map((u) => `<option ${p.unit === u ? "selected" : ""}>${u}</option>`).join("")}</select></div>${field("stock", "Қор көлемі", p.stock ?? 0, "number", 'required min="0" max="1000000000" step="0.01"')}<div class="field"><label for="f-start">Маусымның басталуы</label><select id="f-start" name="season_start">${months.map((m, i) => `<option value="${i + 1}" ${(p.season_start || 1) === i + 1 ? "selected" : ""}>${i + 1} · ${m}</option>`).join("")}</select></div><div class="field"><label for="f-end">Маусымның аяқталуы</label><select id="f-end" name="season_end">${months.map((m, i) => `<option value="${i + 1}" ${(p.season_end || 12) === i + 1 ? "selected" : ""}>${i + 1} · ${m}</option>`).join("")}</select></div></div><p class="form-note">Баға өзгерістері тарихқа автоматты түрде жазылады. Қысты қамтитын маусымға, мысалы, 11–3 аралығын көрсетуге болады.</p><div class="form-error" role="alert"></div><button class="btn" type="submit">Сақтау және тексеруге жіберу</button></form>`,
  );
}
function adminPage(queue, users) {
  return `<section class="container page">${pageTitle("Әкімші панелі", "Сапа мен сенімділік", "Жазбаларды тексеріңіз, рөлдер мен елді мекендерді басқарыңыз.", '<a href="#/owner" class="btn secondary">Барлық жазбаны өңдеу</a>')}<div class="panel"><h2>Кәсіптерді тексеру</h2>${moderationTable(queue.businesses, "businesses")}</div><div class="panel"><h2>Өнімдерді тексеру</h2>${moderationTable(queue.products, "products")}</div><div class="panel"><h2>Пайдаланушылар</h2><div class="table-wrap"><table><thead><tr><th>Аты-жөні</th><th>Пошта</th><th>Рөл</th><th>Белсенділік</th><th>Сақтау</th></tr></thead><tbody>${users.map((u) => `<tr><td>${esc(u.name)}</td><td>${esc(u.email)}</td><td><select aria-label="${esc(u.name)} рөлі" id="role-${u.id}" ${u.id === state.user.id ? "disabled" : ""}>${["user", "owner", "admin"].map((r) => `<option value="${r}" ${u.role === r ? "selected" : ""}>${roleLabel[r]}</option>`).join("")}</select></td><td><label><input type="checkbox" id="active-${u.id}" aria-label="Белсенді тіркелгі" ${u.is_active ? "checked" : ""} ${u.id === state.user.id ? "disabled" : ""}> Белсенді</label></td><td><button class="btn secondary small" data-action="user-save" data-id="${u.id}" ${u.id === state.user.id ? "disabled" : ""}>Сақтау</button></td></tr>`).join("")}</tbody></table></div></div><div class="panel"><div class="owner-heading"><h2>Елді мекендер</h2><button class="btn small" data-action="location-form">+ Елді мекен</button></div><div class="table-wrap"><table><thead><tr><th>Атауы</th><th>Өңір</th><th>Координаттар</th><th>Әрекеттер</th></tr></thead><tbody>${state.locations.map((l) => `<tr><td>${esc(l.name)}</td><td>${esc(l.region)}</td><td>${l.latitude}, ${l.longitude}</td><td class="actions"><button class="btn secondary small" data-action="location-form" data-id="${l.id}">Өңдеу</button><button class="btn danger small" data-action="delete" data-kind="locations" data-id="${l.id}">Жою</button></td></tr>`).join("")}</tbody></table></div></div></section>`;
}
function moderationTable(items, kind) {
  if (!items.length)
    return '<p class="subtle">Тексерілетін жазба жоқ. Барлығы реттелген ✓</p>';
  return `<div class="table-wrap"><table><thead><tr><th>Жазба</th><th>Мәлімет</th><th>Мәртебе</th><th>Шешім</th></tr></thead><tbody>${items.map((x) => `<tr><td>${esc(x.name)}<br><small>${esc(x.description.slice(0, 130))}</small></td><td>${kind === "products" ? money(x.price) + " ₸/" + esc(x.unit) : esc(x.address)}<br><small>${kind === "products" ? esc(x.business_name) : esc(x.location.name)}</small></td><td>${status(x)}</td><td class="actions"><button class="btn small" data-action="moderate" data-kind="${kind}" data-id="${x.id}" data-status="approved">Жариялау</button><button class="btn danger small" data-action="moderate" data-kind="${kind}" data-id="${x.id}" data-status="rejected">Қабылдамау</button></td></tr>`).join("")}</tbody></table></div>`;
}
function locationForm(id) {
  const l = state.locations.find((l) => l.id === Number(id)) || {};
  openModal(
    l.id ? "Елді мекенді өңдеу" : "Елді мекен қосу",
    `<form id="location-form" data-id="${l.id || ""}"><div class="form-grid">${field("name", "Атауы", l.name, "text", 'required minlength="2" maxlength="120"')}${field("region", "Өңір", l.region, "text", 'required minlength="2" maxlength="120"')}${field("latitude", "Ендік", l.latitude ?? 43.2389, "number", 'required min="-90" max="90" step="any"')}${field("longitude", "Бойлық", l.longitude ?? 76.8897, "number", 'required min="-180" max="180" step="any"')}</div><div class="form-error" role="alert"></div><button class="btn" type="submit">Сақтау</button></form>`,
  );
}
function assistantPage() {
  return `<section class="container page">${pageTitle("Сұраңыз. Табыңыз. Танысыңыз.", "Деректерге негізделген көмекші", "Платформадағы жария кәсіптер, өнімдер, бағалар мен өңірлер туралы сұраңыз.")}<div class="assistant-layout"><aside class="assistant-side"><h2>Іздеуді<br>жеңілдетейік.</h2><p>Өнім атауын, елді мекенді немесе өзіңізге қажет мәліметті жазыңыз.</p><button data-action="prompt" data-prompt="Алматыда қандай кәсіптер бар">⌖ Алматыдағы кәсіптер</button><button data-action="prompt" data-prompt="Қызанақ бағасы">🍅 Қызанақ бағасы</button><button data-action="prompt" data-prompt="Маусымдық өнімдер">🌱 Маусымдық өнімдер</button><button data-action="prompt" data-prompt="Платформа статистикасы қанша">↗ Платформа статистикасы</button><small>API кілті болмаса, дерекқор бойынша іздеу автоматты түрде қолданылады. Жеке деректерді жазбаңыз.</small></aside><div class="panel chat-panel"><div class="chat-header"><span class="assistant-icon">✧</span><div><strong>HarvestMap көмекшісі</strong><small>Тек платформаның жария деректеріне сүйенеді</small></div></div><div id="chat-messages" class="chat-messages" role="log" aria-live="polite"><div class="message bot">Сәлеметсіз бе! Қандай өнім немесе кәсіп іздеп жүрсіз? Мысалы, «Қызанақ бағасы» немесе «Талғардағы кәсіптер» деп жазыңыз.<div class="mode">Демо жазбалар нақты нарық деректері емес.</div></div></div><form id="chat-form" class="chat-form"><input name="message" type="text" required minlength="2" maxlength="1500" aria-label="Көмекшіге сұрақ" placeholder="Сұрағыңызды жазыңыз…" autocomplete="off"><button type="submit" class="btn">Жіберу ↑</button></form><p class="chat-disclaimer">Жауаптағы бағаларды сатушыдан нақтылаңыз. AI жауаптары қате болуы мүмкін.</p></div></div></section>`;
}
async function askAssistant(message) {
  const messages = $("#chat-messages");
  const form = $("#chat-form");
  if (!messages || form.dataset.busy) return;
  form.dataset.busy = "true";
  const btn = $("button", form);
  btn.disabled = true;
  messages.insertAdjacentHTML(
    "beforeend",
    `<div class="message user">${esc(message)}</div><div class="message bot thinking"><span class="spinner"></span>Деректерді қарап жатырмын…</div>`,
  );
  messages.scrollTop = messages.scrollHeight;
  try {
    const data = await send("/assistant", { message });
    if (messages.isConnected)
      $(".thinking", messages).outerHTML =
        `<div class="message bot">${esc(data.answer)}<div class="source-links">${data.sources.map((s) => `<a href="${esc(s.url)}">${esc(s.label)}${s.is_demo ? " · демо" : ""} ↗</a>`).join("")}</div><div class="mode">${esc(data.notice)}</div></div>`;
  } catch (e) {
    if (messages.isConnected) $(".thinking", messages).textContent = e.message;
  } finally {
    delete form.dataset.busy;
    btn.disabled = false;
    messages.scrollTop = messages.scrollHeight;
  }
}
function updateCompareTray() {
  $(".compare-tray")?.remove();
  const count = state.compare.size;
  if (!count) return;
  document.body.insertAdjacentHTML(
    "beforeend",
    `<div class="compare-tray"><span>⇄ ${count} өнім таңдалды</span><button class="btn lime small" data-action="compare-open">Салыстыру</button><button class="btn secondary small" data-action="compare-clear">Тазарту</button></div>`,
  );
}
function compareOpen() {
  const products = [...state.compare.values()];
  const same = products.every(
    (p) => p.unit === products[0].unit && p.name === products[0].name,
  );
  openModal(
    "Өнімдерді салыстыру",
    `<div class="notice ${same ? "" : "warn"}">${same ? "Атауы мен өлшем бірлігі бірдей. Сапасы немесе сорты өзгеше болуы мүмкін." : "Әртүрлі өнім немесе өлшем бірлігі таңдалған. Ең арзан ұсынысты тікелей анықтау дұрыс емес."}</div><div class="table-wrap"><table><thead><tr><th>Көрсеткіш</th>${products.map((p) => `<th><a href="#/product/${p.id}" data-action="close-modal">${esc(p.name)} ↗</a></th>`).join("")}</tr></thead><tbody><tr><td>Баға</td>${products.map((p) => `<td>${money(p.price)} ₸/${esc(p.unit)}</td>`).join("")}</tr><tr><td>Сатушы</td>${products.map((p) => `<td>${esc(p.business_name)}</td>`).join("")}</tr><tr><td>Елді мекен</td>${products.map((p) => `<td>${esc(p.location_name)}</td>`).join("")}</tr><tr><td>Қор</td>${products.map((p) => `<td>${money(p.stock)} ${esc(p.unit)}</td>`).join("")}</tr><tr><td>Дерек</td>${products.map((p) => `<td>${badge(p)}</td>`).join("")}</tr></tbody></table></div>`,
  );
}
async function refreshLocations() {
  state.locations = await api("/locations");
}
async function handleForm(form) {
  const data = Object.fromEntries(new FormData(form));
  const button = $("button[type=submit]", form),
    err = $(".form-error", form);
  if (err) err.textContent = "";
  button.disabled = true;
  const old = button.textContent;
  button.textContent = "Күте тұрыңыз…";
  try {
    if (form.id === "auth-form") {
      const result = await send("/auth/" + form.dataset.kind, data);
      state.user = result.user;
      authNav();
      toast("Қош келдіңіз, " + result.user.name + "!");
      location.hash = "/account";
    } else if (form.id === "profile-form") {
      state.user = await send("/auth/me", data, "PATCH");
      authNav();
      toast("Жеке мәліметтер сақталды");
      await route();
    } else if (form.id === "password-form") {
      await send("/auth/password", data);
      form.reset();
      toast("Құпиясөз жаңартылды");
    } else if (
      ["business-form", "product-form", "location-form"].includes(form.id)
    ) {
      const kind = {
        "business-form": "businesses",
        "product-form": "products",
        "location-form": "locations",
      }[form.id];
      for (const key of [
        "latitude",
        "longitude",
        "location_id",
        "business_id",
        "price",
        "stock",
        "season_start",
        "season_end",
      ])
        if (key in data) data[key] = Number(data[key]);
      await send(
        "/" + kind + (form.dataset.id ? "/" + form.dataset.id : ""),
        data,
        form.dataset.id ? "PUT" : "POST",
      );
      $("#modal").close();
      if (kind === "locations") await refreshLocations();
      toast(
        kind === "locations"
          ? "Елді мекен сақталды"
          : "Жазба тексеруге жіберілді",
      );
      await route();
    }
  } catch (e) {
    if (err) err.textContent = e.message;
    else toast(e.message, true);
  } finally {
    button.disabled = false;
    button.textContent = old;
  }
}
document.addEventListener("submit", async (e) => {
  const form = e.target;
  if (!(form instanceof HTMLFormElement)) return;
  e.preventDefault();
  if (form.id === "home-search") {
    const query = new URLSearchParams(new FormData(form));
    location.hash = "/products?" + query;
  } else if (form.id === "catalog-filter") {
    state.listPage = 1;
    await loadListing(form.dataset.kind);
  } else if (form.id === "map-filter") {
    const loc = state.locations.find(
      (l) => String(l.id) === form.location_id.value,
    );
    if (loc && state.map) state.map.setView([loc.latitude, loc.longitude], 11);
    await loadMap(!$("#map-bounds").checked);
  } else if (form.id === "chat-form") {
    const input = $("input", form);
    const text = input.value.trim();
    if (text.length < 2) return;
    input.value = "";
    await askAssistant(text);
  } else if (form.id === "delete-form") {
    const btn = $("button[type=submit]", form);
    btn.disabled = true;
    try {
      await api("/" + form.dataset.kind + "/" + form.dataset.id, {
        method: "DELETE",
      });
      $("#modal").close();
      if (form.dataset.kind === "locations") await refreshLocations();
      toast("Жазба жойылды");
      await route();
    } catch (error) {
      $(".form-error", form).textContent = error.message;
      btn.disabled = false;
    }
  } else await handleForm(form);
});
document.addEventListener("change", (e) => {
  if (e.target.id === "f-location") {
    const l = state.locations.find((l) => l.id === Number(e.target.value));
    if (l) {
      $("#f-latitude").value = l.latitude;
      $("#f-longitude").value = l.longitude;
    }
  }
});
document.addEventListener("keydown", (e) => {
  if ((e.key === "Enter" || e.key === " ") && e.target.matches(".map-item")) {
    e.preventDefault();
    e.target.click();
  }
});
document.addEventListener("click", async (e) => {
  const el = e.target.closest("[data-action]");
  if (!el || el.disabled) return;
  const action = el.dataset.action;
  try {
    if (action === "menu") {
      const nav = $("#navigation");
      nav.classList.toggle("open");
      el.setAttribute("aria-expanded", nav.classList.contains("open"));
    } else if (action === "close-modal") $("#modal").close();
    else if (action === "retry") await route();
    else if (action === "retry-list")
      await loadListing($("#catalog-filter").dataset.kind);
    else if (action === "page") {
      state.listPage = Number(el.dataset.page);
      await loadListing($("#catalog-filter").dataset.kind);
      $("#catalog-filter").scrollIntoView({ block: "start" });
    } else if (action === "reset-filters") {
      const f = $("#catalog-filter");
      f.reset();
      $("[name=q]", f).value = "";
      $("[name=location_id]", f).value = "";
      $("[name=category]", f).value = "";
      state.listPage = 1;
      await loadListing(f.dataset.kind);
    } else if (action === "logout") {
      await api("/auth/logout", { method: "POST" });
      state.user = null;
      authNav();
      toast("Жүйеден шықтыңыз");
      location.hash = "/";
    } else if (action === "business-form") businessForm(el.dataset.id);
    else if (action === "product-form") productForm(el.dataset.id);
    else if (action === "location-form") locationForm(el.dataset.id);
    else if (action === "delete") {
      openModal(
        "Жазбаны жою",
        `<form id="delete-form" data-kind="${esc(el.dataset.kind)}" data-id="${Number(el.dataset.id)}"><p>Жазбаны біржола жоюды растайсыз ба? Кәсіпті жойсаңыз, оның өнімдері мен баға тарихы да жойылады.</p><div class="form-error" role="alert"></div><div class="inline-actions"><button class="btn danger" type="submit">Иә, жою</button><button class="btn secondary" type="button" data-action="close-modal">Бас тарту</button></div></form>`,
      );
    } else if (action === "moderate") {
      el.disabled = true;
      await send(
        `/admin/${el.dataset.kind}/${el.dataset.id}/status`,
        { status: el.dataset.status },
        "PATCH",
      );
      toast("Шешім сақталды");
      await route();
    } else if (action === "user-save") {
      el.disabled = true;
      await send(
        "/admin/users/" + el.dataset.id,
        {
          role: $("#role-" + el.dataset.id).value,
          is_active: $("#active-" + el.dataset.id).checked,
        },
        "PATCH",
      );
      toast("Пайдаланушы параметрлері сақталды");
    } else if (action === "prompt") await askAssistant(el.dataset.prompt);
    else if (action === "nearby") {
      if (!navigator.geolocation) {
        toast("Бұл браузер орналасқан жерді анықтауды қолдамайды", true);
        return;
      }
      el.disabled = true;
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          el.disabled = false;
          if (!state.map) return;
          mapNear = { lat: pos.coords.latitude, lon: pos.coords.longitude };
          state.map.setView([mapNear.lat, mapNear.lon], 11);
          await loadMap(true);
        },
        () => {
          el.disabled = false;
          toast(
            "Орналасқан жерді анықтау мүмкін болмады. Браузер рұқсатын тексеріңіз немесе елді мекенді таңдаңыз.",
            true,
          );
        },
        { timeout: 10000, maximumAge: 60000 },
      );
    } else if (action === "map-reset") {
      mapNear = null;
      $("#map-filter").reset();
      $("#map-q").value = "";
      $("#map-location").value = "";
      await loadMap(true);
    } else if (action === "map-focus") {
      const marker = mapById.get(el.dataset.id);
      if (marker && state.map) {
        const group = el.dataset.id.startsWith("product")
          ? mapProducts
          : mapBusinesses;
        if (!state.map.hasLayer(group)) group.addTo(state.map);
        state.map.setView(marker.getLatLng(), 13);
        marker.openPopup();
      }
    } else if (action === "compare-add") {
      const p = JSON.parse(el.dataset.product);
      if (state.compare.has(p.id)) {
        state.compare.delete(p.id);
        el.classList.remove("selected");
        el.setAttribute("aria-pressed", "false");
        if (el.classList.contains("compare-toggle"))
          el.textContent = "+ Салыстыру";
      } else {
        if (state.compare.size >= 4) {
          toast("Бір уақытта ең көбі 4 өнімді салыстыруға болады");
          return;
        }
        state.compare.set(p.id, p);
        el.classList.add("selected");
        el.setAttribute("aria-pressed", "true");
        if (el.classList.contains("compare-toggle"))
          el.textContent = "✓ Қосылды";
        toast("Өнім салыстыруға қосылды");
      }
      updateCompareTray();
    } else if (action === "compare-clear") {
      state.compare.clear();
      $$(".compare-toggle").forEach((b) => {
        b.classList.remove("selected");
        b.textContent = "+ Салыстыру";
        b.setAttribute("aria-pressed", "false");
      });
      updateCompareTray();
    } else if (action === "compare-open") compareOpen();
  } catch (error) {
    toast(error.message, true);
  } finally {
    if (el.isConnected && ["moderate", "user-save"].includes(action))
      el.disabled = false;
  }
});
window.addEventListener("hashchange", route);
async function boot() {
  $("#year").textContent = new Date().getFullYear();
  try {
    state.user = await api("/auth/me");
  } catch {
    state.user = null;
  }
  authNav();
  try {
    await refreshLocations();
  } catch (e) {
    toast(e.message, true);
  }
  await route();
}
boot();

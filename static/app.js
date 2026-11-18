const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (n) => Number(n).toLocaleString("ru-RU") + " ₸";
const tr = {
  sleep: { early: "рано ложится", late: "поздно ложится" },
  cleanliness: { tidy: "аккуратный", moderate: "средне", messy: "не парится" },
  social: { quiet: "тихий", moderate: "умеренно", social: "общительный" },
};

const favKey = "pt_fav";
const getFav = () => { try { return JSON.parse(localStorage.getItem(favKey)) || []; } catch { return []; } };
const setFav = (a) => { try { localStorage.setItem(favKey, JSON.stringify(a)); } catch {} };

async function api(url, options) {
  const r = await fetch(url, options);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || "Ошибка запроса");
  return d;
}
const post = (url, body) => api(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

let toastTimer;
function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 2500);
}

document.querySelectorAll("#tabs button").forEach((b) => {
  b.addEventListener("click", () => {
    document.querySelectorAll("#tabs button").forEach((x) => x.classList.toggle("on", x === b));
    document.querySelectorAll("main > section").forEach((s) => { s.hidden = s.id !== "tab-" + b.dataset.tab; });
    if (b.dataset.tab === "mates") loadMatches();
    if (b.dataset.tab === "stats") loadStats();
  });
});

function listingCard(x, fav) {
  return `<article class="card">
    <div class="row"><h3>${esc(x.title)}</h3><button class="star ${fav ? "on" : ""}" data-fav="${x.id}" title="В избранное">★</button></div>
    <p class="muted">${esc(x.city)}, ${esc(x.district)} · ${x.rooms} комн.</p>
    <p class="price">${money(x.price)}<small> / мес</small></p>
    <p>${esc(x.description)}</p>
    <button class="btn" data-ask="${x.id}" data-title="${esc(x.title)}">Откликнуться</button>
  </article>`;
}

async function loadListings() {
  const p = new URLSearchParams();
  const map = [["q", "f-q"], ["city", "f-city"], ["district", "f-district"], ["min_price", "f-min"], ["max_price", "f-max"], ["rooms", "f-rooms"], ["sort", "f-sort"]];
  for (const [k, id] of map) {
    const v = $("#" + id).value.trim();
    if (v) p.set(k, v);
  }
  try {
    let items = await api("/api/listings?" + p);
    const fav = getFav();
    if ($("#f-fav").checked) items = items.filter((x) => fav.includes(x.id));
    $("#list").innerHTML = items.map((x) => listingCard(x, fav.includes(x.id))).join("");
    $("#list-empty").hidden = items.length > 0;
  } catch (e) {
    toast(e.message);
  }
}

let debounce;
document.querySelectorAll(".filters input, .filters select").forEach((el) => {
  el.addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(loadListings, 250);
  });
});

$("#list").addEventListener("click", (e) => {
  const f = e.target.closest("[data-fav]");
  if (f) {
    const id = Number(f.dataset.fav);
    const fav = getFav();
    setFav(fav.includes(id) ? fav.filter((x) => x !== id) : [...fav, id]);
    loadListings();
    return;
  }
  const a = e.target.closest("[data-ask]");
  if (a) {
    $("#ask-id").value = a.dataset.ask;
    $("#ask-title").textContent = a.dataset.title;
    $("#ask-dlg").showModal();
  }
});

$("#ask-cancel").addEventListener("click", () => $("#ask-dlg").close());
$("#ask-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  data.listing_id = Number(data.listing_id);
  try {
    await post("/api/inquiries", data);
    e.target.reset();
    $("#ask-dlg").close();
    toast("Отклик отправлен");
  } catch (err) {
    toast(err.message);
  }
});

$("#add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  data.price = Number(data.price);
  data.rooms = Number(data.rooms);
  try {
    await post("/api/listings", data);
    e.target.reset();
    toast("Объявление добавлено");
    loadListings();
  } catch (err) {
    toast(err.message);
  }
});

function mateCard(m) {
  return `<article class="card">
    <div class="row"><h3>${esc(m.name)}</h3><b>${m.compatibility}%</b></div>
    <div class="meter"><i style="width:${m.compatibility}%"></i></div>
    <p class="muted">Бюджет ${money(m.budget)}</p>
    <p class="muted">${tr.sleep[m.sleep] || esc(m.sleep)} · ${tr.cleanliness[m.cleanliness] || esc(m.cleanliness)} · ${tr.social[m.social] || esc(m.social)}</p>
    <p>${esc(m.bio)}</p>
  </article>`;
}

async function loadMatches() {
  const p = new URLSearchParams(new FormData($("#match-form")));
  try {
    const items = await api("/api/matches?" + p);
    $("#mates").innerHTML = items.map(mateCard).join("");
  } catch (e) {
    toast(e.message);
  }
}

$("#match-form").addEventListener("submit", (e) => {
  e.preventDefault();
  loadMatches();
});

$("#mate-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  data.budget = Number(data.budget);
  try {
    await post("/api/roommates", data);
    e.target.reset();
    toast("Профиль сохранён");
    loadMatches();
  } catch (err) {
    toast(err.message);
  }
});

function addMsg(kind, text) {
  const d = document.createElement("div");
  d.className = "msg " + kind;
  d.textContent = text;
  $("#chat").appendChild(d);
  $("#chat").scrollTop = $("#chat").scrollHeight;
  return d;
}

async function ask(text) {
  const send = $("#chat-send");
  send.disabled = true;
  addMsg("me", text);
  const wait = addMsg("bot", "Думаю...");
  try {
    const d = await post("/api/ai", { prompt: text });
    wait.textContent = d.answer.replace(/\*\*/g, "");
  } catch (err) {
    wait.textContent = err.message;
  }
  send.disabled = false;
  $("#chat").scrollTop = $("#chat").scrollHeight;
}

$("#chat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const text = $("#chat-input").value.trim();
  if (!text) return;
  $("#chat-input").value = "";
  ask(text);
});

document.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => ask(c.dataset.q)));

async function loadStats() {
  try {
    const s = await api("/api/stats");
    const cards = [
      ["Объявлений", s.listings],
      ["Средняя цена", money(s.avg_price)],
      ["Минимум", money(s.min_price)],
      ["Максимум", money(s.max_price)],
      ["Соседей в базе", s.roommates],
      ["Откликов", s.inquiries],
    ];
    $("#stat-cards").innerHTML = cards.map(([k, v]) => `<div class="stat"><b>${esc(v)}</b>${k}</div>`).join("");
    const top = Math.max(1, ...s.districts.map((d) => d.avg_price));
    $("#stat-bars").innerHTML = s.districts.map((d) =>
      `<div class="bar-row"><span>${esc(d.district)} (${d.count})</span><div class="bar-track"><i style="width:${Math.round(d.avg_price / top * 100)}%"></i></div><span>${money(d.avg_price)}</span></div>`
    ).join("");
    const inq = await api("/api/inquiries");
    $("#stat-inq").innerHTML = inq.length
      ? inq.map((i) => `<div><b>${esc(i.name)}</b> → ${esc(i.listing)}<br><span class="muted">${esc(i.message || "без сообщения")} · ${esc(i.created_at)}</span></div>`).join("")
      : `<p class="muted">Откликов пока нет.</p>`;
  } catch (e) {
    toast(e.message);
  }
}

loadListings();

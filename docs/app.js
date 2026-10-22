// Dagens lunch – static frontend. Reads data/menus.json (written by the scraper) and renders it.
// JSON contract: see "JSON-kontraktet" in CLAUDE.md.
(function () {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const state = { data: null, kinds: new Set(), sort: "dist", q: "" };

  try {
    const s = JSON.parse(localStorage.getItem("lunch.prefs") || "{}");
    if (s.sort === "dist" || s.sort === "price") state.sort = s.sort;
    (s.kinds || []).forEach((k) => state.kinds.add(k));
  } catch (e) { /* storage unavailable */ }
  function savePrefs() {
    try { localStorage.setItem("lunch.prefs", JSON.stringify({ sort: state.sort, kinds: [...state.kinds] })); } catch (e) { /* ignore */ }
  }

  // Dates in the office's time zone (Sweden).
  const fmt = new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Stockholm", year: "numeric", month: "2-digit", day: "2-digit" });
  const today = fmt.format(new Date());
  const dow = new Date(today + "T12:00:00Z").getUTCDay();
  const isWeekend = dow === 0 || dow === 6;
  function isoWeek(d) {
    const t = new Date(d + "T12:00:00Z"); const day = (t.getUTCDay() + 6) % 7;
    t.setUTCDate(t.getUTCDate() - day + 3); const f = new Date(Date.UTC(t.getUTCFullYear(), 0, 4));
    return 1 + Math.round(((t - f) / 864e5 - 3 + ((f.getUTCDay() + 6) % 7)) / 7);
  }
  const longDate = (d) => new Date(d + "T12:00:00Z").toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" });
  $("#dateline").textContent = longDate(today) + " · week " + isoWeek(today);

  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const speed = () => (state.data && state.data.walk_speed_m_per_min) || 80;
  // Straight-line distance × 1.3 approximates the walking route.
  const walk = (m) => Math.max(1, Math.ceil((m * 1.3) / speed()));
  const distKey = (r) => (typeof r.distance_m === "number" ? r.distance_m : 99999);
  const isUrl = (u) => typeof u === "string" && /^https?:\/\//i.test(u);

  function distHTML(r) {
    if (typeof r.distance_m !== "number") return "<b>—</b><span>distance pending</span>";
    return "<b>" + r.distance_m + " m</b><span>" + walk(r.distance_m) + " min walk</span>";
  }
  function menuLink(r, e) {
    const u = r.menu_source || (e && e.source);
    if (!isUrl(u)) return "";
    return '<div class="meta"><a href="' + esc(u) + '" target="_blank" rel="noopener">' +
      (/instagram\.com/i.test(u) ? "Lunch menu on Instagram ↗" : "Menu source ↗") + "</a></div>";
  }
  function minPrice(dishes) {
    const ps = dishes.map((d) => d.price).filter((p) => typeof p === "number");
    return ps.length ? Math.min(...ps) : null;
  }

  // controls
  document.querySelectorAll(".chip").forEach((b) => {
    b.setAttribute("aria-pressed", state.kinds.has(b.dataset.kind));
    b.addEventListener("click", () => {
      const k = b.dataset.kind;
      state.kinds.has(k) ? state.kinds.delete(k) : state.kinds.add(k);
      b.setAttribute("aria-pressed", state.kinds.has(k));
      savePrefs(); render();
    });
  });
  document.querySelectorAll(".seg button").forEach((b) => {
    b.setAttribute("aria-pressed", b.dataset.sort === state.sort);
    b.addEventListener("click", () => {
      state.sort = b.dataset.sort;
      document.querySelectorAll(".seg button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      savePrefs(); render();
    });
  });
  $("#q").addEventListener("input", (e) => { state.q = e.target.value.trim().toLowerCase(); render(); });

  function renderHeader(d) {
    const o = d.office || {};
    document.title = "Dagens lunch" + (o.name ? " · " + o.name : "");
    const where = [o.name, o.address].filter(Boolean).join(", ");
    $("#subline").textContent = d.restaurants.length + " lunch spots within " + (o.radius_m || 500) + " m of " + (where || "the office") + ".";
    $("#distnote").textContent = "Distances are straight-line from " + (o.address || "the office") + "; walking time assumes " + speed() + " m/min.";
    if (d.updated_at) {
      const t = new Date(d.updated_at);
      $("#stamp").innerHTML = "Menus updated<br>" + esc(t.toLocaleString("en-GB", { timeZone: "Europe/Stockholm", weekday: "short", hour: "2-digit", minute: "2-digit" }));
    }
    const n = $("#notice");
    if (isWeekend) {
      n.hidden = false;
      n.innerHTML = "<span>It’s the weekend, so most places don’t serve dagens lunch. Showing the latest weekday menus.</span>";
    } else if (d.date !== today) {
      n.hidden = false;
      n.innerHTML = "<span><b>Today’s menus aren’t in yet.</b> They’re collected every weekday morning. Showing " + esc(longDate(d.date)) + " for now.</span>";
    } else n.hidden = true;
  }

  function cardHTML(r, e, dishes) {
    const tags = (r.favourite ? '<span class="tag fav" title="' + esc(r.note || "Added by the office") + '">Office favourite</span>' : "") +
      (e.status === "standing" ? '<span class="tag warn" title="No dated menu for today was published; these dishes are on the menu every day">Standing menu</span>' : "");
    const dishHTML = dishes.map((d) =>
      '<li><span class="dot k-' + esc(d.kind || "other") + '"></span><div style="min-width:0"><div class="dname">' + esc(d.name) + "</div>" +
      (d.desc ? '<div class="ddesc">' + esc(d.desc) + "</div>" : "") + "</div>" +
      '<span class="price">' + (typeof d.price === "number" ? d.price + " kr" : esc(d.price || "")) + "</span></li>").join("");
    const incl = e.note || r.includes;
    return '<article class="card" data-id="' + esc(r.id) + '">' +
      '<div class="chead"><div style="min-width:0"><h3>' + esc(r.name) + '</h3><div class="meta">' + esc(r.address) + (r.hours ? " · " + esc(r.hours) : "") + "</div></div>" +
      '<div class="dist">' + distHTML(r) + "</div></div>" +
      (tags ? '<div class="tags">' + tags + "</div>" : "") +
      '<ul class="dishes">' + dishHTML + "</ul>" +
      (incl ? '<div class="incl">' + esc(incl) + "</div>" : "") +
      (isUrl(e.source) ? '<div class="cfoot"><a class="src" href="' + esc(e.source) + '" target="_blank" rel="noopener">Source ↗</a></div>' : "") +
      "</article>";
  }

  function render() {
    const d = state.data;
    if (!d) return;
    renderHeader(d);
    const list = $("#list");
    if (!d.restaurants.length) { list.innerHTML = '<div class="empty">No restaurants listed yet. Add some to config.yaml.</div>'; return; }

    const withMenu = [], without = [];
    for (const r of d.restaurants) {
      const e = (d.items || {})[r.id];
      if (e && (e.status === "today" || e.status === "standing") && (e.dishes || []).length) withMenu.push([r, e]);
      else without.push([r, e]);
    }

    const rows = withMenu.map(([r, e]) => {
      let dishes = e.dishes;
      if (state.kinds.size) dishes = dishes.filter((x) => state.kinds.has(x.kind));
      if (state.q) dishes = dishes.filter((x) => (x.name + " " + (x.desc || "")).toLowerCase().includes(state.q) || r.name.toLowerCase().includes(state.q));
      return { r, e, dishes };
    }).filter((x) => x.dishes.length);

    const byDist = (a, b) => distKey(a.r) - distKey(b.r);
    rows.sort(state.sort === "price" ? (a, b) => (minPrice(a.dishes) ?? 9999) - (minPrice(b.dishes) ?? 9999) || byDist(a, b) : byDist);

    list.innerHTML = rows.length
      ? '<div class="grid">' + rows.map(({ r, e, dishes }) => cardHTML(r, e, dishes)).join("") + "</div>"
      : '<div class="empty">No dishes match these filters. Clear a filter to see more.</div>';

    const box = $("#nomenuBox");
    if (!without.length) { box.hidden = true; return; }
    box.hidden = false;
    $("#nomenuSum").textContent = "No menu online (" + without.length + ")";
    without.sort((a, b) => distKey(a[0]) - distKey(b[0]));
    $("#nlist").innerHTML = without.map(([r, e]) => {
      const note = (e && e.note) || r.includes;
      return '<div class="nitem"><div class="row"><b>' + esc(r.name) + '</b><span class="price">' + (typeof r.distance_m === "number" ? r.distance_m + " m" : "") + "</span></div>" +
        (r.favourite ? '<div><span class="tag fav">Office favourite</span></div>' : "") +
        '<div class="meta">' + esc(r.address || "") + (r.hours ? " · " + esc(r.hours) : "") + "</div>" +
        (note ? '<div class="meta">' + esc(note) + "</div>" : "") + menuLink(r, e) + "</div>";
    }).join("");
  }

  fetch("data/menus.json", { cache: "no-cache" })
    .then((res) => { if (!res.ok) throw new Error(res.status); return res.json(); })
    .then((data) => { state.data = data; render(); })
    .catch(() => { $("#list").innerHTML = '<div class="empty">Couldn’t load today’s menus. Try reloading the page.</div>'; });
})();

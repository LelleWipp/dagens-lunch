// Dagens lunch – static frontend. Reads data/menus.json (written by the scraper) and renders it.
// JSON contract: see "JSON-kontraktet" in CLAUDE.md.
(function () {
  "use strict";
  const $ = (s) => document.querySelector(s);

  // Fallbacks used when menus.json omits a value (config.yaml normally provides them).
  const DEFAULT_WALK_SPEED_M_PER_MIN = 80;
  const DEFAULT_RADIUS_M = 500;
  // Straight-line distance × ROUTE_FACTOR approximates the walking route.
  const ROUTE_FACTOR = 1.3;
  // Sort keys for restaurants without a distance / dishes without a price: sort them last.
  const UNKNOWN_DISTANCE = 99999;
  const UNKNOWN_PRICE = 9999;
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
  const speed = () => (state.data && state.data.walk_speed_m_per_min) || DEFAULT_WALK_SPEED_M_PER_MIN;
  const walk = (m) => Math.max(1, Math.ceil((m * ROUTE_FACTOR) / speed()));
  const hasDistance = (r) => typeof r.distance_m === "number";
  const distKey = (r) => (hasDistance(r) ? r.distance_m : UNKNOWN_DISTANCE);
  const compareDistance = (a, b) => distKey(a) - distKey(b);
  const isUrl = (u) => typeof u === "string" && /^https?:\/\//i.test(u);

  // Shared HTML fragments for menu cards and the "no menu online" list.
  const metersHTML = (r) => (hasDistance(r) ? r.distance_m + " m" : "");
  const metaLineHTML = (r) => '<div class="meta">' + esc(r.address) + (r.hours ? " · " + esc(r.hours) : "") + "</div>";
  const extraInfo = (r, e) => (e && e.note) || r.includes;
  function favouriteTagHTML(r, withTooltip) {
    if (!r.favourite) return "";
    const title = withTooltip ? ' title="' + esc(r.note || "Added by the office") + '"' : "";
    return '<span class="tag fav"' + title + ">Office favourite</span>";
  }
  function externalLinkHTML(url, label, className) {
    const cls = className ? ' class="' + className + '"' : "";
    return "<a" + cls + ' href="' + esc(url) + '" target="_blank" rel="noopener">' + label + "</a>";
  }

  function distHTML(r) {
    if (!hasDistance(r)) return "<b>—</b><span>distance pending</span>";
    return "<b>" + metersHTML(r) + "</b><span>" + walk(r.distance_m) + " min walk</span>";
  }
  function menuLink(r, e) {
    const u = r.menu_source || (e && e.source);
    if (!isUrl(u)) return "";
    return '<div class="meta">' + externalLinkHTML(u, /instagram\.com/i.test(u) ? "Lunch menu on Instagram ↗" : "Menu source ↗") + "</div>";
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
    $("#subline").textContent = d.restaurants.length + " lunch spots within " + (o.radius_m || DEFAULT_RADIUS_M) + " m of " + (where || "the office") + ".";
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
    const tags = favouriteTagHTML(r, true) +
      (e.status === "standing" ? '<span class="tag warn" title="No dated menu for today was published; these dishes are on the menu every day">Standing menu</span>' : "");
    const dishHTML = dishes.map((d) =>
      '<li><span class="dot k-' + esc(d.kind || "other") + '"></span><div style="min-width:0"><div class="dname">' + esc(d.name) + "</div>" +
      (d.desc ? '<div class="ddesc">' + esc(d.desc) + "</div>" : "") + "</div>" +
      '<span class="price">' + (typeof d.price === "number" ? d.price + " kr" : esc(d.price || "")) + "</span></li>").join("");
    const incl = extraInfo(r, e);
    return '<article class="card" data-id="' + esc(r.id) + '">' +
      '<div class="chead"><div style="min-width:0"><h3>' + esc(r.name) + "</h3>" + metaLineHTML(r) + "</div>" +
      '<div class="dist">' + distHTML(r) + "</div></div>" +
      (tags ? '<div class="tags">' + tags + "</div>" : "") +
      '<ul class="dishes">' + dishHTML + "</ul>" +
      (incl ? '<div class="incl">' + esc(incl) + "</div>" : "") +
      (isUrl(e.source) ? '<div class="cfoot">' + externalLinkHTML(e.source, "Source ↗", "src") + "</div>" : "") +
      "</article>";
  }

  const hasMenu = (entry) => Boolean(entry) && (entry.status === "today" || entry.status === "standing") && (entry.dishes || []).length > 0;

  // Splits restaurants into those with a menu to show as cards and those listed under "No menu online".
  function partitionByMenu(data) {
    const withMenu = [], withoutMenu = [];
    for (const restaurant of data.restaurants) {
      const entry = (data.items || {})[restaurant.id];
      (hasMenu(entry) ? withMenu : withoutMenu).push([restaurant, entry]);
    }
    return { withMenu, withoutMenu };
  }

  // Dishes that pass the active kind filters and search query (a restaurant-name match keeps all its dishes).
  function filterDishes(restaurant, dishes) {
    let visible = dishes;
    if (state.kinds.size) visible = visible.filter((dish) => state.kinds.has(dish.kind));
    if (state.q) visible = visible.filter((dish) => (dish.name + " " + (dish.desc || "")).toLowerCase().includes(state.q) || restaurant.name.toLowerCase().includes(state.q));
    return visible;
  }

  function sortRows(rows) {
    const byDistance = (a, b) => compareDistance(a.r, b.r);
    const byPrice = (a, b) => (minPrice(a.dishes) ?? UNKNOWN_PRICE) - (minPrice(b.dishes) ?? UNKNOWN_PRICE) || byDistance(a, b);
    return rows.sort(state.sort === "price" ? byPrice : byDistance);
  }

  function renderMenuGrid(withMenu) {
    const rows = withMenu
      .map(([r, e]) => ({ r, e, dishes: filterDishes(r, e.dishes) }))
      .filter((row) => row.dishes.length);
    sortRows(rows);
    $("#list").innerHTML = rows.length
      ? '<div class="grid">' + rows.map(({ r, e, dishes }) => cardHTML(r, e, dishes)).join("") + "</div>"
      : '<div class="empty">No dishes match these filters. Clear a filter to see more.</div>';
  }

  function noMenuItemHTML(r, e) {
    const note = extraInfo(r, e);
    return '<div class="nitem"><div class="row"><b>' + esc(r.name) + '</b><span class="price">' + metersHTML(r) + "</span></div>" +
      (r.favourite ? "<div>" + favouriteTagHTML(r, false) + "</div>" : "") +
      metaLineHTML(r) +
      (note ? '<div class="meta">' + esc(note) + "</div>" : "") + menuLink(r, e) + "</div>";
  }

  function renderNoMenuList(withoutMenu) {
    const box = $("#nomenuBox");
    if (!withoutMenu.length) { box.hidden = true; return; }
    box.hidden = false;
    $("#nomenuSum").textContent = "No menu online (" + withoutMenu.length + ")";
    withoutMenu.sort(([a], [b]) => compareDistance(a, b));
    $("#nlist").innerHTML = withoutMenu.map(([r, e]) => noMenuItemHTML(r, e)).join("");
  }

  // Re-renders the restaurant lists; called on load and whenever a filter, sort or search changes.
  function render() {
    const data = state.data;
    if (!data) return;
    if (!data.restaurants.length) {
      $("#list").innerHTML = '<div class="empty">No restaurants listed yet. Add some to config.yaml.</div>';
      return;
    }
    const { withMenu, withoutMenu } = partitionByMenu(data);
    renderMenuGrid(withMenu);
    renderNoMenuList(withoutMenu);
  }

  fetch("data/menus.json", { cache: "no-cache" })
    .then((res) => { if (!res.ok) throw new Error(res.status); return res.json(); })
    .then((data) => { state.data = data; renderHeader(data); render(); })
    .catch(() => { $("#list").innerHTML = '<div class="empty">Couldn’t load today’s menus. Try reloading the page.</div>'; });
})();

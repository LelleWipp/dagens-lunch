// Dagens lunch – static frontend. Reads data/menus.json (written by the scraper) and renders it.
// JSON contract: see "JSON-kontraktet" in CLAUDE.md.
(function () {
  "use strict";
  const $ = (selector) => document.querySelector(selector);

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
    const saved = JSON.parse(localStorage.getItem("lunch.prefs") || "{}");
    if (saved.sort === "dist" || saved.sort === "price") state.sort = saved.sort;
    (saved.kinds || []).forEach((kind) => state.kinds.add(kind));
  } catch (err) { /* storage unavailable */ }
  function savePrefs() {
    try { localStorage.setItem("lunch.prefs", JSON.stringify({ sort: state.sort, kinds: [...state.kinds] })); } catch (err) { /* ignore */ }
  }

  // Dates in the office's time zone (Sweden).
  const ymdFormat = new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Stockholm", year: "numeric", month: "2-digit", day: "2-digit" });
  const today = ymdFormat.format(new Date());
  const dayOfWeek = new Date(today + "T12:00:00Z").getUTCDay();
  const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
  // ISO 8601 week number for a YYYY-MM-DD date (weeks start Monday; week 1 contains 4 January).
  function isoWeek(ymd) {
    const date = new Date(ymd + "T12:00:00Z"); const weekday = (date.getUTCDay() + 6) % 7;
    date.setUTCDate(date.getUTCDate() - weekday + 3); const jan4 = new Date(Date.UTC(date.getUTCFullYear(), 0, 4));
    return 1 + Math.round(((date - jan4) / 864e5 - 3 + ((jan4.getUTCDay() + 6) % 7)) / 7);
  }
  const longDate = (ymd) => new Date(ymd + "T12:00:00Z").toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" });
  $("#dateline").textContent = longDate(today) + " · week " + isoWeek(today);

  const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  const walkSpeed = () => (state.data && state.data.walk_speed_m_per_min) || DEFAULT_WALK_SPEED_M_PER_MIN;
  const walkMinutes = (meters) => Math.max(1, Math.ceil((meters * ROUTE_FACTOR) / walkSpeed()));
  const hasDistance = (restaurant) => typeof restaurant.distance_m === "number";
  const distanceSortKey = (restaurant) => (hasDistance(restaurant) ? restaurant.distance_m : UNKNOWN_DISTANCE);
  const compareDistance = (a, b) => distanceSortKey(a) - distanceSortKey(b);
  const isUrl = (value) => typeof value === "string" && /^https?:\/\//i.test(value);

  // Shared HTML fragments for menu cards and the "no menu online" list.
  const metersHTML = (restaurant) => (hasDistance(restaurant) ? restaurant.distance_m + " m" : "");
  const metaLineHTML = (restaurant) => '<div class="meta">' + esc(restaurant.address) + (restaurant.hours ? " · " + esc(restaurant.hours) : "") + "</div>";
  // Today's note from the menu entry wins over the static "includes" text from config.yaml.
  const extraInfo = (restaurant, entry) => (entry && entry.note) || restaurant.includes;
  function favouriteTagHTML(restaurant, withTooltip) {
    if (!restaurant.favourite) return "";
    const title = withTooltip ? ' title="' + esc(restaurant.note || "Added by the office") + '"' : "";
    return '<span class="tag fav"' + title + ">Office favourite</span>";
  }
  function externalLinkHTML(url, label, className) {
    const cls = className ? ' class="' + className + '"' : "";
    return "<a" + cls + ' href="' + esc(url) + '" target="_blank" rel="noopener">' + label + "</a>";
  }

  function distanceHTML(restaurant) {
    if (!hasDistance(restaurant)) return "<b>—</b><span>distance pending</span>";
    return "<b>" + metersHTML(restaurant) + "</b><span>" + walkMinutes(restaurant.distance_m) + " min walk</span>";
  }
  function menuLinkHTML(restaurant, entry) {
    const url = restaurant.menu_source || (entry && entry.source);
    if (!isUrl(url)) return "";
    return '<div class="meta">' + externalLinkHTML(url, /instagram\.com/i.test(url) ? "Lunch menu on Instagram ↗" : "Menu source ↗") + "</div>";
  }
  function minPrice(dishes) {
    const prices = dishes.map((dish) => dish.price).filter((price) => typeof price === "number");
    return prices.length ? Math.min(...prices) : null;
  }

  // controls
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.setAttribute("aria-pressed", state.kinds.has(chip.dataset.kind));
    chip.addEventListener("click", () => {
      const kind = chip.dataset.kind;
      state.kinds.has(kind) ? state.kinds.delete(kind) : state.kinds.add(kind);
      chip.setAttribute("aria-pressed", state.kinds.has(kind));
      savePrefs(); render();
    });
  });
  document.querySelectorAll(".seg button").forEach((sortButton) => {
    sortButton.setAttribute("aria-pressed", sortButton.dataset.sort === state.sort);
    sortButton.addEventListener("click", () => {
      state.sort = sortButton.dataset.sort;
      document.querySelectorAll(".seg button").forEach((other) => other.setAttribute("aria-pressed", other === sortButton));
      savePrefs(); render();
    });
  });
  $("#q").addEventListener("input", (event) => { state.q = event.target.value.trim().toLowerCase(); render(); });

  function renderHeader(data) {
    const office = data.office || {};
    document.title = "Dagens lunch" + (office.name ? " · " + office.name : "");
    const where = [office.name, office.address].filter(Boolean).join(", ");
    $("#subline").textContent = data.restaurants.length + " lunch spots within " + (office.radius_m || DEFAULT_RADIUS_M) + " m of " + (where || "the office") + ".";
    $("#distnote").textContent = "Distances are straight-line from " + (office.address || "the office") + "; walking time assumes " + walkSpeed() + " m/min.";
    if (data.updated_at) {
      const updatedAt = new Date(data.updated_at);
      $("#stamp").innerHTML = "Menus updated<br>" + esc(updatedAt.toLocaleString("en-GB", { timeZone: "Europe/Stockholm", weekday: "short", hour: "2-digit", minute: "2-digit" }));
    }
    const notice = $("#notice");
    if (isWeekend) {
      notice.hidden = false;
      notice.innerHTML = "<span>It’s the weekend, so most places don’t serve dagens lunch. Showing the latest weekday menus.</span>";
    } else if (data.date !== today) {
      notice.hidden = false;
      notice.innerHTML = "<span><b>Today’s menus aren’t in yet.</b> They’re collected every weekday morning. Showing " + esc(longDate(data.date)) + " for now.</span>";
    } else notice.hidden = true;
  }

  function dishHTML(dish) {
    const price = typeof dish.price === "number" ? dish.price + " kr" : esc(dish.price || "");
    return '<li><span class="dot k-' + esc(dish.kind || "other") + '"></span><div class="shrink"><div class="dname">' + esc(dish.name) + "</div>" +
      (dish.desc ? '<div class="ddesc">' + esc(dish.desc) + "</div>" : "") + "</div>" +
      '<span class="price">' + price + "</span></li>";
  }

  function cardHTML(restaurant, entry, dishes) {
    const tags = favouriteTagHTML(restaurant, true) +
      (entry.status === "standing" ? '<span class="tag warn" title="No dated menu for today was published; these dishes are on the menu every day">Standing menu</span>' : "");
    const extra = extraInfo(restaurant, entry);
    return '<article class="card" data-id="' + esc(restaurant.id) + '">' +
      '<div class="chead"><div class="shrink"><h3>' + esc(restaurant.name) + "</h3>" + metaLineHTML(restaurant) + "</div>" +
      '<div class="dist">' + distanceHTML(restaurant) + "</div></div>" +
      (tags ? '<div class="tags">' + tags + "</div>" : "") +
      '<ul class="dishes">' + dishes.map(dishHTML).join("") + "</ul>" +
      (extra ? '<div class="incl">' + esc(extra) + "</div>" : "") +
      (isUrl(entry.source) ? '<div class="cfoot">' + externalLinkHTML(entry.source, "Source ↗", "src") + "</div>" : "") +
      "</article>";
  }

  const hasMenu = (entry) => Boolean(entry) && (entry.status === "today" || entry.status === "standing") && (entry.dishes || []).length > 0;

  // Splits restaurants into those with a menu to show as cards and those listed under "No menu online".
  function partitionByMenu(data) {
    const withMenu = [], withoutMenu = [];
    for (const restaurant of data.restaurants) {
      const entry = (data.items || {})[restaurant.id];
      (hasMenu(entry) ? withMenu : withoutMenu).push({ restaurant, entry });
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
    const byDistance = (a, b) => compareDistance(a.restaurant, b.restaurant);
    const byPrice = (a, b) => (minPrice(a.dishes) ?? UNKNOWN_PRICE) - (minPrice(b.dishes) ?? UNKNOWN_PRICE) || byDistance(a, b);
    return rows.sort(state.sort === "price" ? byPrice : byDistance);
  }

  function renderMenuGrid(withMenu) {
    const rows = withMenu
      .map(({ restaurant, entry }) => ({ restaurant, entry, dishes: filterDishes(restaurant, entry.dishes) }))
      .filter((row) => row.dishes.length);
    sortRows(rows);
    $("#list").innerHTML = rows.length
      ? '<div class="grid">' + rows.map((row) => cardHTML(row.restaurant, row.entry, row.dishes)).join("") + "</div>"
      : '<div class="empty">No dishes match these filters. Clear a filter to see more.</div>';
  }

  function noMenuItemHTML(restaurant, entry) {
    const extra = extraInfo(restaurant, entry);
    return '<div class="nitem"><div class="row"><b>' + esc(restaurant.name) + '</b><span class="price">' + metersHTML(restaurant) + "</span></div>" +
      (restaurant.favourite ? "<div>" + favouriteTagHTML(restaurant, false) + "</div>" : "") +
      metaLineHTML(restaurant) +
      (extra ? '<div class="meta">' + esc(extra) + "</div>" : "") + menuLinkHTML(restaurant, entry) + "</div>";
  }

  function renderNoMenuList(withoutMenu) {
    const box = $("#nomenuBox");
    if (!withoutMenu.length) { box.hidden = true; return; }
    box.hidden = false;
    $("#nomenuSum").textContent = "No menu online (" + withoutMenu.length + ")";
    withoutMenu.sort((a, b) => compareDistance(a.restaurant, b.restaurant));
    $("#nlist").innerHTML = withoutMenu.map((row) => noMenuItemHTML(row.restaurant, row.entry)).join("");
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

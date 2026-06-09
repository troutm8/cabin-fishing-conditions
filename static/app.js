// Fetch the combined conditions and render the dashboard.
// Each refresh of the page calls this once; the server's cache decides
// whether that actually hits the upstream APIs.

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function fmtDate(iso) {
  // "2026-05-20" -> "May 20"; pass anything else through unchanged.
  // Reports on quiet waters can be years old, so show the year when
  // it isn't the current one.
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
  if (!m) return iso || "";
  const base = `${MONTHS[parseInt(m[2], 10) - 1]} ${parseInt(m[3], 10)}`;
  const year = parseInt(m[1], 10);
  return year === new Date().getFullYear() ? base : `${base}, ${year}`;
}

function fmtUpdated(iso, ageMinutes) {
  if (!iso) return "just now";
  const t = new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  if (ageMinutes != null && ageMinutes >= 60) {
    const hrs = Math.round(ageMinutes / 60);
    return `${t} (weather ~${hrs}h old)`;
  }
  return t;
}

function el(tag, className, html) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (html != null) node.innerHTML = html;
  return node;
}

function weatherBlock(w) {
  const wrap = el("div");
  wrap.appendChild(el("p", "label", "Weather"));
  if (!w) {
    wrap.appendChild(el("p", "unavailable", "Weather unavailable"));
    return wrap;
  }
  const row = el("div", "wx");
  row.innerHTML =
    `<i class="ti ${w.icon}" aria-hidden="true"></i>` +
    `<span class="temp">${w.temp}&deg;</span>` +
    `<span class="cond">${w.condition}</span>`;
  wrap.appendChild(row);
  wrap.appendChild(el("p", "wx-detail",
    `Wind ${w.wind} &middot; H ${w.high}&deg; / L ${w.low}&deg;`));
  return wrap;
}

function stockingBlock(s) {
  const wrap = el("div");
  wrap.appendChild(el("p", "label", "Stocking"));
  if (!s || (!s.last && !s.next)) {
    wrap.appendChild(el("p", "unavailable", "No recent stocking data"));
    return wrap;
  }
  if (s.last) {
    wrap.appendChild(el("p", "stock-line",
      `Last: ${fmtDate(s.last.date)} &mdash; ${s.last.species || "fish"}`));
  }
  wrap.appendChild(el("p", "stock-sub",
    s.next ? `Next: ${fmtDate(s.next.date)} &mdash; ${s.next.species || "fish"}`
           : "Next: not yet scheduled"));
  return wrap;
}

function crowdBlock(c) {
  const wrap = el("div");
  wrap.appendChild(el("p", "label", "Latest fish report"));
  if (!c || c.status !== "report") {
    const box = el("div", "placeholder");
    box.innerHTML =
      `<i class="ti ti-users" aria-hidden="true"></i>` +
      `<span>No reports for this water</span>`;
    wrap.appendChild(box);
    return wrap;
  }
  const line = el("p", "crowd-line");
  const link = el("a");
  link.href = c.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = c.title;
  line.appendChild(link);
  wrap.appendChild(line);
  wrap.appendChild(el("p", "crowd-sub",
    `${fmtDate(c.date)} &middot; ${c.author || "NorCal Fish Reports"}`));
  return wrap;
}

function card(water) {
  const c = el("div", "card");

  const head = el("div", "card-head");
  const left = el("div");
  left.appendChild(el("p", "card-name", water.name));
  const meta = [`${water.drive_minutes} min`];
  if (water.notes) meta.push(water.notes);
  left.appendChild(el("p", "card-meta", meta.join(" &middot; ")));
  head.appendChild(left);

  const mapsUrl =
    `https://www.google.com/maps/search/?api=1&query=${water.lat},${water.lon}`;
  const link = el("a", "map-link");
  link.href = mapsUrl;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.title = `Open ${water.name} in Google Maps`;
  link.setAttribute("aria-label", `Open ${water.name} in Google Maps`);
  link.appendChild(el("i", "ti ti-map-pin"));
  head.appendChild(link);
  c.appendChild(head);

  c.appendChild(weatherBlock(water.weather));
  c.appendChild(stockingBlock(water.stocking));
  c.appendChild(crowdBlock(water.crowd));
  return c;
}

function render(data) {
  document.getElementById("updated").textContent =
    "Updated " + fmtUpdated(data.updated, data.weather_age_minutes);

  const board = document.getElementById("board");
  board.innerHTML = "";

  for (const group of data.groups) {
    const head = el("div", "section-head");
    head.innerHTML = `<i class="ti ${group.icon}" aria-hidden="true"></i>` +
                     `<h2>${group.label}</h2>`;
    board.appendChild(head);

    const grid = el("div", "grid");
    group.waters.forEach((w) => grid.appendChild(card(w)));
    board.appendChild(grid);
  }
}

async function load() {
  try {
    const resp = await fetch("/api/conditions");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    render(await resp.json());
  } catch (err) {
    const e = document.getElementById("error");
    e.hidden = false;
    e.textContent = "Couldn't load conditions: " + err.message;
    document.getElementById("updated").textContent = "unavailable";
  }
}

load();

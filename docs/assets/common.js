// Shared helpers for every page: data loading, nav, credit bar, formatting,
// status pills, chart defaults (colors read from the CSS tokens), URL state.

const PAGES = [
  { file: "index.html", nav: "Weekly cycle" },
  { file: "intake.html", nav: "Intake & triage" },
  { file: "skills.html", nav: "Skill ports" },
  { file: "catalog.html", nav: "Listings" },
  { file: "status.html", nav: "Weekly status" },
  { file: "how-this-works.html", nav: "How this works" },
];

const CC = {
  async load(name) {
    const res = await fetch(`data/${name}.json?v=2026101902`);
    if (!res.ok) throw new Error(`Could not load data/${name}.json (${res.status})`);
    return res.json();
  },

  init(pageFile) {
    const nav = document.getElementById("nav");
    if (nav) {
      nav.innerHTML = `<ul>${PAGES.map((p) =>
        `<li><a href="${p.file}"${p.file === pageFile ? ' aria-current="page"' : ""}>${p.nav}</a></li>`).join("")}</ul>`;
    }
    const header = document.querySelector(".site-header");
    if (header && !document.querySelector(".credit-bar")) {
      const bar = document.createElement("div");
      bar.className = "credit-bar";
      bar.innerHTML = `<div class="inner"><strong>Built with AI:</strong> Designed and reviewed by me</div>`;
      header.after(bar);
    }
  },

  // ---------- formatting ----------
  esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  },
  usd(n) {
    n = Number(n) || 0;
    if (n >= 1e6) return `$${(n / 1e6).toFixed(2).replace(/\.?0+$/, "")}M`;
    if (n >= 1e3) return `$${Math.round(n / 1e3)}K`;
    return `$${n.toLocaleString()}`;
  },
  pct(x, d = 0) { return `${(100 * x).toFixed(d)}%`; },
  num(n) { return Number(n).toLocaleString(); },
  date(s) {
    const d = new Date(`${String(s).slice(0, 10)}T12:00:00`);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  },

  // ---------- pills ----------
  PILL: {
    Urgent: "urgent", High: "high", Medium: "medium", Low: "low",
    Build: "pass", Partner: "medium", Decline: "low", "Need info": "action", "Already live": "neutral",
    Pass: "pass", Action: "action", Fail: "fail",
    "Ready to launch": "pass", "Ready to port": "medium", "In QA": "action", "Needs action": "action", Blocked: "fail",
    Rewritten: "pass", "Meets template": "pass", "Queued for rewrite": "action", "Fix in next sweep": "low",
  },
  pill(text, title) {
    const cls = CC.PILL[text] || "neutral";
    return `<span class="pill pill-${cls}"${title ? ` title="${CC.esc(title)}"` : ""}>${CC.esc(text)}</span>`;
  },

  // ---------- URL state ----------
  param(name) { return new URLSearchParams(location.search).get(name); },
  setParam(name, value) {
    const u = new URL(location.href);
    if (value) u.searchParams.set(name, value); else u.searchParams.delete(name);
    history.replaceState(null, "", u);
  },

  // ---------- charts ----------
  css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); },
  layout(extra = {}) {
    const text = CC.css("--text-2"), grid = CC.css("--grid");
    return Object.assign({
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: CC.css("--font"), size: 12, color: text },
      margin: { l: 48, r: 16, t: 16, b: 44 },
      xaxis: { gridcolor: grid, zerolinecolor: grid, linecolor: CC.css("--axis") },
      yaxis: { gridcolor: grid, zerolinecolor: grid, linecolor: CC.css("--axis") },
      legend: { orientation: "h", y: -0.18 },
      hoverlabel: { font: { family: CC.css("--font") } },
    }, extra);
  },
  plot(id, traces, layout) {
    Plotly.newPlot(id, traces, CC.layout(layout), { displayModeBar: false, responsive: true });
  },

  // ---------- tables ----------
  // cols: [{ key, label, num?, render?(row) }]
  table(el, rows, cols, opts = {}) {
    const head = `<thead><tr>${cols.map((c) => `<th${c.num ? ' class="num"' : ""}>${c.label}</th>`).join("")}</tr></thead>`;
    const body = rows.map((r) => {
      const cls = [opts.selected && opts.selected(r) ? "is-selected" : "", opts.onClick ? "clickable" : ""].join(" ").trim();
      return `<tr${cls ? ` class="${cls}"` : ""}${opts.rowKey ? ` data-key="${CC.esc(opts.rowKey(r))}"` : ""}>${cols.map((c) =>
        `<td${c.num ? ' class="num"' : ""}>${c.render ? c.render(r) : CC.esc(r[c.key])}</td>`).join("")}</tr>`;
    }).join("");
    el.innerHTML = `<table>${head}<tbody>${body || `<tr><td colspan="${cols.length}" class="muted">Nothing matches.</td></tr>`}</tbody></table>`;
    if (opts.onClick) {
      el.querySelectorAll("tr[data-key]").forEach((tr) => tr.addEventListener("click", () => opts.onClick(tr.dataset.key)));
    }
  },

  kpi(label, value, sub = "") {
    return `<div class="card kpi"><div class="label">${label}</div><div class="value">${value}</div><div class="sub">${sub}</div></div>`;
  },

  listingCard(l) {
    const list = (v) => String(v || "").split("|").filter(Boolean);
    const caps = list(l.capabilities), prompts = list(l.try_asking);
    const orEmpty = (v) => (v ? CC.esc(v) : `<span class="empty">missing</span>`);
    return `<div class="listing-card">
      <div class="ttl">${orEmpty(l.title)}</div>
      <div class="sum">${orEmpty(l.summary)}</div>
      <div class="lbl">What it can do</div>
      ${caps.length ? `<ul>${caps.map((c) => `<li>${CC.esc(c)}</li>`).join("")}</ul>` : `<span class="empty">missing</span>`}
      <div class="lbl">Permissions</div><div class="small">${orEmpty(l.permissions)}</div>
      <div class="lbl">Required connectors</div><div class="small">${orEmpty(l.required_connectors)}</div>
      <div class="lbl">Try asking</div>
      ${prompts.length ? `<ul>${prompts.map((c) => `<li>“${CC.esc(c)}”</li>`).join("")}</ul>` : `<span class="empty">missing</span>`}
      <div class="lbl">Author</div><div class="small">${orEmpty(l.author)}</div>
    </div>`;
  },

  checklist(checks) {
    return `<ul class="checklist">${Object.entries(checks).map(([k, v]) =>
      `<li class="${v ? "ok" : "no"}">${CC.esc(k)}</li>`).join("")}</ul>`;
  },
};

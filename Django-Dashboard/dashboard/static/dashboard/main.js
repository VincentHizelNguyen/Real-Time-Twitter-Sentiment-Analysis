/* global Chart */

(() => {
  "use strict";

  // =========================
  // Helpers
  // =========================
  const $ = (id) => document.getElementById(id);

  function must(id) {
    const el = $(id);
    if (!el) console.error(`[dashboard] Missing element #${id}`);
    return el;
  }

  function fmtTime(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleString();
    } catch (e) {
      return String(iso);
    }
  }

  // Suy ra base path cho API:
  // - Nếu page là "/" => base = ""
  // - Nếu page là "/dashboard/" => base = "/dashboard"
  // - Có thể override bằng window.API_BASE = "/dashboard"
  function inferApiBase() {
    if (window.API_BASE && typeof window.API_BASE === "string") {
      return window.API_BASE.replace(/\/$/, "");
    }
    // lấy path hiện tại, bỏ query/hash
    const path = window.location.pathname || "/";
    // bỏ trailing slash
    const trimmed = path.length > 1 ? path.replace(/\/$/, "") : "";
    // Nếu đang ở "/dashboard" hoặc "/dashboard/" thì base là "/dashboard"
    // Nếu đang ở "/" thì base là ""
    return trimmed;
  }

  const API_BASE = inferApiBase();
  const apiUrl = (p) => `${API_BASE}${p}`; // p dạng "/api/overview/..."

  async function fetchJson(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} ${res.statusText} @ ${url}\n${text}`);
    }
    return await res.json();
  }

  // =========================
  // State
  // =========================
  let lineChart = null;
  let sourceChart = null;

  // =========================
  // API loaders
  // =========================
  async function loadOverview() {
    const minutesEl = must("minutes");
    const minutes = (minutesEl && minutesEl.value) ? minutesEl.value : "60";
    return await fetchJson(apiUrl(`/api/overview/?minutes=${encodeURIComponent(minutes)}`));
  }

  async function loadSeries() {
    return await fetchJson(apiUrl(`/api/series/?limit=120`));
  }

  async function loadLatest() {
    const labelEl = must("label");
    const sourceEl = must("source");

    const label = (labelEl && labelEl.value) ? labelEl.value : "all";
    const source = (sourceEl && sourceEl.value) ? sourceEl.value : "all";

    return await fetchJson(
      apiUrl(`/api/latest/?limit=20&label=${encodeURIComponent(label)}&source=${encodeURIComponent(source)}`)
    );
  }

  // =========================
  // Renderers
  // =========================
  function renderKPIs(kpis) {
    const total = must("kpiTotal");
    const recent = must("kpiRecent");
    const pos = must("kpiPos");
    const neg = must("kpiNeg");
    const neu = must("kpiNeu");
    if (!total || !recent || !pos || !neg || !neu) return;

    total.innerText = kpis?.total_docs ?? "-";
    recent.innerText = kpis?.recent_docs ?? "-";
    pos.innerText = kpis?.labels?.positive ?? 0;
    neg.innerText = kpis?.labels?.negative ?? 0;
    neu.innerText = kpis?.labels?.neutral ?? 0;
  }

  function renderSourceDropdown(sources) {
    const sel = must("source");
    if (!sel) return;

    const cur = sel.value;
    sel.innerHTML = `<option value="all">all</option>`;

    (sources || []).forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      sel.appendChild(opt);
    });

    if ([...sel.options].some((o) => o.value === cur)) sel.value = cur;
  }

  function renderLine(series) {
    const canvas = must("chartLine");
    if (!canvas) return;

    // gộp theo window_start, cộng dồn
    const map = new Map();
    (series || []).forEach((r) => {
      const key = r.window_start;
      if (!key) return;
      const cur = map.get(key) || { pos: 0, neg: 0, neu: 0 };
      cur.pos += (r.positive || 0);
      cur.neg += (r.negative || 0);
      cur.neu += (r.neutral || 0);
      map.set(key, cur);
    });

    const labels = [...map.keys()];
    const pos = labels.map((k) => map.get(k).pos);
    const neg = labels.map((k) => map.get(k).neg);
    const neu = labels.map((k) => map.get(k).neu);

    if (lineChart) lineChart.destroy();
    lineChart = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "positive", data: pos },
          { label: "negative", data: neg },
          { label: "neutral", data: neu }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: true } }
      }
    });
  }

  function renderSourceBar(bySource) {
    const canvas = must("chartSource");
    if (!canvas) return;

    const labels = (bySource || []).map((x) => x.name);
    const vals = (bySource || []).map((x) => x.cnt);

    if (sourceChart) sourceChart.destroy();
    sourceChart = new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [{ label: "count", data: vals }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: true } }
      }
    });
  }

  function renderLatestTable(rows) {
    const tbody = must("latestBody");
    if (!tbody) return;

    tbody.innerHTML = "";

    (rows || []).forEach((r) => {
      const tr = document.createElement("tr");

      const tdTime = document.createElement("td");
      tdTime.textContent = fmtTime(r.event_time);

      const tdLabel = document.createElement("td");
      tdLabel.innerHTML = `<span class="tag">${r.label || "unknown"}</span>`;

      const tdSR = document.createElement("td");
      tdSR.textContent = `${r.source || "unknown"} / ${r.region || "unknown"}`;

      const tdText = document.createElement("td");
      tdText.textContent = r.text || "";

      tr.appendChild(tdTime);
      tr.appendChild(tdLabel);
      tr.appendChild(tdSR);
      tr.appendChild(tdText);
      tbody.appendChild(tr);
    });
  }

  // =========================
  // Main refresh
  // =========================
  async function refreshAll() {
    const status = must("status");
    if (status) status.textContent = "loading...";

    try {
      // Overview (KPIs + dropdown + source bar)
      const overview = await loadOverview();
      renderKPIs(overview.kpis);
      renderSourceDropdown(overview.sources);
      renderSourceBar(overview.kpis?.by_source || []);

      // Series line
      const series = await loadSeries();
      renderLine(series);

      // Latest table
      const latest = await loadLatest();
      renderLatestTable(latest);

      if (status) status.textContent = `updated @ ${new Date().toLocaleTimeString()} (API_BASE=${API_BASE || "/"})`;
    } catch (e) {
      console.error(e);
      if (status) status.textContent = "failed (open console)";
    }
  }

  // =========================
  // Boot
  // =========================
  document.addEventListener("DOMContentLoaded", () => {
    // nếu Chart.js chưa load thì dừng ngay
    if (typeof Chart === "undefined") {
      console.error("[dashboard] Chart.js not loaded. Check CDN in HTML.");
      const status = $("status");
      if (status) status.textContent = "Chart.js not loaded";
      return;
    }

    // kiểm element tối thiểu để tránh chết ngầm
    const ok =
      must("refresh") && must("label") && must("source") &&
      must("minutes") && must("status") &&
      must("chartLine") && must("chartSource") &&
      must("latestBody");

    if (!ok) {
      const status = $("status");
      if (status) status.textContent = "HTML/template mismatch (check console)";
      return;
    }

    $("refresh").addEventListener("click", refreshAll);
    $("label").addEventListener("change", refreshAll);
    $("source").addEventListener("change", refreshAll);

    refreshAll();
    setInterval(refreshAll, 5000);
  });
})();

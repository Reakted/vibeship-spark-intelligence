(function () {
  function esc(text) {
    if (text === null || text === undefined) return "";
    const div = document.createElement("div");
    div.textContent = String(text);
    return div.innerHTML;
  }

  function tag(text, cls) {
    return `<span class="tag ${cls || ""}">${esc(text)}</span>`;
  }

  function row(k, vHtml) {
    return `<div class="row"><span>${esc(k)}</span>${vHtml}</div>`;
  }

  function kpi(label, value, sub) {
    return `<div class="kpi-card"><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${esc(
      value
    )}</div><div class="kpi-sub">${esc(sub || "")}</div></div>`;
  }

  async function fetchJson(url) {
    const r = await fetch(url, { cache: "no-store" });
    return await r.json();
  }

  function renderMission(data) {
    const services = data.services || {};
    const entries = Object.entries(services);
    const up = entries.filter(([_, s]) => s && (s.healthy || s.running)).length;
    const queue = data.queue || {};
    const eidos = data.eidos || {};
    const watchers = data.watchers || [];
    const runs = data.runs || [];

    const kpisHtml =
      `<section class="kpi-grid" aria-label="KPIs">` +
      kpi("Services Up", up, `${up} / ${entries.length}`) +
      kpi("Queue Depth", queue.depth ?? queue.queue_depth ?? "-", "events queued") +
      kpi("Oldest", queue.oldest_age ?? queue.oldest_age_s ?? "-", "queue age") +
      kpi("Active EIDOS", eidos.active_episodes ?? "-", "episodes") +
      kpi("Watchers", watchers.length, "feed size") +
      kpi("Memory", data.process_memory_mb ?? "-", "process MB") +
      `</section>`;

    const servicesRows =
      entries
        .map(([name, s]) => {
          const ok = !!(s && (s.healthy || s.running));
          return row(name, tag(ok ? "up" : "down", ok ? "pos" : "neg"));
        })
        .join("") || `<div class="muted">No service data.</div>`;

    const watcherRows =
      watchers
        .slice(0, 14)
        .map((w) => {
          const sev = String(w.severity || "info").toLowerCase();
          const cls = sev.includes("block") || sev.includes("error") ? "neg" : sev.includes("warn") ? "neu" : "pos";
          const msg = w.message || w.watcher || "watcher";
          return row(String(msg).slice(0, 72), tag(sev, cls));
        })
        .join("") || `<div class="muted">No watcher alerts.</div>`;

    const runRows =
      runs
        .slice(0, 8)
        .map((rn) => {
          const outcome = String(rn.outcome || rn.status || "unknown").toLowerCase();
          const cls = outcome.includes("success") ? "pos" : outcome.includes("fail") ? "neg" : "neu";
          const label = rn.goal || rn.intent || rn.episode_id || rn.id || "run";
          return row(String(label).slice(0, 72), tag(outcome, cls));
        })
        .join("") || `<div class="muted">No recent runs.</div>`;

    const adv = data.advisory || {};
    const delivery = adv.delivery_badge || {};
    const advRows =
      row("state", tag(delivery.state || "unknown", String(delivery.state || "").toLowerCase() === "live" ? "pos" : "neu")) +
      row("provider", `<span class="muted">${esc(delivery.provider || adv.provider || "-")}</span>`) +
      row("model", `<span class="muted">${esc(delivery.model || adv.model || "-")}</span>`);

    const bridge = data.bridge || {};
    const bridgeRows =
      row("last_run", `<span class="muted">${esc(bridge.last_run || "-")}</span>`) +
      row("events", `<span class="muted">${esc(bridge.events_processed ?? "-")}</span>`) +
      row("learned", `<span class="muted">${esc(bridge.content_learned ?? "-")}</span>`);

    const queueRows =
      (queue.oldest_age ? row("oldest", `<span class="muted">${esc(queue.oldest_age)}</span>`) : "") +
      (queue.depth !== undefined ? row("depth", `<span class="muted">${esc(queue.depth)}</span>`) : "") +
      (queue.invalid_events !== undefined ? row("invalid", `<span class="muted">${esc(queue.invalid_events)}</span>`) : "") +
      (queue.lock_present !== undefined
        ? row("lock", tag(queue.lock_present ? "present" : "none", queue.lock_present ? "neg" : "pos"))
        : "") ||
      `<div class="muted">No queue data.</div>`;

    return (
      kpisHtml +
      `<section class="grid">` +
      `<div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Services</div><div class="muted">${entries.length} tracked</div></div><div class="panel-body">${servicesRows}</div></div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Watchers</div><div class="muted">latest</div></div><div class="panel-body">${watcherRows}</div></div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Recent Runs</div><div class="muted">last 8</div></div><div class="panel-body">${runRows}</div></div>` +
      `</div>` +
      `<div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Queue</div><div class="muted">health</div></div><div class="panel-body">${queueRows}</div></div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Advisory</div><div class="muted">delivery</div></div><div class="panel-body">${advRows}</div></div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Bridge</div><div class="muted">heartbeat</div></div><div class="panel-body">${bridgeRows}</div></div>` +
      `</div>` +
      `</section>`
    );
  }

  function renderOps(data) {
    const cats = data.categories || {};
    const needs = data.needs_attention || [];
    const top = data.top_performers || [];
    const used = data.most_used || [];
    const handoffs = data.recent_handoffs || [];
    const adv = data.advisory || {};
    const delivery = adv.delivery_badge || {};

    const kpisHtml =
      `<section class="kpi-grid" aria-label="KPIs">` +
      kpi("Skills", data.skills_total ?? "-", "indexed") +
      kpi("Needs Attention", needs.length, "low success") +
      kpi("Top Performers", top.length, "high success") +
      kpi("No Signal", data.no_signal_count ?? (data.no_signal_skills || []).length, "0 outcomes") +
      kpi("Best Pairs", (data.best_pairs || []).length, "agent handoffs") +
      kpi("Risky Pairs", (data.risky_pairs || []).length, "handoff failures") +
      `</section>`;

    function skillRows(items, mode) {
      if (!items.length) return `<div class="muted">No data.</div>`;
      return items
        .slice(0, 10)
        .map((it) => {
          const label = it.skill || it.name || "skill";
          const rate = Math.round((it.rate || 0) * 100);
          const total = it.total ?? "";
          const cls = mode === "bad" ? (rate >= 55 ? "neu" : "neg") : "pos";
          return row(`${String(label).slice(0, 60)} (${total})`, tag(`${rate}%`, cls));
        })
        .join("");
    }

    const catRows =
      Object.entries(cats)
        .sort((a, b) => (b[1] || 0) - (a[1] || 0))
        .map(([k, v]) => row(k, `<span class="muted">${esc(v)}</span>`))
        .join("") || `<div class="muted">No category breakdown.</div>`;

    const handoffRows =
      handoffs
        .slice(0, 10)
        .map((h) => {
          const pair = `${h.from_agent || "unknown"} -> ${h.to_agent || "unknown"}`;
          const ok = h.success;
          const cls = ok === true ? "pos" : ok === false ? "neg" : "neu";
          const label = ok === true ? "success" : ok === false ? "fail" : "unknown";
          return row(String(pair).slice(0, 72), tag(label, cls));
        })
        .join("") || `<div class="muted">No handoffs recorded.</div>`;

    const advRows =
      row("state", tag(delivery.state || "unknown", String(delivery.state || "").toLowerCase() === "live" ? "pos" : "neu")) +
      row("provider", `<span class="muted">${esc(delivery.provider || adv.provider || "-")}</span>`) +
      row("model", `<span class="muted">${esc(delivery.model || adv.model || "-")}</span>`);

    return (
      kpisHtml +
      `<section class="grid">` +
      `<div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Needs Attention</div><div class="muted">top</div></div><div class="panel-body">${skillRows(
        needs,
        "bad"
      )}</div></div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Top Performers</div><div class="muted">top</div></div><div class="panel-body">${skillRows(
        top,
        "good"
      )}</div></div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Most Used</div><div class="muted">top</div></div><div class="panel-body">${skillRows(
        used,
        "use"
      )}</div></div>` +
      `</div>` +
      `<div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Categories</div><div class="muted">skills</div></div><div class="panel-body">${catRows}</div></div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Recent Handoffs</div><div class="muted">last</div></div><div class="panel-body">${handoffRows}</div></div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Advisory</div><div class="muted">delivery</div></div><div class="panel-body">${advRows}</div></div>` +
      `</div>` +
      `</section>`
    );
  }

  function renderLearning(data) {
    if (!data.available) {
      return `<div class="panel"><div class="panel-header"><div class="panel-title">Learning Factory</div><div class="muted">unavailable</div></div><div class="panel-body"><div class="muted">EIDOS is not installed/running, so learning stats are unavailable.</div></div></div>`;
    }

    const dist = data.distillations || {};
    const promo = data.promotion || {};
    const ledger = data.truth_ledger || {};
    const util = data.utilization || {};
    const reval = data.revalidation || {};
    const src = data.source_attribution || {};

    const kpisHtml =
      `<section class="kpi-grid" aria-label="KPIs">` +
      kpi("Total", dist.total ?? "-", "distillations") +
      kpi("Today", dist.today ?? "-", "distillations") +
      kpi("Last 7d", dist.last_7d ?? "-", "distillations") +
      kpi("Promoted", promo.promoted_count ?? promo.promoted ?? "-", "items") +
      kpi("Contradicted", ledger.contradicted ?? "-", "truth ledger") +
      kpi("Revalidate Due", reval.due ?? "-", "items") +
      `</section>`;

    function listRows(items, rightKey, cls) {
      if (!items || !items.length) return `<div class="muted">No data.</div>`;
      return items
        .slice(0, 10)
        .map((it) => row(String(it.statement || "").slice(0, 72), tag(it[rightKey] ?? 0, cls)))
        .join("");
    }

    const helpedRows = listRows(util.top_helped || [], "helped", "pos");
    const ignoredRows = listRows(util.top_ignored || [], "retrieved", "neu");

    const ev = ledger.evidence_levels || {};
    const ledgerRows =
      row("strong", tag(ev.strong ?? 0, "pos")) +
      row("weak", tag(ev.weak ?? 0, "neu")) +
      row("none", tag(ev.none ?? 0, "neg")) +
      row("contradicted", tag(ledger.contradicted ?? 0, (ledger.contradicted || 0) > 0 ? "neg" : "pos"));

    const promoRows =
      (promo.recent_promoted || [])
        .slice(0, 10)
        .map((it) => row(String(it.insight || "").slice(0, 72), tag(`${Math.round((it.reliability || 0) * 100)}%`, "neu")))
        .join("") || `<div class="muted">No recent promoted items.</div>`;

    const srcRows =
      (src.rows || [])
        .slice(0, 10)
        .map((r) => row(r.source || r.name || "source", `<span class="muted">${esc(r.count ?? r.total ?? "")}</span>`))
        .join("") || `<div class="muted">No source attribution.</div>`;

    return (
      kpisHtml +
      `<section class="grid">` +
      `<div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Top Helped</div><div class="muted">times helped</div></div><div class="panel-body">${helpedRows}</div></div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Top Ignored</div><div class="muted">retrieved, not used</div></div><div class="panel-body">${ignoredRows}</div></div>` +
      `</div>` +
      `<div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Truth Ledger</div><div class="muted">evidence</div></div><div class="panel-body">${ledgerRows}</div></div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Promotion</div><div class="muted">recent</div></div><div class="panel-body">${promoRows}</div></div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Source Attribution</div><div class="muted">top sources</div></div><div class="panel-body">${srcRows}</div></div>` +
      `</div>` +
      `</section>`
    );
  }

  function renderMetaRalph(data) {
    const ralph = data.ralph || {};
    const totals = ralph.totals || {};
    const rates = ralph.rates || {};
    const avg = ralph.avg_scores || {};
    const outcomes = ralph.outcomes || {};

    const kpisHtml =
      `<section class="kpi-grid" aria-label="KPIs">` +
      kpi("Roasted", totals.roasted ?? "-", "total items") +
      kpi("Pass Rate", `${Math.round((rates.pass_rate || 0) * 100)}%`, "quality gate") +
      kpi("Avg Total", avg.total !== undefined ? Number(avg.total).toFixed(2) : "-", "score") +
      kpi("Refinements", totals.refinements_made ?? "-", "made") +
      kpi("Effectiveness", `${Math.round((outcomes.effectiveness || 0) * 100)}%`, "good / acted") +
      kpi("Learnings", totals.learnings_stored ?? "-", "stored") +
      `</section>`;

    const recs =
      (data.recommendations || [])
        .slice(0, 10)
        .map((rc) => {
          const pr = String(rc.priority || "info").toLowerCase();
          const cls = pr.includes("high") ? "neg" : pr.includes("success") ? "pos" : "neu";
          return row(
            `${rc.dimension || "rec"}: ${String(rc.fix || "").slice(0, 72)}`,
            tag(rc.priority || "info", cls)
          );
        })
        .join("") || `<div class="muted">No recommendations.</div>`;

    const roasts =
      (ralph.recent_roasts || [])
        .slice(0, 20)
        .map((rt) => {
          const v = String(rt.verdict || "unknown").toLowerCase();
          const cls = v.includes("quality") ? "pos" : v.includes("primitive") ? "neg" : "neu";
          return row(String(rt.text || "").slice(0, 72), tag(v, cls));
        })
        .join("") || `<div class="muted">No roasts yet.</div>`;

    const avgRows =
      Object.entries(avg)
        .map(([k, v]) => row(k, tag(Number(v || 0).toFixed(2), "neu")))
        .join("") || `<div class="muted">No averages.</div>`;

    const bySource = (data.advice || {}).by_source || {};
    const srcRows =
      Object.entries(bySource)
        .sort((a, b) => ((b[1] && b[1].count) || 0) - ((a[1] && a[1].count) || 0))
        .slice(0, 10)
        .map(([k, v]) => row(k, `<span class="muted">${esc((v && v.count) || 0)}</span>`))
        .join("") || `<div class="muted">No source analysis.</div>`;

    return (
      kpisHtml +
      `<section class="grid">` +
      `<div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Recommendations</div><div class="muted">auto</div></div><div class="panel-body">${recs}</div></div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Recent Roasts</div><div class="muted">last 20</div></div><div class="panel-body">${roasts}</div></div>` +
      `</div>` +
      `<div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Averages</div><div class="muted">dimensions</div></div><div class="panel-body">${avgRows}</div></div>` +
      `<div class="panel"><div class="panel-header"><div class="panel-title">Advice Sources</div><div class="muted">last 500</div></div><div class="panel-body">${srcRows}</div></div>` +
      `</div>` +
      `</section>`
    );
  }

  async function loadAndRender(page) {
    const meta = document.getElementById("meta");
    const app = document.getElementById("app");
    meta.textContent = "Loading...";
    try {
      const url =
        page === "mission"
          ? "/api/mission"
          : page === "ops"
          ? "/api/ops"
          : page === "learning"
          ? "/api/learning"
          : "/api/meta-ralph";
      const data = await fetchJson(url);
      if (!data.ok) throw new Error(data.error || "request failed");

      app.innerHTML =
        page === "mission"
          ? renderMission(data)
          : page === "ops"
          ? renderOps(data)
          : page === "learning"
          ? renderLearning(data)
          : renderMetaRalph(data);
      meta.textContent = `Updated ${new Date().toLocaleTimeString()}`;
    } catch (e) {
      meta.textContent = `Error: ${e}`;
      app.innerHTML = `<div class="panel"><div class="panel-header"><div class="panel-title">Error</div><div class="muted">render</div></div><div class="panel-body"><div class="mono">${esc(
        String(e)
      )}</div></div></div>`;
    }
  }

  window.HubPages = {
    init: function (page) {
      const btn = document.getElementById("refresh");
      if (btn) btn.addEventListener("click", () => loadAndRender(page));
      loadAndRender(page);
    },
  };
})();


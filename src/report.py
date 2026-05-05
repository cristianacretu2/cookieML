# =============================================================================
# report.py — Generarea raportului HTML final (modul NOU)
# =============================================================================
#
# CE FACE?
# Primește datele de la analyzer.py și generează un fișier HTML complet
# cu dashboard vizual: grafice, tabel de cookies, GDPR verdict și recomandări.
#
# TECHNOLOGIE:
# - HTML + CSS pur (fără framework-uri)
# - Chart.js (librărie JS pentru grafice) — inclusă via CDN
# - Totul e într-un singur fișier .html — ușor de deschis și trimis
# =============================================================================

from datetime import datetime
import json
import os


# =============================================================================
# FUNCȚIA PRINCIPALĂ: generate_report()
# =============================================================================

def generate_report(analysis_data, output_path="report.html"):
    """
    Generează raportul HTML complet.

    Parametri:
      analysis_data - dict returnat de analyzer.analyze_site()
      output_path   - unde se salvează fișierul HTML

    Returnează:
      calea absolută a fișierului generat
    """
    html = _build_html(analysis_data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    abs_path = os.path.abspath(output_path)
    print(f"\n✓ Raport generat: {abs_path}")
    print(f"  Deschide în browser: file://{abs_path}")
    return abs_path


# =============================================================================
# BUILDER HTML — construiește fișierul HTML complet
# =============================================================================

def _build_html(data):
    """Construiește HTML-ul complet al raportului."""

    site_url      = data["site_url"]
    cookies       = data["cookies"]
    stats         = data["stats"]
    gdpr_score    = data["gdpr_score"]
    verdict       = data["gdpr_verdict"]
    pages_scanned = data["pages_scanned"]
    scan_date     = datetime.now().strftime("%d %B %Y, %H:%M")

    # Date pentru grafice — le convertim la JSON pentru Chart.js
    categories_chart = {
        "labels": list(stats["by_category"].keys()),
        "data":   list(stats["by_category"].values()),
    }

    # Culorile pentru fiecare categorie — asociate cu riscul GDPR
    category_colors = {
        "Strictly Necessary": "#22c55e",   # verde — ok
        "Preferences":        "#3b82f6",   # albastru — neutru
        "Analytics":          "#f59e0b",   # galben — atenție
        "Marketing":          "#ef4444",   # roșu — risc
        "Unclassified":       "#94a3b8",   # gri — necunoscut
    }

    # culori în ordinea categoriilor din grafic
    chart_colors = [category_colors.get(cat, "#94a3b8") for cat in categories_chart["labels"]]

    # culorile pentru GDPR score
    if gdpr_score <= 20:
        score_color = "#22c55e"
        score_bg    = "#f0fdf4"
    elif gdpr_score <= 50:
        score_color = "#f59e0b"
        score_bg    = "#fffbeb"
    else:
        score_color = "#ef4444"
        score_bg    = "#fef2f2"

    # construim rândurile tabelului de cookies
    table_rows = _build_table_rows(cookies, category_colors)

    # construim lista de recomandări
    recommendations_html = "".join(
        f'<li class="recommendation-item">{action}</li>'
        for action in verdict["actions"]
    )

    # data pentru graficul First vs Third Party
    party_chart = {
        "labels": ["First-party", "Third-party"],
        "data":   [stats["first_party"], stats["third_party"]],
        "colors": ["#3b82f6", "#ef4444"]
    }

    # statistici per metodă de clasificare
    method_counts = {}
    for c in cookies:
        m = c.get("method", "ml")
        method_counts[m] = method_counts.get(m, 0) + 1

    n_known    = method_counts.get("known_cookie", 0)
    n_ml       = method_counts.get("ml", 0)
    n_uncertain = method_counts.get("ml_uncertain", 0)

    method_chart = {
        "labels": ["Dicționar (cert)", "Model ML", "Nesigur"],
        "data":   [n_known, n_ml, n_uncertain],
        "colors": ["#1d4ed8", "#6d28d9", "#c2410c"]
    }

    return f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cookie Audit — {site_url}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  /* ============================================================
     RESET & VARIABILE
     ============================================================ */
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --font-main:   'Segoe UI', system-ui, -apple-system, sans-serif;
    --font-mono:   'Cascadia Code', 'Fira Code', monospace;
    --bg:          #f8fafc;
    --surface:     #ffffff;
    --border:      #e2e8f0;
    --text:        #1e293b;
    --text-muted:  #64748b;
    --accent:      #6366f1;   /* indigo — culoarea principală */
    --radius:      12px;
    --shadow:      0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
    --shadow-lg:   0 10px 15px -3px rgba(0,0,0,0.1);
  }}

  body {{
    font-family: var(--font-main);
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    font-size: 14px;
  }}

  /* ============================================================
     LAYOUT
     ============================================================ */
  .container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}

  /* Header principal */
  .header {{
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
    color: white;
    padding: 40px;
    border-radius: var(--radius);
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
  }}

  .header::before {{
    content: '';
    position: absolute;
    top: -50%; right: -10%;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 70%);
    border-radius: 50%;
  }}

  .header-badge {{
    display: inline-block;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.2);
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 12px;
    margin-bottom: 16px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }}

  .header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 4px; }}
  .header .site-url {{ font-size: 16px; opacity: 0.8; margin-bottom: 16px; }}
  .header .meta {{ font-size: 13px; opacity: 0.6; }}

  /* ============================================================
     CARDURI METRICE (rândul de sus)
     ============================================================ */
  .metrics-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }}

  .metric-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
  }}

  .metric-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent);
  }}

  .metric-label {{
    font-size: 12px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
  }}

  .metric-value {{
    font-size: 32px;
    font-weight: 700;
    color: var(--text);
    line-height: 1;
  }}

  .metric-sub {{
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
  }}

  /* ============================================================
     RÂNDUL CU GRAFICE + GDPR
     ============================================================ */
  .charts-row {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16px;
    margin-bottom: 24px;
  }}

  @media (max-width: 900px) {{
    .charts-row {{ grid-template-columns: 1fr; }}
  }}

  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    box-shadow: var(--shadow);
  }}

  .card-title {{
    font-size: 14px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 20px;
  }}

  .chart-container {{ height: 200px; position: relative; }}

  /* GDPR Score */
  .gdpr-score-display {{
    text-align: center;
    padding: 16px;
    border-radius: 8px;
    background: {score_bg};
    margin-bottom: 16px;
  }}

  .gdpr-score-number {{
    font-size: 56px;
    font-weight: 800;
    color: {score_color};
    line-height: 1;
  }}

  .gdpr-score-label {{
    font-size: 13px;
    color: var(--text-muted);
    margin-top: 4px;
  }}

  .gdpr-verdict-level {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 600;
    background: {score_bg};
    color: {score_color};
    border: 1.5px solid {score_color}40;
    margin-bottom: 12px;
  }}

  .gdpr-verdict-text {{
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.5;
  }}

  /* ============================================================
     RECOMANDĂRI
     ============================================================ */
  .recommendations {{ margin-bottom: 24px; }}

  .recommendations .card-title {{ margin-bottom: 12px; }}

  .recommendation-item {{
    padding: 10px 14px;
    border-left: 3px solid {score_color};
    background: {score_bg};
    border-radius: 0 8px 8px 0;
    margin-bottom: 8px;
    font-size: 13px;
    color: var(--text);
    list-style: none;
  }}

  /* ============================================================
     TABEL COOKIES
     ============================================================ */
  .table-section {{ margin-bottom: 24px; }}

  .table-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }}

  .table-header h2 {{
    font-size: 18px;
    font-weight: 700;
  }}

  .filter-bar {{
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }}

  .filter-btn {{
    padding: 6px 14px;
    border-radius: 999px;
    border: 1.5px solid var(--border);
    background: var(--surface);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    color: var(--text-muted);
    transition: all 0.15s;
  }}

  .filter-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
  .filter-btn.active {{ background: var(--accent); color: white; border-color: var(--accent); }}

  .table-wrapper {{ overflow-x: auto; border-radius: var(--radius); box-shadow: var(--shadow); }}

  table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--surface);
    font-size: 13px;
  }}

  thead th {{
    padding: 12px 16px;
    text-align: left;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    background: #f8fafc;
  }}

  tbody tr {{ transition: background 0.1s; }}
  tbody tr:hover {{ background: #f8fafc; }}
  tbody tr.hidden {{ display: none; }}

  td {{
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }}

  td:first-child {{ font-family: var(--font-mono); font-size: 12px; font-weight: 600; }}

  .category-badge {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
  }}

  .badge-dot {{ width: 6px; height: 6px; border-radius: 50%; }}

  .conf-bar-wrap {{ display: flex; align-items: center; gap: 8px; }}
  .conf-bar {{
    height: 4px;
    border-radius: 2px;
    background: #e2e8f0;
    width: 60px;
    overflow: hidden;
  }}
  .conf-bar-fill {{ height: 100%; border-radius: 2px; background: var(--accent); }}
  .conf-text {{ font-size: 11px; color: var(--text-muted); min-width: 30px; }}

  .party-tag {{
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
  }}

  .party-third {{
    background: #fef2f2;
    color: #dc2626;
  }}

  .party-first {{
    background: #f0fdf4;
    color: #16a34a;
  }}

  /* Badge metodă clasificare */
  .method-tag {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 600;
    white-space: nowrap;
  }}

  .method-known    {{ background: #eff6ff; color: #1d4ed8; }}
  .method-ml       {{ background: #f5f3ff; color: #6d28d9; }}
  .method-uncertain {{ background: #fff7ed; color: #c2410c; }}

  /* Sectiune explicativa metode */
  .method-legend {{
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    padding: 14px 18px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    margin-bottom: 12px;
    font-size: 12px;
  }}

  .method-legend-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-muted);
  }}

  /* ============================================================
     FOOTER
     ============================================================ */
  .footer {{
    text-align: center;
    padding: 20px;
    font-size: 12px;
    color: var(--text-muted);
    border-top: 1px solid var(--border);
    margin-top: 24px;
  }}
</style>
</head>

<body>
<div class="container">

  <!-- HEADER -->
  <div class="header">
    <div class="header-badge">Cookie Audit Report</div>
    <h1>🍪 GDPR Cookie Scanner</h1>
    <div class="site-url">{site_url}</div>
    <div class="meta">
      Scanat pe: {scan_date} &nbsp;·&nbsp;
      {pages_scanned} pagini analizate &nbsp;·&nbsp;
      {stats['total']} cookies unice
    </div>
  </div>

  <!-- METRICI PRINCIPALE -->
  <div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-label">Total cookies</div>
      <div class="metric-value">{stats['total']}</div>
      <div class="metric-sub">unice pe site</div>
    </div>
    <div class="metric-card" style="--accent: #22c55e">
      <div class="metric-label">Strictly Necessary</div>
      <div class="metric-value">{stats['by_category'].get('Strictly Necessary', 0)}</div>
      <div class="metric-sub">nu necesită consent</div>
    </div>
    <div class="metric-card" style="--accent: #f59e0b">
      <div class="metric-label">Analytics</div>
      <div class="metric-value">{stats['by_category'].get('Analytics', 0)}</div>
      <div class="metric-sub">necesită consent</div>
    </div>
    <div class="metric-card" style="--accent: #ef4444">
      <div class="metric-label">Marketing</div>
      <div class="metric-value">{stats['by_category'].get('Marketing', 0)}</div>
      <div class="metric-sub">risc GDPR ridicat</div>
    </div>
    <div class="metric-card" style="--accent: #3b82f6">
      <div class="metric-label">Preferences</div>
      <div class="metric-value">{stats['by_category'].get('Preferences', 0)}</div>
      <div class="metric-sub">necesită consent</div>
    </div>
    <div class="metric-card" style="--accent: #8b5cf6">
      <div class="metric-label">Third-party</div>
      <div class="metric-value">{stats['third_party']}</div>
      <div class="metric-sub">{stats['third_party_pct']}% din total</div>
    </div>
  </div>

  <!-- GRAFICE + GDPR — 4 coloane -->
  <div class="charts-row" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr))">

    <!-- Grafic donut categorii -->
    <div class="card">
      <div class="card-title">Distribuție categorii</div>
      <div class="chart-container">
        <canvas id="categoriesChart"></canvas>
      </div>
    </div>

    <!-- Grafic First vs Third party -->
    <div class="card">
      <div class="card-title">First vs Third-party</div>
      <div class="chart-container">
        <canvas id="partyChart"></canvas>
      </div>
    </div>

    <!-- Grafic metode clasificare NOU -->
    <div class="card">
      <div class="card-title">Metode de clasificare</div>
      <div class="chart-container">
        <canvas id="methodChart"></canvas>
      </div>
    </div>

    <!-- GDPR Score -->
    <div class="card">
      <div class="card-title">GDPR Risk Score</div>
      <div class="gdpr-score-display">
        <div class="gdpr-score-number">{gdpr_score}</div>
        <div class="gdpr-score-label">din 100</div>
      </div>
      <div class="gdpr-verdict-level">
        {verdict['emoji']} Risc {verdict['level']}
      </div>
      <div class="gdpr-verdict-text">{verdict['verdict']}</div>
    </div>

  </div>

  <!-- RECOMANDĂRI GDPR -->
  <div class="card recommendations">
    <div class="card-title">⚡ Acțiuni recomandate</div>
    <ul>{recommendations_html}</ul>
  </div>

  <!-- TABEL COOKIES -->
  <div class="table-section">
    <div class="table-header">
      <h2>📋 Toate cookie-urile ({stats['total']})</h2>
    </div>

    <div class="filter-bar">
      <button class="filter-btn active" onclick="filterTable('all', event)">Toate ({stats['total']})</button>
      <button class="filter-btn" onclick="filterTable('cat:Marketing', event)" style="border-color: #fecaca; color: #dc2626">
        🔴 Marketing ({stats['by_category'].get('Marketing', 0)})
      </button>
      <button class="filter-btn" onclick="filterTable('cat:Analytics', event)" style="border-color: #fde68a; color: #d97706">
        🟡 Analytics ({stats['by_category'].get('Analytics', 0)})
      </button>
      <button class="filter-btn" onclick="filterTable('cat:Strictly Necessary', event)" style="border-color: #bbf7d0; color: #16a34a">
        🟢 Necessary ({stats['by_category'].get('Strictly Necessary', 0)})
      </button>
      <button class="filter-btn" onclick="filterTable('cat:Preferences', event)" style="border-color: #bfdbfe; color: #2563eb">
        🔵 Preferences ({stats['by_category'].get('Preferences', 0)})
      </button>
      <button class="filter-btn" onclick="filterTable('party:third', event)" style="border-color: #e9d5ff; color: #7c3aed">
        Third-party ({stats['third_party']})
      </button>
      <button class="filter-btn" onclick="filterTable('method:known_cookie', event)" style="border-color: #bfdbfe; color: #1d4ed8">
        🔷 Dicționar ({n_known})
      </button>
      <button class="filter-btn" onclick="filterTable('method:ml', event)" style="border-color: #ddd6fe; color: #6d28d9">
        🤖 Model ML ({n_ml})
      </button>
      <button class="filter-btn" onclick="filterTable('method:ml_uncertain', event)" style="border-color: #fed7aa; color: #c2410c">
        ⚠ Nesigur ({n_uncertain})
      </button>
    </div>

    <!-- Legendă explicativă metode -->
    <div class="method-legend">
      <div class="method-legend-item">
        <span class="method-tag method-known">🔷 Dicționar</span>
        Cookie identificat cu certitudine 100% din lista hardcodată (_ga, _fbp etc.)
      </div>
      <div class="method-legend-item">
        <span class="method-tag method-ml">🤖 Model ML</span>
        Clasificat de RandomForest pe baza celor 14 features, confidence ≥ 55%
      </div>
      <div class="method-legend-item">
        <span class="method-tag method-uncertain">⚠ Nesigur</span>
        Modelul are confidence &lt; 55% — cookie necunoscut, necesită review manual
      </div>
    </div>

    <div class="table-wrapper">
      <table id="cookiesTable">
        <thead>
          <tr>
            <th>Nume cookie</th>
            <th>Domeniu</th>
            <th>Categorie</th>
            <th>Durată</th>
            <th>Party</th>
            <th>Metodă</th>
            <th>Confidence</th>
            <th>Pagini</th>
          </tr>
        </thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>
    </div>
  </div>

  <div class="footer">
    Generat de Cookie Scanner &middot; {scan_date} &middot;
    Informațiile sunt orientative și nu constituie consultanță juridică GDPR.
  </div>

</div>

<script>
// ============================================================
// GRAFICE CU CHART.JS
// ============================================================

// Donut — distribuție categorii
const ctx1 = document.getElementById('categoriesChart').getContext('2d');
new Chart(ctx1, {{
  type: 'doughnut',
  data: {{
    labels: {json.dumps(categories_chart['labels'])},
    datasets: [{{
      data:            {json.dumps(categories_chart['data'])},
      backgroundColor: {json.dumps(chart_colors)},
      borderWidth: 2,
      borderColor: '#ffffff',
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{
        position: 'bottom',
        labels: {{ font: {{ size: 11 }}, padding: 8 }}
      }}
    }}
  }}
}});

// Donut — first vs third party
const ctx2 = document.getElementById('partyChart').getContext('2d');
new Chart(ctx2, {{
  type: 'doughnut',
  data: {{
    labels: {json.dumps(party_chart['labels'])},
    datasets: [{{
      data:            {json.dumps(party_chart['data'])},
      backgroundColor: {json.dumps(party_chart['colors'])},
      borderWidth: 2,
      borderColor: '#ffffff',
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{
        position: 'bottom',
        labels: {{ font: {{ size: 11 }}, padding: 8 }}
      }}
    }}
  }}
}});

// Donut — metode de clasificare
const ctx3 = document.getElementById('methodChart').getContext('2d');
new Chart(ctx3, {{
  type: 'doughnut',
  data: {{
    labels: {json.dumps(method_chart['labels'])},
    datasets: [{{
      data:            {json.dumps(method_chart['data'])},
      backgroundColor: {json.dumps(method_chart['colors'])},
      borderWidth: 2,
      borderColor: '#ffffff',
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{
        position: 'bottom',
        labels: {{ font: {{ size: 11 }}, padding: 8 }}
      }},
      tooltip: {{
        callbacks: {{
          label: function(ctx) {{
            const total = ctx.dataset.data.reduce((a,b) => a+b, 0);
            const pct = total ? Math.round(ctx.parsed / total * 100) : 0;
            return ` ${{ctx.label}}: ${{ctx.parsed}} (${{pct}}%)`;
          }}
        }}
      }}
    }}
  }}
}});

// ============================================================
// FILTRARE TABEL — suportă filtre pe categorie, party și metodă
// ============================================================
function filterTable(filter, event) {{
  document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
  if (event && event.target) event.target.classList.add('active');

  document.querySelectorAll('#cookiesTable tbody tr').forEach(row => {{
    if (filter === 'all') {{
      row.classList.remove('hidden');
      return;
    }}

    // filter are formatul "tip:valoare" — ex: "cat:Marketing", "party:third", "method:ml"
    const [type, value] = filter.split(':');

    let show = false;
    if (type === 'cat')    show = row.dataset.category === value;
    if (type === 'party')  show = row.dataset.party    === value;
    if (type === 'method') show = row.dataset.method   === value;

    row.classList.toggle('hidden', !show);
  }});
}}
</script>

</body>
</html>"""


# =============================================================================
# BUILDER RÂNDURI TABEL
# =============================================================================

def _build_table_rows(cookies, category_colors):
    """Construiește HTML-ul pentru rândurile tabelului."""
    rows = []

    for c in cookies:
        cat      = c["category"]
        cat_id   = c["category_id"]
        color    = category_colors.get(cat, "#94a3b8")
        party    = "third" if c["third_party"] else "first"
        conf     = c["confidence"]

        # culori pentru badge categorie
        cat_bg_map = {
            "Strictly Necessary": ("#f0fdf4", "#15803d"),
            "Preferences":        ("#eff6ff", "#1d4ed8"),
            "Analytics":          ("#fffbeb", "#b45309"),
            "Marketing":          ("#fef2f2", "#b91c1c"),
            "Unclassified":       ("#f1f5f9", "#64748b"),
        }
        bg_color, text_color = cat_bg_map.get(cat, ("#f1f5f9", "#64748b"))

        # emoji pentru fiecare categorie
        cat_emoji = {
            "Strictly Necessary": "🟢",
            "Preferences":        "🔵",
            "Analytics":          "🟡",
            "Marketing":          "🔴",
            "Unclassified":       "⚪",
        }.get(cat, "⚪")

        # bara de confidence
        conf_width = int(conf)  # conf e deja în procente (0-100)

        # tag first/third party
        if c["third_party"]:
            party_html = '<span class="party-tag party-third">3rd party</span>'
        else:
            party_html = '<span class="party-tag party-first">1st party</span>'

        # badge metodă de clasificare
        method = c.get("method", "ml")
        method_map = {
            "known_cookie": ("method-known",     "🔷 Dicționar"),
            "ml":           ("method-ml",        "🤖 Model ML"),
            "ml_uncertain": ("method-uncertain", "⚠ Nesigur"),
        }
        method_cls, method_label = method_map.get(method, ("method-ml", "🤖 Model ML"))
        method_html = f'<span class="method-tag {method_cls}">{method_label}</span>'

        rows.append(f"""
<tr data-category="{cat}" data-party="{party}" data-method="{method}">
  <td>{c['name']}</td>
  <td style="color: #64748b;">{c['domain']}</td>
  <td>
    <span class="category-badge" style="background:{bg_color}; color:{text_color}">
      {cat_emoji} {cat}
    </span>
  </td>
  <td style="color: #64748b;">{c['lifespan']}</td>
  <td>{party_html}</td>
  <td>{method_html}</td>
  <td>
    <div class="conf-bar-wrap">
      <div class="conf-bar">
        <div class="conf-bar-fill" style="width:{conf_width}%"></div>
      </div>
      <span class="conf-text">{conf:.0f}%</span>
    </div>
  </td>
  <td style="color: #64748b; text-align:center">{c['found_on_pages']}</td>
</tr>""")

    return "\n".join(rows)


# =============================================================================
# TEST RAPID — generează un raport demo
# =============================================================================

if __name__ == "__main__":
    # date demo pentru testare fără a rula scraper-ul
    demo_data = {
        "site_url":       "https://demo-site.ro",
        "pages_scanned":  5,
        "total_unique":   8,
        "cookies": [
            {"name": "_ga",         "domain": ".google-analytics.com", "category": "Analytics",          "category_id": 2, "confidence": 100.0, "third_party": True,  "lifespan": "2 years",  "found_on_pages": 5, "method": "known_cookie"},
            {"name": "_fbp",        "domain": ".facebook.com",         "category": "Marketing",          "category_id": 3, "confidence": 100.0, "third_party": True,  "lifespan": "3 months", "found_on_pages": 5, "method": "known_cookie"},
            {"name": "PHPSESSID",   "domain": "demo-site.ro",          "category": "Strictly Necessary", "category_id": 0, "confidence": 100.0, "third_party": False, "lifespan": "Session",  "found_on_pages": 5, "method": "known_cookie"},
            {"name": "lang",        "domain": "demo-site.ro",          "category": "Preferences",        "category_id": 1, "confidence": 85.0,  "third_party": False, "lifespan": "1 year",   "found_on_pages": 3, "method": "ml"},
            {"name": "IDE",         "domain": ".doubleclick.net",      "category": "Marketing",          "category_id": 3, "confidence": 100.0, "third_party": True,  "lifespan": "2 years",  "found_on_pages": 4, "method": "known_cookie"},
            {"name": "_hjid",       "domain": ".hotjar.com",           "category": "Analytics",          "category_id": 2, "confidence": 95.0,  "third_party": True,  "lifespan": "1 year",   "found_on_pages": 5, "method": "ml"},
            {"name": "csrftoken",   "domain": "demo-site.ro",          "category": "Strictly Necessary", "category_id": 0, "confidence": 100.0, "third_party": False, "lifespan": "Session",  "found_on_pages": 2, "method": "known_cookie"},
            {"name": "custom_pref", "domain": "demo-site.ro",          "category": "Unclassified",       "category_id": -1,"confidence": 42.0,  "third_party": False, "lifespan": "7 days",   "found_on_pages": 1, "method": "ml_uncertain"},
        ],
        "stats": {
            "total":              8,
            "by_category":        {"Analytics": 2, "Marketing": 2, "Strictly Necessary": 2, "Preferences": 1, "Unclassified": 1},
            "third_party":        4,
            "first_party":        4,
            "third_party_pct":    50.0,
            "low_confidence":     1,
            "session_cookies":    2,
            "persistent_cookies": 6,
        },
        "gdpr_score":    55,
        "gdpr_breakdown": {},
        "gdpr_verdict": {
            "level":   "Mediu",
            "color":   "yellow",
            "emoji":   "⚠️",
            "verdict": "Site-ul are cookies de analytics care necesită consent.",
            "actions": [
                "Implementați un banner de cookies conform (OneTrust, CookieYes etc.)",
                "Blocați cookies analytics până la obținerea consimțământului.",
                "Actualizați politica de confidențialitate cu toate cookie-urile.",
            ]
        },
    }

    generate_report(demo_data, "demo_report.html")
    print("Deschide demo_report.html în browser!")
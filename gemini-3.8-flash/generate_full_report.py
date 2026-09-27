import json

with open("engine-comparison-summary-data.json", "r") as f:
    raw_data = json.load(f)

# Compact the data for embedding
cluster_queries_compact = raw_data.get("clusterQueries", {})
cluster_totals = raw_data.get("cluster", {})
hardware_data = raw_data.get("hardware", {})
wins_data = raw_data.get("wins", {})
single_totals = raw_data.get("totals", {})
engines_list = raw_data.get("engines", [])

embedded_data = {
    "engines": engines_list,
    "totals": single_totals,
    "cluster": cluster_totals,
    "clusterQueries": cluster_queries_compact,
    "hardware": hardware_data,
    "wins": wins_data
}

embedded_json_str = json.dumps(embedded_data)

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SQL Engine Benchmark Suite | Single-Node & Distributed Cluster (SF10000 / 10 TB)</title>
  <style>
    :root {{
      --bg: #0b0f19;
      --surface: #111827;
      --surface-card: #1a2234;
      --surface-card-hover: #212c42;
      --border: #2e3a52;
      --border-subtle: #1e293b;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      
      --brand: #3b82f6;
      --brand-glow: rgba(59, 130, 246, 0.25);
      --success: #10b981;
      --success-subtle: rgba(16, 185, 129, 0.15);
      --warning: #f59e0b;
      --warning-subtle: rgba(245, 158, 11, 0.15);
      --danger: #ef4444;
      --danger-subtle: rgba(239, 68, 68, 0.15);
      --purple: #8b5cf6;
      --purple-subtle: rgba(139, 92, 246, 0.15);
      
      --engine-rust-def: #38bdf8;
      --engine-rust-tuned: #06b6d4;
      --engine-duckdb: #eab308;
      --engine-gluten: #a855f7;
      --engine-spark42: #ec4899;
      
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 16px;
      --shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
      --shadow-lg: 0 10px 30px -4px rgba(0, 0, 0, 0.6);
      
      --font-sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-sans);
      line-height: 1.5;
      font-size: 14px;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      -webkit-font-smoothing: antialiased;
    }}

    header {{
      background: linear-gradient(180deg, #131b2e 0%, var(--surface) 100%);
      border-bottom: 1px solid var(--border);
      padding: 20px 32px;
      position: sticky;
      top: 0;
      z-index: 40;
      backdrop-filter: blur(8px);
    }}

    .header-inner {{
      max-width: 1440px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 20px;
      flex-wrap: wrap;
    }}

    .brand-group {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}

    .logo-badge {{
      width: 44px;
      height: 44px;
      background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: var(--radius-md);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 15px var(--brand-glow);
    }}

    .logo-badge svg {{
      width: 24px;
      height: 24px;
      fill: none;
      stroke: white;
      stroke-width: 2;
    }}

    .brand-titles h1 {{
      font-size: 19px;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: #fff;
    }}

    .brand-titles p {{
      font-size: 12px;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .status-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--success);
      display: inline-block;
      box-shadow: 0 0 8px var(--success);
    }}

    .mode-nav {{
      display: flex;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 3px;
      gap: 2px;
    }}

    .mode-tab {{
      padding: 7px 18px;
      font-size: 13px;
      font-weight: 600;
      border: none;
      background: transparent;
      color: var(--text-muted);
      border-radius: 4px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }}

    .mode-tab.active {{
      background: var(--brand);
      color: #fff;
      box-shadow: 0 1px 3px rgba(0,0,0,0.4);
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 14px;
      border-radius: var(--radius-sm);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      border: 1px solid var(--border);
      background: var(--surface-card);
      color: var(--text);
      transition: all 0.2s ease;
    }}

    .btn:hover {{
      background: var(--surface-card-hover);
      border-color: var(--brand);
      color: #fff;
    }}

    .btn-primary {{
      background: var(--brand);
      border-color: #2563eb;
      color: white;
    }}

    main {{
      flex: 1;
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
      padding: 24px 32px 48px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }}

    /* Summary cards */
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
    }}

    .kpi-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
      transition: transform 0.2s ease;
    }}

    .kpi-card:hover {{
      transform: translateY(-2px);
    }}

    .kpi-card::before {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; height: 3px;
      background: var(--border);
    }}

    .kpi-card.blue::before {{ background: linear-gradient(90deg, #38bdf8, #2563eb); }}
    .kpi-card.gold::before {{ background: linear-gradient(90deg, #fbbf24, #d97706); }}
    .kpi-card.green::before {{ background: linear-gradient(90deg, #34d399, #059669); }}
    .kpi-card.purple::before {{ background: linear-gradient(90deg, #c084fc, #7c3aed); }}

    .kpi-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }}

    .kpi-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      font-weight: 600;
    }}

    .kpi-value {{
      font-size: 26px;
      font-weight: 700;
      color: #fff;
      font-family: var(--font-mono);
      letter-spacing: -0.03em;
      margin-bottom: 6px;
    }}

    .kpi-subtext {{
      font-size: 12px;
      color: var(--text-dim);
      line-height: 1.4;
    }}

    .badge-pill {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 600;
    }}

    .badge-win {{
      background: var(--success-subtle);
      color: #34d399;
      border: 1px solid rgba(52, 211, 153, 0.3);
    }}

    .badge-purple {{
      background: var(--purple-subtle);
      color: #c084fc;
      border: 1px solid rgba(192, 132, 252, 0.3);
    }}

    .badge-neutral {{
      background: rgba(148, 163, 184, 0.1);
      color: var(--text-muted);
      border: 1px solid var(--border);
    }}

    /* Controls Panel */
    .controls-panel {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 14px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 16px;
      box-shadow: var(--shadow);
    }}

    .filter-group {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}

    .filter-title {{
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    .segmented-control {{
      display: inline-flex;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 3px;
      gap: 2px;
    }}

    .segment-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 5px 12px;
      font-size: 12px;
      font-weight: 600;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s ease;
      white-space: nowrap;
    }}

    .segment-btn:hover {{ color: #fff; }}
    .segment-btn.active {{
      background: var(--surface-card);
      color: #fff;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
    }}

    /* Visual Dashboard Section */
    .dashboard-grid {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 20px;
    }}

    @media (max-width: 1024px) {{
      .dashboard-grid {{ grid-template-columns: 1fr; }}
    }}

    .panel-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}

    .panel-header {{
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}

    .panel-header h2 {{
      font-size: 15px;
      font-weight: 600;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .panel-header .subtitle {{
      font-size: 12px;
      color: var(--text-dim);
      font-weight: 400;
    }}

    .panel-body {{
      padding: 20px;
      flex: 1;
    }}

    /* Bar Charts */
    .bar-row {{
      display: grid;
      grid-template-columns: 210px 1fr 140px;
      align-items: center;
      gap: 16px;
      margin-bottom: 14px;
    }}

    .bar-label-box {{
      display: flex;
      flex-direction: column;
    }}

    .bar-label-main {{
      font-size: 13px;
      font-weight: 600;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .bar-label-tag {{
      font-size: 11px;
      color: var(--text-dim);
    }}

    .bar-track {{
      background: rgba(255, 255, 255, 0.04);
      height: 26px;
      border-radius: 4px;
      overflow: hidden;
      position: relative;
      display: flex;
      align-items: center;
      border: 1px solid var(--border-subtle);
    }}

    .bar-fill {{
      height: 100%;
      border-radius: 3px;
      transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    .bar-metrics {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      font-family: var(--font-mono);
    }}

    .bar-metric-time {{
      font-size: 13px;
      font-weight: 700;
      color: #fff;
    }}

    .bar-metric-ratio {{
      font-size: 11px;
      color: var(--text-muted);
    }}

    /* Table styles */
    .table-container {{
      overflow-x: auto;
    }}

    table.benchmark-table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 13px;
    }}

    table.benchmark-table th {{
      background: var(--bg);
      color: var(--text-muted);
      font-weight: 600;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
      cursor: pointer;
      user-select: none;
    }}

    table.benchmark-table th:hover {{ color: #fff; }}

    table.benchmark-table td {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--border-subtle);
      color: var(--text);
      white-space: nowrap;
    }}

    table.benchmark-table tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    table.benchmark-table .num-col {{
      text-align: right;
      font-family: var(--font-mono);
    }}

    .best-badge {{
      background: rgba(16, 185, 129, 0.2);
      color: #34d399;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 10px;
      border: 1px solid rgba(16, 185, 129, 0.4);
    }}

    /* Speedup List */
    .speedup-list {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .speedup-card {{
      background: var(--surface-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      padding: 12px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}

    .speedup-ratio-badge {{
      font-size: 13px;
      font-weight: 700;
      font-family: var(--font-mono);
      padding: 4px 10px;
      border-radius: 6px;
      white-space: nowrap;
    }}

    .ratio-baseline {{
      background: rgba(234, 179, 8, 0.15);
      color: #facc15;
      border: 1px solid rgba(234, 179, 8, 0.3);
    }}

    .ratio-faster {{
      background: var(--success-subtle);
      color: #34d399;
      border: 1px solid rgba(52, 211, 153, 0.3);
    }}

    .ratio-slower {{
      background: var(--danger-subtle);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }}

    /* Cluster deep dive specs */
    .hw-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}

    .hw-item {{
      background: var(--surface-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      padding: 12px 14px;
    }}

    .hw-item-label {{
      font-size: 11px;
      text-transform: uppercase;
      color: var(--text-dim);
      font-weight: 600;
      margin-bottom: 4px;
    }}

    .hw-item-val {{
      font-size: 15px;
      font-weight: 700;
      color: #fff;
      font-family: var(--font-mono);
    }}

    /* Cluster Query Table */
    .query-filter-bar {{
      display: flex;
      gap: 12px;
      align-items: center;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }}

    .input-search {{
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 6px 12px;
      color: #fff;
      font-size: 12px;
      width: 180px;
    }}

    .input-search:focus {{
      outline: none;
      border-color: var(--brand);
    }}

    /* Status badges */
    .status-badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .status-pass {{ background: var(--success-subtle); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); }}
    .status-gap {{ background: var(--danger-subtle); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
    .status-fail {{ background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid var(--border); }}

    /* Insights */
    .insights-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 16px;
    }}

    .insight-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 18px 20px;
      display: flex;
      gap: 14px;
    }}

    .insight-icon {{
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      color: var(--brand);
    }}

    .insight-body h3 {{
      font-size: 14px;
      font-weight: 600;
      color: #fff;
      margin-bottom: 4px;
    }}

    .insight-body p {{
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.5;
    }}

    footer {{
      border-top: 1px solid var(--border);
      background: var(--surface);
      padding: 20px 32px;
      font-size: 12px;
      color: var(--text-dim);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }}

    @media print {{
      body {{ background: #fff; color: #000; }}
      header, .controls-panel, .header-actions, .query-filter-bar {{ display: none !important; }}
      .panel-card, .kpi-card, .insight-card {{
        border: 1px solid #ccc;
        background: #fff !important;
        box-shadow: none !important;
        color: #000 !important;
      }}
      table.benchmark-table th {{ background: #f1f5f9 !important; color: #000 !important; }}
      table.benchmark-table td {{ color: #000 !important; }}
    }}
  </style>
</head>
<body>

  <!-- Top Navigation Header -->
  <header>
    <div class="header-inner">
      <div class="brand-group">
        <div class="logo-badge" title="Query Engine Benchmark Suite">
          <svg viewBox="0 0 24 24">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
          </svg>
        </div>
        <div class="brand-titles">
          <h1>SQL Engine Benchmark Executive Suite</h1>
          <p><span class="status-dot"></span> Single-Node &bull; 8-Node Distributed Cluster &bull; SF1 &ndash; SF10000 (10 TB)</p>
        </div>
      </div>

      <!-- Top Primary Track Switcher -->
      <div class="mode-nav">
        <button class="mode-tab active" id="tabCluster" data-track="cluster">
          <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
          Distributed Cluster (SF10000)
        </button>
        <button class="mode-tab" id="tabSingle" data-track="single">
          <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <rect x="4" y="4" width="16" height="16" rx="2"/>
            <path d="M9 9h6v6H9z"/>
          </svg>
          Single-Node (SF1 &ndash; SF1000)
        </button>
      </div>

      <div class="header-actions">
        <button class="btn" id="exportCsvBtn" title="Export current benchmark matrix to CSV">
          <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>
          </svg>
          Export CSV
        </button>
        <button class="btn btn-primary" onclick="window.print()" title="Print report or save as PDF">
          <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
            <path d="M6 14h12v8H6z"/>
          </svg>
          Print Report
        </button>
      </div>
    </div>
  </header>

  <main>

    <!-- KPI Summary Cards -->
    <div class="summary-grid" id="kpiContainer">
      <!-- Populated dynamically via JavaScript -->
    </div>

    <!-- Cluster Hardware Banner (Only in Cluster Mode) -->
    <div id="clusterHwBanner" class="panel-card" style="padding: 16px 20px;">
      <div style="font-size:12px; text-transform:uppercase; font-weight:700; color:var(--text-muted); margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
        <span>Distributed Hardware Configuration: Azure Standard_E16ads_v5 Cluster</span>
        <span class="badge-pill badge-neutral">ADLS Gen2 Storage &bull; Parquet</span>
      </div>
      <div class="hw-grid">
        <div class="hw-item">
          <div class="hw-item-label">Worker Nodes</div>
          <div class="hw-item-val">8 Dedicated VMs</div>
        </div>
        <div class="hw-item">
          <div class="hw-item-label">Total Cluster Cores</div>
          <div class="hw-item-val">128 vCPUs (16 / node)</div>
        </div>
        <div class="hw-item">
          <div class="hw-item-label">Total Cluster RAM</div>
          <div class="hw-item-val">1,024 GB (128 GB / node)</div>
        </div>
        <div class="hw-item">
          <div class="hw-item-label">Benchmark Suite</div>
          <div class="hw-item-val">TPC-DS (SF100, 1000, 10000)</div>
        </div>
      </div>
    </div>

    <!-- Interactive Filters -->
    <div class="controls-panel">
      <!-- Cluster-specific Scale Factor switcher -->
      <div class="filter-group" id="clusterFilterGroup">
        <span class="filter-title">Cluster Scale Factor:</span>
        <div class="segmented-control" id="clusterSfFilter">
          <button class="segment-btn active" data-sf="10000">SF10000 (10 TB &bull; 94 queries)</button>
          <button class="segment-btn" data-sf="1000">SF1000 (1 TB &bull; 99 queries)</button>
          <button class="segment-btn" data-sf="100">SF100 (100 GB &bull; 99 queries)</button>
        </div>
      </div>

      <!-- Single-node specific controls -->
      <div class="filter-group" id="singleFilterGroup" style="display:none;">
        <span class="filter-title">Benchmark:</span>
        <div class="segmented-control" id="singleBenchFilter">
          <button class="segment-btn active" data-bench="TPC-DS">TPC-DS (99 Queries)</button>
          <button class="segment-btn" data-bench="TPC-H">TPC-H (22 Queries)</button>
          <button class="segment-btn" data-bench="COMBINED">Aggregated Overview</button>
        </div>
        <span class="filter-title" style="margin-left: 10px;">Scale Factor:</span>
        <div class="segmented-control" id="singleSfFilter">
          <button class="segment-btn active" data-sf="1000">SF1000</button>
          <button class="segment-btn" data-sf="100">SF100</button>
          <button class="segment-btn" data-sf="10">SF10</button>
          <button class="segment-btn" data-sf="1">SF1</button>
          <button class="segment-btn" data-sf="all">All Scales</button>
        </div>
      </div>

      <!-- Metric Toggle -->
      <div class="filter-group">
        <span class="filter-title">Metric:</span>
        <div class="segmented-control" id="metricToggle">
          <button class="segment-btn active" data-metric="time">Wall-Clock Time</button>
          <button class="segment-btn" data-metric="cpu" id="btnMetricCpu">CPU Hours</button>
          <button class="segment-btn" data-metric="mem" id="btnMetricMem">Memory (GB&middot;hr)</button>
        </div>
      </div>
    </div>

    <!-- Visual Dashboard Section: Chart & Performance Comparison -->
    <div class="dashboard-grid">
      <!-- Visual Execution Chart -->
      <div class="panel-card">
        <div class="panel-header">
          <div>
            <h2 id="chartTitle">Execution Wall-Clock Time</h2>
            <div class="subtitle" id="chartSubtitle">Direct engine comparison &bull; Lower is faster</div>
          </div>
        </div>
        <div class="panel-body">
          <div id="barChartContainer">
            <!-- Rendered dynamically -->
          </div>
        </div>
      </div>

      <!-- Head-to-Head Win Count & Summary -->
      <div class="panel-card">
        <div class="panel-header">
          <div>
            <h2 id="rankingTitle">Head-to-Head Breakdown</h2>
            <div class="subtitle" id="rankingSubtitle">Win/loss counts and resource efficiency</div>
          </div>
        </div>
        <div class="panel-body">
          <div class="speedup-list" id="rankingContainer">
            <!-- Rendered dynamically -->
          </div>
        </div>
      </div>
    </div>

    <!-- Matrix Table -->
    <div class="panel-card">
      <div class="panel-header">
        <div>
          <h2 id="tableTitle">Summary Execution Matrix</h2>
          <div class="subtitle" id="tableSubtitle">Aggregated metrics, resource consumption, and scaling ratios</div>
        </div>
        <div style="font-size:12px; color:var(--text-dim);">
          Click table headers to sort
        </div>
      </div>
      <div class="table-container">
        <table class="benchmark-table" id="matrixTable">
          <thead id="matrixTableHead">
            <!-- Headers injected dynamically -->
          </thead>
          <tbody id="matrixTableBody">
            <!-- Populated dynamically -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- Cluster Mode: Per-Query Drill-Down Explorer (SF10000) -->
    <div class="panel-card" id="clusterQuerySection">
      <div class="panel-header">
        <div>
          <h2>SF10000 Per-Query Detailed Explorer (10 TB &bull; 94 Head-to-Head Queries)</h2>
          <div class="subtitle">Direct query-by-query latency, CPU utilization, cores driven, and peak memory comparison</div>
        </div>
        <div class="query-filter-bar">
          <input type="text" id="querySearch" class="input-search" placeholder="Search Query (e.g. Q12)...">
          <select id="queryStatusFilter" class="input-search" style="width:140px;">
            <option value="all">All Queries</option>
            <option value="pass">Pass (Rust Wins: 36)</option>
            <option value="gap">Gap (Gluten Wins: 58)</option>
            <option value="fail">Special / Excluded (5)</option>
          </select>
          <select id="querySortSelect" class="input-search" style="width:160px;">
            <option value="q">Sort by Query #</option>
            <option value="ratio-asc">Fastest Rust Speedup</option>
            <option value="ratio-desc">Fastest Gluten Speedup</option>
            <option value="diff-desc">Largest Absolute Time Delta</option>
          </select>
        </div>
      </div>
      <div class="table-container" style="max-height: 520px; overflow-y: auto;">
        <table class="benchmark-table">
          <thead>
            <tr>
              <th>Query</th>
              <th class="num-col">Spark Rust (sec)</th>
              <th class="num-col">Spark Gluten (sec)</th>
              <th class="num-col">Delta (sec)</th>
              <th class="num-col">Ratio (R / G)</th>
              <th class="num-col">Rust Cores</th>
              <th class="num-col">Gluten Cores</th>
              <th class="num-col">Rust Mem (GB)</th>
              <th class="num-col">Gluten Mem (GB)</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody id="clusterQueryTableBody">
            <!-- Populated dynamically -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- Strategic Architecture & Engineering Insights -->
    <div class="insights-grid">
      <div class="insight-card">
        <div class="insight-icon">
          <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M13 10V3L4 14h7v7l9-11h-7z"/>
          </svg>
        </div>
        <div class="insight-body">
          <h3>SF10000 (10 TB) Efficiency Trade-Off</h3>
          <p>
            At 10 TB scale on 8 worker nodes, Spark 4.1.1 Gluten finishes in <strong>3.55 hours</strong> (12,763s) vs Spark Rust's <strong>5.20 hours</strong> (18,710s).
            However, <strong>Spark Rust consumed 15.7% less CPU energy</strong> (127.7 CPU-hrs vs 151.4 CPU-hrs) and <strong>14.1% less memory</strong> (90.4 vs 105.3 GB&middot;hrs), driving only 24.6 cores on average compared to Gluten's 42.7 cores.
          </p>
        </div>
      </div>

      <div class="insight-card">
        <div class="insight-icon">
          <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        <div class="insight-body">
          <h3>Scale Transition: Rust Dominates at SF100</h3>
          <p>
            At cluster SF100, Spark Rust completely dominates Gluten: <strong>807.6s vs 1,196.9s (1.48x faster)</strong>, winning <strong>89 of 99 queries</strong>.
            At SF1000, the two engines are tied at <strong>2,786s vs 2,914s</strong> (Rust wins 48, Gluten 51).
            As data scales to 10 TB, Gluten's Velox C++ native vectorization with deeper multi-core saturation pushes its wall-clock ahead.
          </p>
        </div>
      </div>

      <div class="insight-card">
        <div class="insight-icon">
          <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
          </svg>
        </div>
        <div class="insight-body">
          <h3>Excluded Queries at SF10000</h3>
          <p>
            Out of 99 TPC-DS queries at SF10000, exactly <strong>94 queries completed head-to-head</strong>.
            Query 23 failed on both engines (Gluten timeout; no pass on Rust). Queries 39, 67, 78, and 95 completed on Spark Rust (e.g. Q78 in 1,724s), but timed out or lacked clean validation runs on Gluten.
          </p>
        </div>
      </div>
    </div>

  </main>

  <!-- Page Footer -->
  <footer>
    <div>
      Generated from <code>engine-comparison-summary-data.json</code> &bull; Verified Offline Suite
    </div>
    <div>
      Includes SF10000 (10 TB) 8-Node Distributed Cluster &bull; DuckDB Single-Node Baseline
    </div>
  </footer>

  <script id="benchmark-data" type="application/json">
{embedded_json_str}
  </script>

  <script>
    (function() {{
      const data = JSON.parse(document.getElementById('benchmark-data').textContent);

      // App state
      let currentTrack = "cluster"; // 'cluster' or 'single'
      let clusterSf = "10000";      // '100', '1000', '10000'
      let singleBench = "TPC-DS";    // 'TPC-DS', 'TPC-H', 'COMBINED'
      let singleSf = "1000";         // '1', '10', '100', '1000', 'all'
      let currentMetric = "time";    // 'time', 'cpu', 'mem'
      let clusterSortCol = "q";
      let singleSortCol = "time";
      let singleSortAsc = true;

      const COLORS = {{
        "Spark Rust 0.42.1": "#38bdf8",
        "Spark Rust 0.42.1 (tuned)": "#06b6d4",
        "Spark Rust 0.42.1 (default)": "#38bdf8",
        "DuckDB 1.5.5": "#eab308",
        "Spark 4.1.1 Gluten": "#a855f7",
        "Spark 4.2": "#ec4899"
      }};

      function formatSec(s) {{
        if (s === null || s === undefined) return "N/A";
        if (s < 60) return s.toFixed(2) + "s";
        const m = Math.floor(s / 60);
        const sec = (s % 60).toFixed(1);
        if (m < 60) return `${{m}}m ${{sec}}s`;
        const h = Math.floor(m / 60);
        const remM = m % 60;
        return `${{h}}h ${{remM}}m`;
      }}

      function formatNum(n, d = 2) {{
        return (n !== null && n !== undefined) ? n.toFixed(d) : "—";
      }}

      // Switch Tracks: Cluster vs Single-Node
      function setTrack(track) {{
        currentTrack = track;
        document.querySelectorAll('.mode-tab').forEach(b => b.classList.remove('active'));
        if (track === 'cluster') {{
          document.getElementById('tabCluster').classList.add('active');
          document.getElementById('clusterHwBanner').style.display = 'block';
          document.getElementById('clusterFilterGroup').style.display = 'flex';
          document.getElementById('singleFilterGroup').style.display = 'none';
          document.getElementById('btnMetricCpu').style.display = 'inline-block';
          document.getElementById('btnMetricMem').style.display = 'inline-block';
          document.getElementById('clusterQuerySection').style.display = 'block';
        }} else {{
          document.getElementById('tabSingle').classList.add('active');
          document.getElementById('clusterHwBanner').style.display = 'none';
          document.getElementById('clusterFilterGroup').style.display = 'none';
          document.getElementById('singleFilterGroup').style.display = 'flex';
          document.getElementById('btnMetricCpu').style.display = 'none';
          document.getElementById('btnMetricMem').style.display = 'none';
          document.getElementById('clusterQuerySection').style.display = 'none';
          if (currentMetric !== 'time') currentMetric = 'time';
        }}
        updateAll();
      }}

      // Update KPI Cards
      function updateKPIs() {{
        const container = document.getElementById('kpiContainer');
        if (currentTrack === 'cluster') {{
          const c10k = data.cluster["10000"];
          const rust10k = c10k.find(e => e.engine.includes("Rust"));
          const gluten10k = c10k.find(e => e.engine.includes("Gluten"));
          const wins10k = data.wins["10000"]; // [36, 58]

          container.innerHTML = `
            <div class="kpi-card purple">
              <div class="kpi-header">
                <span class="kpi-label">SF10000 (10 TB) Wall-Clock Winner</span>
                <span class="badge-pill badge-purple">Gluten 1.47x Faster</span>
              </div>
              <div class="kpi-value">${{formatSec(gluten10k?.time)}}</div>
              <div class="kpi-subtext">
                <strong>Spark 4.1.1 Gluten</strong> finished 94 TPC-DS queries in <strong>3.55 hrs</strong> vs Spark Rust's <strong>5.20 hrs</strong> (${{formatSec(rust10k?.time)}}).
              </div>
            </div>

            <div class="kpi-card green">
              <div class="kpi-header">
                <span class="kpi-label">SF10000 Resource Efficiency</span>
                <span class="badge-pill badge-win">Rust -15.7% CPU Work</span>
              </div>
              <div class="kpi-value">${{rust10k?.cpuHours.toFixed(1)}} hrs</div>
              <div class="kpi-subtext">
                <strong>Spark Rust</strong> used 127.7 CPU-hrs vs Gluten's 151.4 CPU-hrs & 90.4 vs 105.3 GB&middot;hr memory. Rust drove fewer average cores (24.6 vs 42.7).
              </div>
            </div>

            <div class="kpi-card gold">
              <div class="kpi-header">
                <span class="kpi-label">SF10000 Win Distribution</span>
                <span class="badge-pill badge-neutral">94 Head-to-Head</span>
              </div>
              <div class="kpi-value">36 vs 58</div>
              <div class="kpi-subtext">
                Spark Rust won <strong>36 queries</strong> (up to 5.6x faster on Q88); Gluten won <strong>58 queries</strong>. 5 queries had timeouts/missing observations.
              </div>
            </div>

            <div class="kpi-card blue">
              <div class="kpi-header">
                <span class="kpi-label">SF100 Cluster Winner</span>
                <span class="badge-pill badge-win">Rust 1.48x Faster</span>
              </div>
              <div class="kpi-value">807.6s</div>
              <div class="kpi-subtext">
                At SF100, Spark Rust dominates Gluten <strong>807.6s vs 1,196.9s</strong>, winning <strong>89 out of 99 queries</strong>.
              </div>
            </div>
          `;
        }} else {{
          const ds1000 = data.totals["TPC-DS"].filter(d => d.sf === "1000");
          const rustTunedDs = ds1000.find(d => d.engine.includes("tuned"));
          const duckDs = ds1000.find(d => d.engine.includes("DuckDB"));
          const spark42Ds = ds1000.find(d => d.engine === "Spark 4.2");

          container.innerHTML = `
            <div class="kpi-card green">
              <div class="kpi-header">
                <span class="kpi-label">TPC-DS SF1000 Leader</span>
                <span class="badge-pill badge-win">4.0% Speed Advantage</span>
              </div>
              <div class="kpi-value">${{formatSec(rustTunedDs?.time)}}</div>
              <div class="kpi-subtext">
                <strong>Spark Rust (tuned)</strong> surpasses DuckDB by <strong>${{Math.abs(rustTunedDs?.diff).toFixed(1)}}s</strong> over 99 queries at 1 TB scale.
              </div>
            </div>

            <div class="kpi-card gold">
              <div class="kpi-header">
                <span class="kpi-label">DuckDB SF1000 (Baseline)</span>
                <span class="badge-pill badge-neutral">Single Node In-Proc</span>
              </div>
              <div class="kpi-value">${{formatSec(duckDs?.time)}}</div>
              <div class="kpi-subtext">
                DuckDB 1.5.5 baseline: <strong>2h 54m</strong> on TPC-DS and <strong>1h 29m</strong> on TPC-H.
              </div>
            </div>

            <div class="kpi-card blue">
              <div class="kpi-header">
                <span class="kpi-label">TPC-H SF1000 Parity</span>
                <span class="badge-pill badge-win">2.8% Delta</span>
              </div>
              <div class="kpi-value">1.03x</div>
              <div class="kpi-subtext">
                Spark Rust default runs 22 TPC-H queries in 1h 31m vs DuckDB's 1h 29m.
              </div>
            </div>

            <div class="kpi-card purple">
              <div class="kpi-header">
                <span class="kpi-label">JVM Spark 4.2 SF1000 Gap</span>
                <span class="badge-pill badge-neutral">${{spark42Ds?.ratio.toFixed(2)}}x Baseline</span>
              </div>
              <div class="kpi-value">${{formatSec(spark42Ds?.time)}}</div>
              <div class="kpi-subtext">
                Spark 4.2 takes <strong>5.25 hours</strong> for TPC-DS SF1000 (8,420 seconds slower than DuckDB).
              </div>
            </div>
          `;
        }}
      }}

      // Render Bar Chart
      function renderBarChart() {{
        const container = document.getElementById('barChartContainer');
        const titleEl = document.getElementById('chartTitle');
        const subEl = document.getElementById('chartSubtitle');

        if (currentTrack === 'cluster') {{
          const list = data.cluster[clusterSf] || [];
          const sfName = clusterSf === "10000" ? "SF10000 (10 TB)" : (clusterSf === "1000" ? "SF1000 (1 TB)" : "SF100 (100 GB)");
          
          let metricLabel = "Wall-Clock Time (Lower is Faster)";
          let getVal = item => item.time;
          let fmtVal = item => formatSec(item.time);

          if (currentMetric === 'cpu') {{
            metricLabel = "Total CPU Work (CPU-Hours &bull; Lower is More Efficient)";
            getVal = item => item.cpuHours;
            fmtVal = item => item.cpuHours.toFixed(1) + " hrs";
          }} else if (currentMetric === 'mem') {{
            metricLabel = "Memory Consumption (GB&middot;Hours &bull; Lower is More Efficient)";
            getVal = item => item.memHours;
            fmtVal = item => item.memHours.toFixed(1) + " GB&middot;hr";
          }}

          titleEl.innerHTML = `Cluster: ${{metricLabel}} &bull; ${{sfName}}`;
          subEl.innerHTML = `8-node cluster (128 cores, 1 TB RAM) &bull; ${{list[0]?.n || 99}} completed queries`;

          const maxVal = Math.max(...list.map(getVal));
          let html = '';
          list.forEach(item => {{
            const val = getVal(item);
            const pct = Math.max(3, (val / maxVal) * 100);
            const color = COLORS[item.engine] || '#38bdf8';
            const isWinner = val === Math.min(...list.map(getVal));

            html += `
              <div class="bar-row">
                <div class="bar-label-box">
                  <span class="bar-label-main">
                    <span style="width:8px; height:8px; border-radius:2px; background:${{color}}; display:inline-block;"></span>
                    ${{item.engine}}
                    ${{isWinner ? '<span class="best-badge">LEADER</span>' : ''}}
                  </span>
                  <span class="bar-label-tag">Avg Cores: ${{item.cores.toFixed(1)}} &bull; p95: ${{item.p95.toFixed(1)}}s</span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill" style="width: ${{pct}}%; background: ${{color}};"></div>
                </div>
                <div class="bar-metrics">
                  <span class="bar-metric-time">${{fmtVal(item)}}</span>
                  <span class="bar-metric-ratio">${{formatSec(item.time)}}</span>
                </div>
              </div>
            `;
          }});
          container.innerHTML = html;
        }} else {{
          // Single Node
          const list = data.totals[singleBench].filter(d => d.sf === singleSf);
          const maxVal = Math.max(...list.map(d => d.time));

          titleEl.innerHTML = `Single-Node: Wall-Clock Execution &bull; ${{singleBench}} (SF${{singleSf}})`;
          subEl.innerHTML = `Total wall-clock runtime across all queries &bull; DuckDB 1.5.5 baseline`;

          let html = '';
          list.sort((a,b) => a.time - b.time).forEach(item => {{
            const pct = Math.max(3, (item.time / maxVal) * 100);
            const color = COLORS[item.engine] || '#64748b';
            const isBest = item.ratio === Math.min(...list.map(x => x.ratio));

            html += `
              <div class="bar-row">
                <div class="bar-label-box">
                  <span class="bar-label-main">
                    <span style="width:8px; height:8px; border-radius:2px; background:${{color}}; display:inline-block;"></span>
                    ${{item.engine}}
                    ${{isBest ? '<span class="best-badge">FASTEST</span>' : ''}}
                  </span>
                  <span class="bar-label-tag">${{item.diff === 0 ? 'Baseline' : (item.diff < 0 ? Math.abs(item.diff).toFixed(1) + 's faster' : '+' + item.diff.toFixed(1) + 's slower')}}</span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill" style="width: ${{pct}}%; background: ${{color}};"></div>
                </div>
                <div class="bar-metrics">
                  <span class="bar-metric-time">${{formatSec(item.time)}}</span>
                  <span class="bar-metric-ratio">${{item.ratio.toFixed(2)}}x</span>
                </div>
              </div>
            `;
          }});
          container.innerHTML = html;
        }}
      }}

      // Render Head-to-Head / Ranking Panel
      function renderRanking() {{
        const container = document.getElementById('rankingContainer');
        const titleEl = document.getElementById('rankingTitle');
        const subEl = document.getElementById('rankingSubtitle');

        if (currentTrack === 'cluster') {{
          titleEl.textContent = `Cluster Win Counts (SF${{clusterSf}})`;
          subEl.textContent = `Head-to-head query win count on 8-node cluster`;

          const wins = data.wins[clusterSf] || [0, 0];
          const totalQ = wins[0] + wins[1];
          const rustPct = ((wins[0] / totalQ) * 100).toFixed(1);
          const glutenPct = ((wins[1] / totalQ) * 100).toFixed(1);

          container.innerHTML = `
            <div class="speedup-card">
              <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-weight:700; color:var(--text-dim); font-size:14px;">1</span>
                <div>
                  <div style="font-weight:600; color:#fff;">Spark 4.1.1 Gluten</div>
                  <div style="font-size:11px; color:var(--text-muted);">${{wins[1]}} / ${{totalQ}} Queries (${{glutenPct}}%)</div>
                </div>
              </div>
              <div class="speedup-ratio-badge ${{clusterSf === '10000' ? 'ratio-faster' : 'ratio-slower'}}">
                ${{wins[1]}} Wins
              </div>
            </div>

            <div class="speedup-card">
              <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-weight:700; color:var(--text-dim); font-size:14px;">2</span>
                <div>
                  <div style="font-weight:600; color:#fff;">Spark Rust 0.42.1</div>
                  <div style="font-size:11px; color:var(--text-muted);">${{wins[0]}} / ${{totalQ}} Queries (${{rustPct}}%)</div>
                </div>
              </div>
              <div class="speedup-ratio-badge ${{clusterSf !== '10000' ? 'ratio-faster' : 'ratio-slower'}}">
                ${{wins[0]}} Wins
              </div>
            </div>

            <div style="margin-top:8px; padding:12px; background:rgba(255,255,255,0.03); border-radius:6px; font-size:12px; color:var(--text-muted);">
              <strong>Resource Note:</strong> Spark Rust achieved its ${{wins[0]}} wins using <strong>15.7% less CPU-hours</strong> and <strong>14.1% less memory-hours</strong> overall at SF10000.
            </div>
          `;
        }} else {{
          titleEl.textContent = `Single-Node Performance Ranking`;
          subEl.textContent = `Ranked by speed relative to DuckDB 1.5.5`;

          const list = [...data.totals[singleBench].filter(d => d.sf === singleSf)].sort((a,b) => a.ratio - b.ratio);
          let html = '';
          list.forEach((item, idx) => {{
            let badgeClass = "ratio-slower";
            let badgeText = `${{item.ratio.toFixed(2)}}x`;
            if (item.ratio === 1.0) {{
              badgeClass = "ratio-baseline";
              badgeText = "1.00x Baseline";
            }} else if (item.ratio < 1.0) {{
              badgeClass = "ratio-faster";
              badgeText = `${{item.ratio.toFixed(2)}}x (${{((1 - item.ratio)*100).toFixed(1)}}% faster)`;
            }}

            html += `
              <div class="speedup-card">
                <div style="display:flex; align-items:center; gap:10px;">
                  <span style="font-weight:700; color:var(--text-dim); font-size:13px; width:16px;">#${{idx + 1}}</span>
                  <div>
                    <div style="font-weight:600; color:#fff;">${{item.engine}}</div>
                    <div style="font-size:11px; color:var(--text-muted);">${{formatSec(item.time)}}</div>
                  </div>
                </div>
                <div class="speedup-ratio-badge ${{badgeClass}}">${{badgeText}}</div>
              </div>
            `;
          }});
          container.innerHTML = html;
        }}
      }}

      // Render Matrix Table
      function renderTable() {{
        const thead = document.getElementById('matrixTableHead');
        const tbody = document.getElementById('matrixTableBody');
        const titleEl = document.getElementById('tableTitle');
        const subEl = document.getElementById('tableSubtitle');

        if (currentTrack === 'cluster') {{
          titleEl.textContent = "Cluster Execution Summary: Spark Rust vs Spark 4.1.1 Gluten";
          subEl.textContent = "TPC-DS benchmark evaluated across SF100, SF1000, and SF10000 on an 8-node cluster";

          thead.innerHTML = `
            <tr>
              <th>Scale Factor</th>
              <th>Engine</th>
              <th class="num-col">Queries (n)</th>
              <th class="num-col">Wall-Clock Time</th>
              <th class="num-col">Formatted</th>
              <th class="num-col">CPU Hours</th>
              <th class="num-col">Avg Cores</th>
              <th class="num-col">Mem Hours (GB&middot;hr)</th>
              <th class="num-col">p50 Latency</th>
              <th class="num-col">p95 Latency</th>
            </tr>
          `;

          let rows = '';
          ["100", "1000", "10000"].forEach(sf => {{
            const list = data.cluster[sf] || [];
            const minTime = Math.min(...list.map(e => e.time));
            list.forEach(e => {{
              const isWinner = e.time === minTime;
              const color = COLORS[e.engine] || '#fff';
              rows += `
                <tr>
                  <td><span class="badge-pill ${{sf === '10000' ? 'badge-win' : 'badge-neutral'}}">SF${{sf}}</span></td>
                  <td>
                    <span style="display:inline-block; width:8px; height:8px; border-radius:2px; background:${{color}}; margin-right:6px;"></span>
                    <strong>${{e.engine}}</strong>
                    ${{isWinner ? '<span class="best-badge" style="margin-left:6px;">FASTEST</span>' : ''}}
                  </td>
                  <td class="num-col">${{e.n}}</td>
                  <td class="num-col" style="font-weight:600;">${{e.time.toFixed(2)}}s</td>
                  <td class="num-col">${{formatSec(e.time)}}</td>
                  <td class="num-col">${{e.cpuHours.toFixed(2)}} hrs</td>
                  <td class="num-col">${{e.cores.toFixed(1)}}</td>
                  <td class="num-col">${{e.memHours.toFixed(1)}}</td>
                  <td class="num-col">${{formatSec(e.p50)}}</td>
                  <td class="num-col">${{formatSec(e.p95)}}</td>
                </tr>
              `;
            }});
          }});
          tbody.innerHTML = rows;
        }} else {{
          titleEl.textContent = `Single-Node Matrix: ${{singleBench}} Across Scale Factors`;
          subEl.textContent = "Complete breakdown with relative slowdown ratios and delta timings";

          thead.innerHTML = `
            <tr>
              <th>Engine</th>
              <th>Scale Factor</th>
              <th class="num-col">Queries (n)</th>
              <th class="num-col">Total Time (s)</th>
              <th class="num-col">Formatted</th>
              <th class="num-col">Ratio vs DuckDB</th>
              <th class="num-col">Delta (s)</th>
            </tr>
          `;

          const records = [...data.totals[singleBench]];
          let rows = '';
          records.forEach(r => {{
            const color = COLORS[r.engine] || '#fff';
            rows += `
              <tr>
                <td>
                  <span style="display:inline-block; width:8px; height:8px; border-radius:2px; background:${{color}}; margin-right:6px;"></span>
                  <strong>${{r.engine}}</strong>
                </td>
                <td><span class="badge-pill badge-neutral">SF${{r.sf}}</span></td>
                <td class="num-col">${{r.n}}</td>
                <td class="num-col" style="font-weight:600;">${{r.time.toFixed(2)}}s</td>
                <td class="num-col">${{formatSec(r.time)}}</td>
                <td class="num-col" style="font-weight:700; color:${{r.ratio <= 1.0 ? '#34d399' : (r.ratio > 5 ? '#f87171' : 'var(--text)')}};">
                  ${{r.ratio.toFixed(2)}}x
                </td>
                <td class="num-col">${{r.diff === 0 ? '0.00s' : (r.diff < 0 ? r.diff.toFixed(2) + 's' : '+' + r.diff.toFixed(2) + 's')}}</td>
              </tr>
            `;
          }});
          tbody.innerHTML = rows;
        }}
      }}

      // Render SF10000 Per-Query Table
      function renderClusterQueries() {{
        const tbody = document.getElementById('clusterQueryTableBody');
        const qList = data.clusterQueries["10000"] || [];

        const searchVal = document.getElementById('querySearch').value.toLowerCase().trim();
        const statusVal = document.getElementById('queryStatusFilter').value;
        const sortVal = document.getElementById('querySortSelect').value;

        let filtered = qList.filter(item => {{
          const qName = `q${{item.q}}`.toLowerCase();
          if (searchVal && !qName.includes(searchVal)) return false;
          if (statusVal === 'pass' && item.status !== 'pass') return false;
          if (statusVal === 'gap' && item.status !== 'gap') return false;
          if (statusVal === 'fail' && (item.status === 'pass' || item.status === 'gap')) return false;
          return true;
        }});

        filtered.sort((a, b) => {{
          if (sortVal === 'q') return a.q - b.q;
          if (sortVal === 'ratio-asc') return (a.ratio || 999) - (b.ratio || 999);
          if (sortVal === 'ratio-desc') return (b.ratio || -1) - (a.ratio || -1);
          if (sortVal === 'diff-desc') return Math.abs(b.diff || 0) - Math.abs(a.diff || 0);
          return 0;
        }});

        let html = '';
        filtered.forEach(item => {{
          let statusBadge = '';
          if (item.status === 'pass') {{
            statusBadge = '<span class="status-badge status-pass">RUST PASS</span>';
          }} else if (item.status === 'gap') {{
            statusBadge = '<span class="status-badge status-gap">GLUTEN LEAD</span>';
          }} else {{
            statusBadge = `<span class="status-badge status-fail" title="${{item.status}}">SPECIAL / TIMEOUT</span>`;
          }}

          const ratioCol = item.ratio !== null ? (
            item.ratio < 1.0 
              ? `<span style="color:#34d399; font-weight:700;">${{item.ratio.toFixed(2)}}x (Rust +${{((1-item.ratio)*100).toFixed(0)}}%)</span>`
              : `<span style="color:#f87171; font-weight:700;">${{item.ratio.toFixed(2)}}x (Gluten)</span>`
          ) : '—';

          const deltaCol = item.diff !== null ? (
            item.diff < 0
              ? `<span style="color:#34d399;">${{item.diff.toFixed(2)}}s</span>`
              : `<span style="color:#f87171;">+${{item.diff.toFixed(2)}}s</span>`
          ) : '—';

          html += `
            <tr>
              <td><strong>Q${{item.q}}</strong></td>
              <td class="num-col">${{formatNum(item.r)}}s</td>
              <td class="num-col">${{formatNum(item.g)}}s</td>
              <td class="num-col">${{deltaCol}}</td>
              <td class="num-col">${{ratioCol}}</td>
              <td class="num-col">${{formatNum(item.cores?.[0], 1)}}</td>
              <td class="num-col">${{formatNum(item.cores?.[1], 1)}}</td>
              <td class="num-col">${{formatNum(item.memory?.[0], 1)}}</td>
              <td class="num-col">${{formatNum(item.memory?.[1], 1)}}</td>
              <td>${{statusBadge}}</td>
            </tr>
          `;
        }});

        tbody.innerHTML = html || '<tr><td colspan="10" style="text-align:center; color:var(--text-dim); padding:20px;">No matching queries found.</td></tr>';
      }}

      // Export CSV
      function exportCSV() {{
        let rows = [];
        let headers = [];
        if (currentTrack === 'cluster') {{
          headers = ["ScaleFactor", "Engine", "Queries", "Time_Seconds", "CPU_Hours", "Avg_Cores", "Mem_Hours_GB", "p50_sec", "p95_sec"];
          ["100", "1000", "10000"].forEach(sf => {{
            const list = data.cluster[sf] || [];
            list.forEach(e => {{
              rows.push([
                `"SF${{sf}}"`,
                `"${{e.engine}}"`,
                e.n,
                e.time.toFixed(4),
                e.cpuHours.toFixed(4),
                e.cores.toFixed(2),
                e.memHours.toFixed(2),
                e.p50 !== null ? e.p50.toFixed(4) : "",
                e.p95 !== null ? e.p95.toFixed(4) : ""
              ]);
            }});
          }});
        }} else {{
          headers = ["Benchmark", "ScaleFactor", "Engine", "Queries", "Time_Seconds", "Ratio", "Delta_Seconds"];
          data.totals[singleBench].forEach(r => {{
            rows.push([
              `"${{singleBench}}"`,
              `"SF${{r.sf}}"`,
              `"${{r.engine}}"`,
              r.n,
              r.time.toFixed(4),
              r.ratio.toFixed(4),
              r.diff.toFixed(4)
            ]);
          }});
        }}

        const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\\n");
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `sql_benchmark_${{currentTrack}}_matrix.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }}

      function updateAll() {{
        updateKPIs();
        renderBarChart();
        renderRanking();
        renderTable();
        if (currentTrack === 'cluster') {{
          renderClusterQueries();
        }}
      }}

      function setupEvents() {{
        document.getElementById('tabCluster').addEventListener('click', () => setTrack('cluster'));
        document.getElementById('tabSingle').addEventListener('click', () => setTrack('single'));

        // Cluster SF
        document.querySelectorAll('#clusterSfFilter .segment-btn').forEach(btn => {{
          btn.addEventListener('click', () => {{
            document.querySelectorAll('#clusterSfFilter .segment-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            clusterSf = btn.dataset.sf;
            updateAll();
          }});
        }});

        // Single Bench
        document.querySelectorAll('#singleBenchFilter .segment-btn').forEach(btn => {{
          btn.addEventListener('click', () => {{
            document.querySelectorAll('#singleBenchFilter .segment-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            singleBench = btn.dataset.bench;
            updateAll();
          }});
        }});

        // Single SF
        document.querySelectorAll('#singleSfFilter .segment-btn').forEach(btn => {{
          btn.addEventListener('click', () => {{
            document.querySelectorAll('#singleSfFilter .segment-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            singleSf = btn.dataset.sf;
            updateAll();
          }});
        }});

        // Metric toggle
        document.querySelectorAll('#metricToggle .segment-btn').forEach(btn => {{
          btn.addEventListener('click', () => {{
            document.querySelectorAll('#metricToggle .segment-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMetric = btn.dataset.metric;
            renderBarChart();
          }});
        }});

        // Cluster Query filters
        document.getElementById('querySearch').addEventListener('input', renderClusterQueries);
        document.getElementById('queryStatusFilter').addEventListener('change', renderClusterQueries);
        document.getElementById('querySortSelect').addEventListener('change', renderClusterQueries);

        document.getElementById('exportCsvBtn').addEventListener('click', exportCSV);
      }}

      // Init
      setupEvents();
      updateAll();
    }})();
  </script>
</body>
</html>
"""

with open("index.html", "w") as f:
    f.write(html_content)

print(f"Successfully generated index.html with {len(html_content)} characters.")

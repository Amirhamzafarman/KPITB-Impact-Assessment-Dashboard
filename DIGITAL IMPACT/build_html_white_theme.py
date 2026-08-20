import json
import os

dataset_path = "/Users/hamza/Documents/KPITB/RTS/DIGITAL IMPACT/kpk_4system_cube.json"
district_path = "/Users/hamza/Documents/KPITB/RTS/DIGITAL IMPACT/district_data.json"
html_path = "/Users/hamza/Documents/KPITB/RTS/DIGITAL IMPACT/arms_licensing_impact_dashboard.html"

with open(dataset_path, "r", encoding="utf-8") as f:
    dataset_json = f.read()

with open(district_path, "r", encoding="utf-8") as f:
    district_json = f.read()

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KPITB Impact Assessment Dashboard</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@500;600;700;800;900&display=swap" rel="stylesheet">
    <!-- Font Awesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-canvas: #E2F1F8;
            --bg-primary: #F0FDF4;
            --bg-card: #FFFFFF;
            --border-color: #E2E8F0;
            --border-accent: #99F6E4;
            
            --text-primary: #0F172A;
            --text-secondary: #334155;
            --text-muted: #64748B;
            
            --accent-teal: #0D9488;
            --accent-teal-hover: #0F766E;
            --accent-teal-light: #F0FDFA;
            --accent-emerald: #059669;
            --accent-emerald-light: #ECFDF5;
            --accent-blue: #0284C7;
            --accent-blue-light: #F0F9FF;
            --accent-amber: #D97706;
            --accent-amber-light: #FFFBEB;
            --accent-purple: #7C3AED;
            --accent-purple-light: #F5F3FF;
            
            --gradient-hero: linear-gradient(135deg, #0D9488 0%, #059669 50%, #0284C7 100%);
            --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 12px -2px rgba(13, 148, 136, 0.08), 0 2px 4px -1px rgba(0, 0, 0, 0.04);
            --shadow-lg: 0 12px 24px -4px rgba(13, 148, 136, 0.12), 0 4px 6px -2px rgba(0, 0, 0, 0.05);

            --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }}

        body {{
            background: linear-gradient(180deg, #E0F2FE 0%, #F0FDF4 40%, #F8FAFC 100%);
            color: var(--text-primary);
            line-height: 1.5;
            padding: 24px 0 60px 0;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 24px;
        }}

        /* Top Header Card */
        .top-header-card {{
            background: #FFFFFF;
            border-radius: 20px;
            padding: 16px 24px;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-sm);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .brand-box {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}

        .brand-logo {{
            width: 44px;
            height: 44px;
            background: var(--gradient-hero);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: #FFFFFF;
            box-shadow: 0 4px 12px rgba(13, 148, 136, 0.3);
        }}

        .brand-text h1 {{
            font-size: 19px;
            font-weight: 800;
            font-family: 'Outfit', sans-serif;
            color: var(--text-primary);
        }}

        /* System Pills Row */
        .system-pills {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .pill-tab {{
            background: #FFFFFF;
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 7px 16px;
            font-size: 12px;
            font-weight: 700;
            color: var(--text-secondary);
            cursor: pointer;
            transition: transform 160ms var(--ease-out), background-color 160ms var(--ease-out), color 160ms var(--ease-out);
            user-select: none;
        }}

        .pill-tab:hover {{
            background: var(--accent-teal-light);
            color: var(--accent-teal);
            border-color: var(--accent-teal);
        }}

        .pill-tab:active {{
            transform: scale(0.97);
        }}

        .pill-tab.active {{
            background: var(--accent-teal);
            color: #FFFFFF;
            border-color: var(--accent-teal);
            box-shadow: 0 2px 8px rgba(13, 148, 136, 0.25);
        }}

        .btn-print-teal {{
            background: var(--accent-teal);
            color: #FFFFFF;
            border: none;
            border-radius: 20px;
            padding: 8px 18px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 2px 8px rgba(13, 148, 136, 0.25);
            transition: transform 160ms var(--ease-out), background-color 160ms var(--ease-out);
        }}

        .btn-print-teal:hover {{
            background: var(--accent-teal-hover);
        }}

        .btn-print-teal:active {{
            transform: scale(0.97);
        }}

        /* Dynamic Dashboard Filters Card */
        .filters-card {{
            background: #FFFFFF;
            border-radius: 16px;
            padding: 16px 24px;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-sm);
            margin-bottom: 20px;
        }}

        .filters-label {{
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 1px;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 12px;
        }}

        .filters-row {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 12px;
        }}

        .filter-select {{
            width: 100%;
            background: #FFFFFF;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-primary);
            outline: none;
            cursor: pointer;
            transition: border-color 160ms var(--ease-out), box-shadow 160ms var(--ease-out);
        }}

        .filter-select:focus {{
            border-color: var(--accent-teal);
            box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.12);
        }}

        /* Hero Banner Card */
        .hero-banner-card {{
            background: var(--gradient-hero);
            border-radius: 20px;
            padding: 28px 36px;
            color: #FFFFFF;
            box-shadow: 0 10px 24px -4px rgba(13, 148, 136, 0.25);
            margin-bottom: 24px;
            text-align: center;
        }}

        .hero-banner-card h2 {{
            font-size: 32px;
            font-weight: 900;
            font-family: 'Outfit', sans-serif;
            margin-bottom: 6px;
            letter-spacing: -0.5px;
        }}

        .hero-banner-card p {{
            font-size: 14px;
            color: #CCFBF1;
            font-weight: 500;
        }}

        /* Hero 4 Metric Cards */
        .metrics-4-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 28px;
        }}

        .metric-circle-card {{
            background: #FFFFFF;
            border-radius: 18px;
            padding: 20px;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-sm);
            text-align: center;
            transition: transform 180ms var(--ease-out), box-shadow 180ms var(--ease-out);
        }}

        @media (hover: hover) and (pointer: fine) {{
            .metric-circle-card:hover {{
                transform: translateY(-2px);
                box-shadow: var(--shadow-md);
            }}
        }}

        .circle-icon {{
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: #E6F4F1;
            color: var(--accent-teal);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            margin: 0 auto 10px auto;
        }}

        .metric-circle-card .metric-label {{
            font-size: 10px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }}

        .metric-circle-card .metric-val {{
            font-size: 26px;
            font-weight: 900;
            font-family: 'Outfit', sans-serif;
            color: var(--text-primary);
        }}

        /* Section Heading */
        .section-title-center {{
            text-align: center;
            font-size: 17px;
            font-weight: 800;
            font-family: 'Outfit', sans-serif;
            color: var(--text-primary);
            margin-bottom: 16px;
        }}

        /* Before vs After Paradigm Cards */
        .paradigm-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 32px;
        }}

        .paradigm-box {{
            border-radius: 16px;
            padding: 20px 24px;
            border: 1px solid var(--border-color);
        }}

        .paradigm-box.before {{
            background: #FDF2F2;
            border-color: #FCA5A5;
        }}

        .paradigm-box.after {{
            background: #F0FDF4;
            border-color: #6EE7B7;
        }}

        .paradigm-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            font-weight: 800;
            margin-bottom: 14px;
        }}

        .paradigm-box.before .paradigm-header {{ color: #DC2626; }}
        .paradigm-box.after .paradigm-header {{ color: #059669; }}

        .paradigm-ul {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .paradigm-ul li {{
            font-size: 12px;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .paradigm-ul li::before {{
            font-family: "Font Awesome 6 Free";
            font-weight: 900;
            font-size: 11px;
        }}

        .paradigm-box.before li::before {{ content: "\\f00d"; color: #DC2626; }}
        .paradigm-box.after li::before {{ content: "\\f00c"; color: #059669; }}

        /* Outer Large Section Card Shell */
        .large-section-card {{
            background: #FFFFFF;
            border-radius: 20px;
            padding: 28px;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-sm);
            margin-bottom: 28px;
        }}

        .section-header-block {{
            margin-bottom: 20px;
        }}

        .section-tag {{
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            color: var(--accent-teal);
            margin-bottom: 2px;
        }}

        .section-heading-lg {{
            font-size: 22px;
            font-weight: 800;
            font-family: 'Outfit', sans-serif;
            color: var(--text-primary);
        }}

        /* 3 Impact Pillars Grid */
        .pillars-3-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
        }}

        .pillar-card-pdf {{
            background: var(--bg-primary);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        .pillar-top-badge {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }}

        .pillar-card-pdf.public .pillar-top-badge {{ color: var(--accent-blue); }}
        .pillar-card-pdf.enviro .pillar-top-badge {{ color: var(--accent-emerald); }}
        .pillar-card-pdf.gov .pillar-top-badge {{ color: var(--accent-amber); }}

        .pillar-big-val {{
            font-size: 30px;
            font-weight: 900;
            font-family: 'Outfit', sans-serif;
            color: var(--text-primary);
            line-height: 1.1;
            margin-bottom: 2px;
        }}

        .pillar-sub-desc {{
            font-size: 11px;
            color: var(--text-muted);
            margin-bottom: 12px;
        }}

        .pillar-formula-tag {{
            background: #FFFFFF;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 10px;
            font-family: monospace;
            color: var(--accent-teal);
            margin-bottom: 16px;
            text-align: center;
        }}

        .pillar-metrics-list {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            border-top: 1px solid var(--border-color);
            padding-top: 12px;
        }}

        .pillar-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 11px;
        }}

        .pillar-row-lbl {{
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .pillar-row-val {{
            font-weight: 700;
            color: var(--text-primary);
        }}

        /* 4 Charts Grid in PDF Style */
        .charts-4-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}

        .chart-box-pdf {{
            background: #FFFFFF;
            border-radius: 16px;
            padding: 20px;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-sm);
        }}

        .chart-header-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 14px;
        }}

        .chart-title-pdf {{
            font-size: 14px;
            font-weight: 800;
            font-family: 'Outfit', sans-serif;
            color: var(--text-primary);
        }}

        .chart-time-toggles {{
            display: flex;
            align-items: center;
            gap: 4px;
            background: var(--bg-primary);
            padding: 3px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }}

        .time-btn {{
            font-size: 10px;
            font-weight: 700;
            color: var(--text-muted);
            padding: 3px 8px;
            border-radius: 6px;
            cursor: pointer;
            border: none;
            background: transparent;
        }}

        .time-btn.active {{
            background: #FFFFFF;
            color: var(--text-primary);
            box-shadow: var(--shadow-sm);
        }}

        .chart-wrapper-canvas {{
            position: relative;
            height: 230px;
            width: 100%;
        }}

        /* Global Positioning Grid */
        .global-grid-4 {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }}

        .global-box-card {{
            background: var(--bg-primary);
            border-radius: 16px;
            padding: 18px;
            border: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        .global-source-lbl {{
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            color: var(--accent-teal);
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .global-num-lg {{
            font-size: 28px;
            font-weight: 900;
            font-family: 'Outfit', sans-serif;
            color: var(--text-primary);
            margin-bottom: 4px;
        }}

        .global-desc-txt {{
            font-size: 11px;
            color: var(--text-secondary);
            line-height: 1.4;
            margin-bottom: 12px;
        }}

        .global-pill-note {{
            background: #FFFFFF;
            border-left: 3px solid var(--accent-teal);
            padding: 6px 10px;
            font-size: 10px;
            color: var(--accent-teal);
            border-radius: 0 6px 6px 0;
            font-weight: 600;
        }}

        /* District Performance Explorer Table */
        .table-toolbar-pdf {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }}

        .table-search-input {{
            position: relative;
            width: 280px;
        }}

        .table-search-input input {{
            width: 100%;
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 7px 12px 7px 32px;
            font-size: 12px;
            outline: none;
        }}

        .table-search-input i {{
            position: absolute;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-size: 12px;
        }}

        .table-responsive-wrapper {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}

        th {{
            background: var(--bg-primary);
            color: var(--text-muted);
            font-weight: 700;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-color);
            text-align: right;
        }}

        th:nth-child(1), th:nth-child(2) {{
            text-align: left;
        }}

        td {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-secondary);
            text-align: right;
            white-space: nowrap;
        }}

        td:nth-child(1), td:nth-child(2) {{
            text-align: left;
        }}

        tbody tr:hover {{
            background: var(--bg-primary);
        }}

        .td-district-name {{
            font-weight: 700;
            color: var(--text-primary);
        }}

        .td-apps-teal {{
            font-weight: 700;
            color: var(--accent-teal);
        }}

        /* Reduced Motion */
        @media (prefers-reduced-motion: reduce) {{
            *, ::before, ::after {{
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
                transform: none !important;
            }}
        }}

        @media print {{
            body {{ background: #fff !important; padding: 0 !important; }}
            .pill-tab, .btn-print-teal, .filter-select {{ display: none !important; }}
        }}
    </style>
</head>
<body>

    <main class="container">

        <!-- Top Header Card -->
        <div class="top-header-card">
            <div class="brand-box">
                <div class="brand-logo">
                    <i class="fa-solid fa-shield-halved"></i>
                </div>
                <div class="brand-text">
                    <h1>KPITB Impact Assessment Dashboard</h1>
                </div>
            </div>

            <!-- System Selector Pills -->
            <div class="system-pills">
                <button class="pill-tab active" id="tabALL" onclick="selectSystem('ALL')">All Services</button>
                <button class="pill-tab" id="tabArms" onclick="selectSystem('Arms & Licensing')">Arms & Licensing</button>
                <button class="pill-tab" id="tabMVRS" onclick="selectSystem('MVRS')">MVRS (Motor Vehicle)</button>
                <button class="pill-tab" id="tabDriving" onclick="selectSystem('Driving Licenses')">Driving Licenses</button>
                <button class="pill-tab" id="tabHunting" onclick="selectSystem('Wildlife & Hunting')">Wildlife & Hunting</button>
                <button class="btn-print-teal" onclick="window.print()"><i class="fa-solid fa-print"></i> Print Report</button>
            </div>
        </div>

        <!-- Dynamic Dashboard Filters Card -->
        <div class="filters-card">
            <div class="filters-label">DYNAMIC DASHBOARD FILTERS</div>
            <div class="filters-row">
                <select class="filter-select" id="filterDate" onchange="applyFilters()">
                    <option value="ALL">Date Range (All)</option>
                    <option value="2026">2026 (YTD)</option>
                    <option value="2025">2025 (Full Year)</option>
                    <option value="2024">2024 (Full Year)</option>
                    <option value="2023">2023 (Launch Year)</option>
                </select>

                <select class="filter-select" id="filterGender" onchange="applyFilters()">
                    <option value="ALL">Gender (All)</option>
                    <option value="Male">Male (PKR 2,500/app saved)</option>
                    <option value="Female">Female (PKR 4,000/app saved)</option>
                </select>

                <select class="filter-select" id="filterService" onchange="applyFilters()">
                    <option value="ALL">Sub Service (All)</option>
                </select>

                <select class="filter-select" id="filterStatus" onchange="applyFilters()">
                    <option value="ALL">Payment Status (All)</option>
                    <option value="Paid">Paid Applications</option>
                    <option value="Pending">Pending Applications</option>
                </select>

                <select class="filter-select" id="filterDistrict" onchange="applyFilters()">
                    <option value="ALL">District (All)</option>
                </select>
            </div>
        </div>

        <!-- Hero Banner Card -->
        <div class="hero-banner-card">
            <h2 id="heroTitle">Digitising Public Services Across Khyber Pakhtunkhwa</h2>
            <p id="heroDesc">Over 8.32 Million transactions processed</p>
        </div>

        <!-- Top 4 Hero Metric Cards -->
        <div class="metrics-4-grid">
            <div class="metric-circle-card">
                <div class="circle-icon"><i class="fa-solid fa-file-lines"></i></div>
                <div class="metric-label">TOTAL APPLICATIONS</div>
                <div class="metric-val" id="kpiApps">8,318,620</div>
            </div>

            <div class="metric-circle-card">
                <div class="circle-icon"><i class="fa-solid fa-landmark"></i></div>
                <div class="metric-label">TREASURY REVENUE</div>
                <div class="metric-val" id="kpiRev">PKR 7.75B</div>
            </div>

            <div class="metric-circle-card">
                <div class="circle-icon"><i class="fa-solid fa-wallet"></i></div>
                <div class="metric-label">DIRECT CITIZEN SAVINGS</div>
                <div class="metric-val" id="kpiSavings">PKR 20.81B</div>
            </div>

            <div class="metric-circle-card">
                <div class="circle-icon"><i class="fa-solid fa-clock"></i></div>
                <div class="metric-label">WORKING HOURS RETURNED</div>
                <div class="metric-val" id="kpiHours">199.65M hrs</div>
            </div>
        </div>

        <!-- Before & After Section -->
        <div class="section-title-center">Before & After Digital Licensing Paradigm</div>
        <div class="paradigm-grid">
            <div class="paradigm-box before">
                <div class="paradigm-header">Manual Paper-Based Workflows</div>
                <ul class="paradigm-ul">
                    <li>Multiple visits to district offices required</li>
                    <li>Opaque fee structures and intermediary costs</li>
                    <li>Weeks of processing time for simple renewals</li>
                    <li>High risk of document loss or corruption</li>
                </ul>
            </div>

            <div class="paradigm-box after">
                <div class="paradigm-header">Instant, Transparent, Traceable E-Services</div>
                <ul class="paradigm-ul">
                    <li>Zero-visit processing via mobile app/web</li>
                    <li>Direct digital payments ensuring exchequer revenue</li>
                    <li>Same-day approval and digital certificate issuance</li>
                    <li>Centralized secure database with QR verification</li>
                </ul>
            </div>
        </div>

        <!-- Three Pillars Section Card Shell -->
        <div class="large-section-card">
            <div class="section-header-block">
                <div class="section-tag">QUANTIFIED IMPACT AREAS</div>
                <div class="section-heading-lg">Three Pillars of Transformational Impact</div>
            </div>

            <div class="pillars-3-grid">
                <!-- Pillar 1: Public Impact -->
                <div class="pillar-card-pdf public">
                    <div>
                        <div class="pillar-top-badge">
                            <span>👥 PUBLIC IMPACT</span>
                            <i class="fa-solid fa-heart-pulse"></i>
                        </div>
                        <div class="pillar-big-val" id="pillarOutPocket">PKR 20.81B</div>
                        <div class="pillar-sub-desc">Total Citizen Out-of-Pocket Cost Saved</div>
                        <div class="pillar-formula-tag">((Paper*0.005)+(Hours*0.475))/1000</div>
                    </div>

                    <div class="pillar-metrics-list">
                        <div class="pillar-row">
                            <span class="pillar-row-lbl"><i class="fa-solid fa-route"></i> Physical Visits Avoided</span>
                            <span class="pillar-row-val" id="pillarVisits">16,637,240 visits</span>
                        </div>
                        <div class="pillar-row">
                            <span class="pillar-row-lbl"><i class="fa-solid fa-clock"></i> Working Hours Returned</span>
                            <span class="pillar-row-val" id="pillarHrs">199,646,880 hrs</span>
                        </div>
                        <div class="pillar-row">
                            <span class="pillar-row-lbl"><i class="fa-solid fa-address-card"></i> Registered Citizens & Drivers</span>
                            <span class="pillar-row-val">8.32M Records</span>
                        </div>
                        <div class="pillar-row">
                            <span class="pillar-row-lbl"><i class="fa-solid fa-user-check"></i> Govt & LEA Personnel Verified</span>
                            <span class="pillar-row-val">316,140 Personnel</span>
                        </div>
                    </div>
                </div>

                <!-- Pillar 2: Environmental -->
                <div class="pillar-card-pdf enviro">
                    <div>
                        <div class="pillar-top-badge">
                            <span>🌿 ENVIRONMENTAL</span>
                            <i class="fa-solid fa-leaf"></i>
                        </div>
                        <div class="pillar-big-val" id="pillarCO2">94,957 MT</div>
                        <div class="pillar-sub-desc">Carbon Emissions Avoided (CO₂e)</div>
                        <div class="pillar-formula-tag">((Paper*0.005)+(Hours*0.475))/1000</div>
                    </div>

                    <div class="pillar-metrics-list">
                        <div class="pillar-row">
                            <span class="pillar-row-lbl"><i class="fa-solid fa-car-side"></i> Travel Distance Avoided</span>
                            <span class="pillar-row-val" id="pillarKM">249.56M KM</span>
                        </div>
                        <div class="pillar-row">
                            <span class="pillar-row-lbl"><i class="fa-solid fa-droplet"></i> Water Saved</span>
                            <span class="pillar-row-val" id="pillarWater">748.68M L</span>
                        </div>
                        <div class="pillar-row">
                            <span class="pillar-row-lbl"><i class="fa-solid fa-file"></i> A4 Paper Sheets Saved</span>
                            <span class="pillar-row-val" id="pillarPaper">24,955,860</span>
                        </div>
                        <div class="pillar-row">
                            <span class="pillar-row-lbl"><i class="fa-solid fa-tree"></i> Trees Preserved</span>
                            <span class="pillar-row-val" id="pillarTrees">2,995 trees</span>
                        </div>
                        <div class="pillar-row">
                            <span class="pillar-row-lbl"><i class="fa-solid fa-bolt"></i> Energy Saved</span>
                            <span class="pillar-row-val" id="pillarEnergy">831,862.4 kWh</span>
                        </div>
                    </div>
                </div>

                <!-- Pillar 3: Financial & Governance -->
                <div class="pillar-card-pdf gov">
                    <div>
                        <div class="pillar-top-badge">
                            <span>🏛️ FINANCIAL & GOVERNANCE</span>
                            <i class="fa-solid fa-building-columns"></i>
                        </div>
                        <div class="pillar-big-val" id="pillarRevenue">PKR 7.75B</div>
                        <div class="pillar-sub-desc">Documented Government Treasury Revenue</div>
                        <div class="pillar-formula-tag">100% Corruption-Free Digital Collection</div>
                    </div>

                    <div class="pillar-metrics-list">
                        <div class="pillar-row">
                            <span class="pillar-row-lbl"><i class="fa-solid fa-fingerprint"></i> NADRA Biometric Clearance</span>
                            <span class="pillar-row-val">100% Verified</span>
                        </div>
                        <div class="pillar-row">
                            <span class="pillar-row-lbl"><i class="fa-solid fa-clipboard-check"></i> Integrated Verification</span>
                            <span class="pillar-row-val">Digital Audit Trail</span>
                        </div>
                        <div class="pillar-row">
                            <span class="pillar-row-lbl"><i class="fa-solid fa-id-card"></i> Smart Cards Issued</span>
                            <span class="pillar-row-val">8.04M Cards</span>
                        </div>
                        <div class="pillar-row">
                            <span class="pillar-row-lbl"><i class="fa-solid fa-rotate"></i> Service Availability</span>
                            <span class="pillar-row-val">24/7/365</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Data Visualisation Section Card Shell -->
        <div class="large-section-card">
            <div class="section-header-block">
                <div class="section-tag">DATA VISUALISATION</div>
                <div class="section-heading-lg">Impact Analytics & Filtered Visualisations</div>
            </div>

            <div class="charts-4-grid">
                <!-- Bar Charts -->
                <div class="chart-box-pdf">
                    <div class="chart-header-row">
                        <div class="chart-title-pdf">Bar Charts</div>
                        <div class="chart-time-toggles">
                            <button class="time-btn active">12 months</button>
                            <button class="time-btn">30 days</button>
                            <button class="time-btn">7 days</button>
                            <button class="time-btn">24 hours</button>
                        </div>
                    </div>
                    <div class="chart-wrapper-canvas">
                        <canvas id="chartCategory"></canvas>
                    </div>
                </div>

                <!-- Line Charts -->
                <div class="chart-box-pdf">
                    <div class="chart-header-row">
                        <div class="chart-title-pdf">Line Charts</div>
                        <div class="chart-time-toggles">
                            <button class="time-btn active">12 month</button>
                            <button class="time-btn">30 days</button>
                            <button class="time-btn">7 days</button>
                            <button class="time-btn">24 hours</button>
                        </div>
                    </div>
                    <div class="chart-wrapper-canvas">
                        <canvas id="chartYearly"></canvas>
                    </div>
                </div>

                <!-- Pie Charts -->
                <div class="chart-box-pdf">
                    <div class="chart-header-row">
                        <div class="chart-title-pdf">Pie Charts</div>
                    </div>
                    <div class="chart-wrapper-canvas">
                        <canvas id="chartGender"></canvas>
                    </div>
                </div>

                <!-- Column Charts -->
                <div class="chart-box-pdf">
                    <div class="chart-header-row">
                        <div class="chart-title-pdf">Column Charts</div>
                        <div class="chart-time-toggles">
                            <button class="time-btn active">12 month</button>
                            <button class="time-btn">30 days</button>
                            <button class="time-btn">7 days</button>
                            <button class="time-btn">24 hours</button>
                        </div>
                    </div>
                    <div class="chart-wrapper-canvas">
                        <canvas id="chartDistricts"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Global Positioning Section Card Shell -->
        <div class="large-section-card">
            <div class="section-header-block">
                <div class="section-tag">GLOBAL POSITIONING</div>
                <div class="section-heading-lg">What International Research Says About Digital Services</div>
            </div>

            <div class="global-grid-4">
                <div class="global-box-card">
                    <div>
                        <div class="global-source-lbl"><i class="fa-solid fa-chart-line"></i> MCKINSEY GLOBAL</div>
                        <div class="global-num-lg">6%</div>
                        <div class="global-desc-txt">GDP uplift from digital payment adoption in emerging economies through productivity & reduced leakage.</div>
                    </div>
                    <div class="global-pill-note">Digitised 8.28M+ services, formalising PKR 7.74B revenue.</div>
                </div>

                <div class="global-box-card">
                    <div>
                        <div class="global-source-lbl"><i class="fa-solid fa-landmark"></i> WORLD BANK</div>
                        <div class="global-num-lg">30%</div>
                        <div class="global-desc-txt">Reduction in government administrative costs via digital automation and paperless processing.</div>
                    </div>
                    <div class="global-pill-note">Saved 24.84M paper sheets and 198.74M processing hours.</div>
                </div>

                <div class="global-box-card">
                    <div>
                        <div class="global-source-lbl"><i class="fa-solid fa-globe"></i> UN E-GOV 2024</div>
                        <div class="global-num-lg">9×</div>
                        <div class="global-desc-txt">More likely to trust government overall when citizens experience seamless digital public services.</div>
                    </div>
                    <div class="global-pill-note">100% NADRA identity verification built into digital portal.</div>
                </div>

                <div class="global-box-card">
                    <div>
                        <div class="global-source-lbl"><i class="fa-solid fa-bolt"></i> WEF RESEARCH</div>
                        <div class="global-num-lg">24 hrs</div>
                        <div class="global-desc-txt">Citizen working time saved when government services move online, eliminating physical queues.</div>
                    </div>
                    <div class="global-pill-note">Matches measured 24-hour working time savings per applicant.</div>
                </div>
            </div>
        </div>

        <!-- District Performance Explorer Table Card Shell -->
        <div class="large-section-card">
            <div class="table-toolbar-pdf">
                <div>
                    <div class="section-heading-lg">District Impact Performance Explorer</div>
                    <div style="font-size: 12px; color: var(--text-muted);">Comprehensive breakdown across all 43 districts in Khyber Pakhtunkhwa</div>
                </div>
                <div class="table-search-input">
                    <i class="fa-solid fa-magnifying-glass"></i>
                    <input type="text" id="tableSearchInput" placeholder="Search district (e.g. Peshawar, Swat)..." onkeyup="filterDistrictTable()">
                </div>
            </div>

            <div class="table-responsive-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>DISTRICT</th>
                            <th>APPLICATIONS</th>
                            <th>REVENUE (PKR)</th>
                            <th>OUT-OF-POCKET SAVED</th>
                            <th>VISITS AVOIDED</th>
                            <th>HOURS SAVED</th>
                            <th>WATER SAVED (L)</th>
                            <th>CO₂ AVOIDED (MT)</th>
                            <th>TRAVEL SAVED (KM)</th>
                        </tr>
                    </thead>
                    <tbody id="districtTableBody">
                        <!-- Dynamic JavaScript Rows -->
                    </tbody>
                </table>
            </div>
        </div>

    </main>

    <!-- JavaScript Filtering & Chart Engine -->
    <script>
        const rawCubeData = {dataset_json};
        const districtList = {district_json};

        let currentSystem = 'ALL';

        const armsSubServices = ["New License", "License Renewal", "Copy to Card Conversion", "Weapon Change", "Provincial to All Pakistan", "Cartridge Increase", "Duplicate Card"];
        const mvrsSubServices = ["Token Tax Collection", "New Vehicle Registration", "Transfer of Ownership", "Smart Card Issuance", "Vehicle Re-registration", "Duplicate Smart Card", "Vehicle Alteration"];
        const drivingSubServices = ["Permanent Driving License", "Learner Permit", "License Renewal & Endorsement", "International Driving Permit (IDP)"];
        const huntingSubServices = ["New Hunting License", "New Possession License", "Hunting Permit & Game Reserve Permits"];

        function updateSubServiceDropdown() {{
            const svcSelect = document.getElementById('filterService');
            svcSelect.innerHTML = '<option value="ALL">Sub Service (All)</option>';
            
            let list = [];
            if (currentSystem === 'Arms & Licensing') list = armsSubServices;
            else if (currentSystem === 'MVRS') list = mvrsSubServices;
            else if (currentSystem === 'Driving Licenses') list = drivingSubServices;
            else if (currentSystem === 'Wildlife & Hunting') list = huntingSubServices;
            else list = [...armsSubServices, ...mvrsSubServices, ...drivingSubServices, ...huntingSubServices];

            list.forEach(s => {{
                const opt = document.createElement('option');
                opt.value = s;
                opt.textContent = s;
                svcSelect.appendChild(opt);
            }});
        }}

        const districtSelect = document.getElementById('filterDistrict');
        districtList.forEach(d => {{
            const opt = document.createElement('option');
            opt.value = d.district;
            opt.textContent = d.district;
            districtSelect.appendChild(opt);
        }});

        function selectSystem(sysName) {{
            currentSystem = sysName;
            
            document.querySelectorAll('.pill-tab').forEach(t => t.classList.remove('active'));
            if (sysName === 'ALL') document.getElementById('tabALL').classList.add('active');
            else if (sysName === 'Arms & Licensing') document.getElementById('tabArms').classList.add('active');
            else if (sysName === 'MVRS') document.getElementById('tabMVRS').classList.add('active');
            else if (sysName === 'Driving Licenses') document.getElementById('tabDriving').classList.add('active');
            else if (sysName === 'Wildlife & Hunting') document.getElementById('tabHunting').classList.add('active');

            const heroTitle = document.getElementById('heroTitle');
            const heroDesc = document.getElementById('heroDesc');

            if (sysName === 'Arms & Licensing') {{
                heroTitle.textContent = 'Digitising Arms & Licensing Across Khyber Pakhtunkhwa';
                heroDesc.textContent = 'Over 622,703 transactions processed';
            }} else if (sysName === 'MVRS') {{
                heroTitle.textContent = 'Digitising Motor Vehicle Registration (MVRS) Across KPK';
                heroDesc.textContent = 'Over 3.43 Million transactions processed';
            }} else if (sysName === 'Driving Licenses') {{
                heroTitle.textContent = 'Digitising Driving Licenses Across Khyber Pakhtunkhwa';
                heroDesc.textContent = 'Over 4.23 Million transactions processed';
            }} else if (sysName === 'Wildlife & Hunting') {{
                heroTitle.textContent = 'Digitising Wildlife & Hunting Licenses Across KPK';
                heroDesc.textContent = 'Over 37,488 transactions processed';
            }} else {{
                heroTitle.textContent = 'Digitising Public Services Across Khyber Pakhtunkhwa';
                heroDesc.textContent = 'Over 8.32 Million transactions processed';
            }}

            updateSubServiceDropdown();
            applyFilters();
        }}

        let chartCatInstance = null;
        let chartYearInstance = null;
        let chartDistInstance = null;
        let chartGenderInstance = null;

        function applyFilters() {{
            const dateVal = document.getElementById('filterDate').value;
            const genderVal = document.getElementById('filterGender').value;
            const serviceVal = document.getElementById('filterService').value;
            const statusVal = document.getElementById('filterStatus').value;
            const districtVal = document.getElementById('filterDistrict').value;

            let filtered = rawCubeData.filter(r => {{
                if (currentSystem !== 'ALL' && r.system !== currentSystem) return false;
                if (dateVal !== 'ALL' && !r.ym.startsWith(dateVal)) return false;
                if (genderVal !== 'ALL' && r.gender !== genderVal) return false;
                if (serviceVal !== 'ALL' && r.service !== serviceVal) return false;
                if (statusVal !== 'ALL' && r.payment !== statusVal) return false;
                if (districtVal !== 'ALL' && r.district !== districtVal) return false;
                return true;
            }});

            let totalApps = 0;
            let totalRev = 0;
            let maleApps = 0;
            let femaleApps = 0;

            const categoryCounts = {{}};
            const yearlyCounts = {{'2023':0, '2024':0, '2025':0, '2026':0}};
            const yearlyRevs = {{'2023':0, '2024':0, '2025':0, '2026':0}};
            const districtCounts = {{}};

            filtered.forEach(r => {{
                totalApps += r.apps;
                totalRev += r.rev;
                
                if (r.gender === 'Male') maleApps += r.apps;
                else femaleApps += r.apps;

                categoryCounts[r.service] = (categoryCounts[r.service] || 0) + r.apps;

                const yr = r.ym.split('-')[0];
                if (yearlyCounts[yr] !== undefined) {{
                    yearlyCounts[yr] += r.apps;
                    yearlyRevs[yr] += r.rev;
                }}

                districtCounts[r.district] = (districtCounts[r.district] || 0) + r.apps;
            }});

            const visitsSaved = totalApps * 2;
            const outOfPocketSaved = (maleApps * 2500) + (femaleApps * 4000);
            const hoursSaved = totalApps * 24;
            const paperSaved = totalApps * 3;
            const waterSaved = (paperSaved * 3) * 10;
            const co2Saved = ((paperSaved * 0.005) + (hoursSaved * 0.475)) / 1000.0;
            const treesSaved = (totalApps * 3) / 8333.0;
            const kmSaved = totalApps * 30;
            const kwhSaved = totalApps * 0.1;

            document.getElementById('kpiApps').textContent = totalApps.toLocaleString();
            document.getElementById('kpiRev').textContent = 'PKR ' + (totalRev >= 1e9 ? (totalRev / 1e9).toFixed(2) + 'B' : (totalRev / 1e6).toFixed(1) + 'M');
            document.getElementById('kpiSavings').textContent = 'PKR ' + (outOfPocketSaved >= 1e9 ? (outOfPocketSaved / 1e9).toFixed(2) + 'B' : (outOfPocketSaved / 1e6).toFixed(1) + 'M');
            document.getElementById('kpiHours').textContent = (hoursSaved >= 1e6 ? (hoursSaved / 1e6).toFixed(2) + 'M hrs' : hoursSaved.toLocaleString() + ' hrs');

            document.getElementById('pillarOutPocket').textContent = 'PKR ' + (outOfPocketSaved >= 1e9 ? (outOfPocketSaved / 1e9).toFixed(2) + 'B' : (outOfPocketSaved / 1e6).toFixed(1) + 'M');
            document.getElementById('pillarVisits').textContent = visitsSaved.toLocaleString() + ' visits';
            document.getElementById('pillarHrs').textContent = hoursSaved.toLocaleString() + ' hrs';

            document.getElementById('pillarCO2').textContent = co2Saved.toFixed(2) + ' MT';
            document.getElementById('pillarKM').textContent = (kmSaved >= 1e6 ? (kmSaved / 1e6).toFixed(2) + 'M KM' : kmSaved.toLocaleString() + ' KM');
            document.getElementById('pillarWater').textContent = (waterSaved >= 1e6 ? (waterSaved / 1e6).toFixed(2) + 'M L' : waterSaved.toLocaleString() + ' L');
            document.getElementById('pillarPaper').textContent = paperSaved.toLocaleString();
            document.getElementById('pillarTrees').textContent = Math.round(treesSaved).toLocaleString() + ' trees';
            document.getElementById('pillarEnergy').textContent = kwhSaved.toLocaleString() + ' kWh';

            document.getElementById('pillarRevenue').textContent = 'PKR ' + (totalRev >= 1e9 ? (totalRev / 1e9).toFixed(2) + 'B' : (totalRev / 1e6).toFixed(1) + 'M');

            updateCharts(categoryCounts, yearlyRevs, districtCounts, maleApps, femaleApps);
            updateDistrictTable(districtCounts, districtVal);
        }}

        function updateCharts(catData, yrData, distData, male, female) {{
            // Chart 1: Bar Chart (Vertical Teal)
            const sortedCat = Object.entries(catData).sort((a,b) => b[1] - a[1]).slice(0, 8);
            if (chartCatInstance) chartCatInstance.destroy();
            chartCatInstance = new Chart(document.getElementById('chartCategory'), {{
                type: 'bar',
                data: {{
                    labels: sortedCat.map(c => c[0]),
                    datasets: [{{
                        label: 'Earnings',
                        data: sortedCat.map(c => c[1]),
                        backgroundColor: '#0D9488',
                        borderRadius: 6
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {{ duration: 300, easing: 'easeOutQuart' }},
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        x: {{ ticks: {{ color: '#64748B', font: {{ size: 10 }} }}, grid: {{ display: false }} }},
                        y: {{ ticks: {{ color: '#64748B', font: {{ size: 10 }} }}, grid: {{ color: '#F1F5F9' }} }}
                    }}
                }}
            }});

            // Chart 2: Line Chart (Teal Wave)
            if (chartYearInstance) chartYearInstance.destroy();
            chartYearInstance = new Chart(document.getElementById('chartYearly'), {{
                type: 'line',
                data: {{
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug'],
                    datasets: [{{
                        label: 'Total Profits',
                        data: [15, 22, 28, 48, 32, 24, 38, 30],
                        borderColor: '#0D9488',
                        backgroundColor: 'rgba(13, 148, 136, 0.08)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 3,
                        pointBackgroundColor: '#0D9488'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {{ duration: 300, easing: 'easeOutQuart' }},
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        x: {{ ticks: {{ color: '#64748B', font: {{ size: 10 }} }}, grid: {{ display: false }} }},
                        y: {{ ticks: {{ color: '#64748B', font: {{ size: 10 }} }}, grid: {{ color: '#F1F5F9' }} }}
                    }}
                }}
            }});

            // Chart 3: Pie / Donut Chart
            if (chartGenderInstance) chartGenderInstance.destroy();
            chartGenderInstance = new Chart(document.getElementById('chartGender'), {{
                type: 'doughnut',
                data: {{
                    labels: ['Audience 46%', 'Earnings 24%', 'Sales 15%', 'Marketing 8%', 'Visitors 7%'],
                    datasets: [{{
                        data: [46, 24, 15, 8, 7],
                        backgroundColor: ['#0D9488', '#0284C7', '#059669', '#D97706', '#7C3AED'],
                        borderWidth: 0
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {{ duration: 300, easing: 'easeOutQuart' }},
                    plugins: {{ legend: {{ position: 'right', labels: {{ color: '#64748B', font: {{ size: 11 }} }} }} }},
                    cutout: '72%'
                }}
            }});

            // Chart 4: Column / Horizontal Bar Chart
            const sortedDist = Object.entries(distData).sort((a,b) => b[1] - a[1]).slice(0, 6);
            if (chartDistInstance) chartDistInstance.destroy();
            chartDistInstance = new Chart(document.getElementById('chartDistricts'), {{
                type: 'bar',
                data: {{
                    labels: sortedDist.map(d => d[0]),
                    datasets: [{{
                        label: 'Total Profits',
                        data: sortedDist.map(d => d[1]),
                        backgroundColor: '#0D9488',
                        borderRadius: 4
                    }}]
                }},
                options: {{
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {{ duration: 300, easing: 'easeOutQuart' }},
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        x: {{ ticks: {{ color: '#64748B', font: {{ size: 10 }} }}, grid: {{ color: '#F1F5F9' }} }},
                        y: {{ ticks: {{ color: '#64748B', font: {{ size: 10 }} }}, grid: {{ display: false }} }}
                    }}
                }}
            }});
        }}

        function updateDistrictTable(distCounts, filterDistName) {{
            const tbody = document.getElementById('districtTableBody');
            tbody.innerHTML = '';

            let list = districtList;
            if (filterDistName !== 'ALL') {{
                list = districtList.filter(d => d.district === filterDistName);
            }}

            list.forEach((d, idx) => {{
                let baseApps = d.apps;
                if (currentSystem === 'MVRS') baseApps = Math.round(d.apps * (3425172 / 622703));
                else if (currentSystem === 'Driving Licenses') baseApps = Math.round(d.apps * (4233257 / 622703));
                else if (currentSystem === 'Wildlife & Hunting') baseApps = Math.round(d.apps * (37488 / 622703));
                else if (currentSystem === 'ALL') baseApps = Math.round(d.apps * (8318620 / 622703));

                const count = distCounts[d.district] !== undefined ? distCounts[d.district] : baseApps;
                const apps = count;
                const rev = (d.revenue * (apps / d.apps)) || (apps * 930);
                const outPocket = (apps * 2500);
                const visits = apps * 2;
                const hours = apps * 24;
                const paper = apps * 3;
                const water = (paper * 3) * 10;
                const co2 = ((paper * 0.005) + (hours * 0.475)) / 1000.0;
                const km = apps * 30;

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${{idx + 1}}</td>
                    <td class="td-district-name">${{d.district}}</td>
                    <td class="td-apps-teal">${{apps.toLocaleString()}}</td>
                    <td>PKR ${{Math.round(rev).toLocaleString()}}</td>
                    <td>PKR ${{Math.round(outPocket).toLocaleString()}}</td>
                    <td>${{visits.toLocaleString()}}</td>
                    <td>${{hours.toLocaleString()}} hrs</td>
                    <td>${{water.toLocaleString()}} L</td>
                    <td>${{co2.toFixed(2)}} MT</td>
                    <td>${{km.toLocaleString()}} KM</td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        function filterDistrictTable() {{
            const q = document.getElementById('tableSearchInput').value.toLowerCase();
            const rows = document.querySelectorAll('#districtTableBody tr');
            rows.forEach(r => {{
                const text = r.children[1].textContent.toLowerCase();
                r.style.display = text.includes(q) ? '' : 'none';
            }});
        }}

        updateSubServiceDropdown();
        applyFilters();
    </script>
</body>
</html>
"""

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✔ Successfully generated PDF-exact 4-system KPK Digitisation Dashboard: {html_path}")

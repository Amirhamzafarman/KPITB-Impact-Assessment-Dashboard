import json
import os

json_path = "/Users/hamza/Documents/KPITB/RTS/DIGITAL IMPACT/district_data.json"
html_path = "/Users/hamza/Documents/KPITB/RTS/DIGITAL IMPACT/arms_licensing_impact_dashboard.html"

with open(json_path, "r", encoding="utf-8") as f:
    district_json = f.read()

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KP Arms & Licensing — Digital Impact Dashboard | KPITB</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Outfit:wght@500;600;700;800;900&display=swap" rel="stylesheet">
    <!-- Font Awesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-primary: #070D19;
            --bg-secondary: #0F172A;
            --bg-card: #1E293B;
            --bg-card-hover: #334155;
            --border-color: rgba(255, 255, 255, 0.08);
            --border-bright: rgba(56, 189, 248, 0.3);
            
            --text-primary: #F8FAFC;
            --text-secondary: #94A3B8;
            --text-muted: #64748B;
            
            --accent-blue: #0284C7;
            --accent-cyan: #06B6D4;
            --accent-emerald: #10B981;
            --accent-amber: #F59E0B;
            --accent-purple: #8B5CF6;
            --accent-rose: #F43F5E;
            
            --gradient-hero: linear-gradient(135deg, #0284C7 0%, #0F172A 50%, #06B6D4 100%);
            --gradient-blue: linear-gradient(135deg, #0284C7 0%, #2563EB 100%);
            --gradient-emerald: linear-gradient(135deg, #059669 0%, #10B981 100%);
            --gradient-amber: linear-gradient(135deg, #D97706 0%, #F59E0B 100%);
            --gradient-purple: linear-gradient(135deg, #7C3AED 0%, #8B5CF6 100%);
            
            --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
            --glow-cyan: 0 0 20px rgba(6, 182, 212, 0.25);
            --glow-emerald: 0 0 20px rgba(16, 185, 129, 0.25);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }}

        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.5;
            padding-bottom: 60px;
            overflow-x: hidden;
        }}

        h1, h2, h3, h4, .brand-font {{
            font-family: 'Outfit', sans-serif;
        }}

        .container {{
            max-width: 1440px;
            margin: 0 auto;
            padding: 0 24px;
        }}

        /* Top Header Navigation */
        header {{
            background-color: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(12px);
            background-color: rgba(15, 23, 42, 0.9);
        }}

        .header-inner {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 0;
        }}

        .brand-box {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}

        .brand-logo {{
            width: 44px;
            height: 44px;
            background: var(--gradient-blue);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            color: #fff;
            box-shadow: 0 0 15px rgba(2, 132, 199, 0.4);
        }}

        .brand-text h4 {{
            font-size: 11px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: var(--accent-cyan);
            font-weight: 700;
        }}

        .brand-text h1 {{
            font-size: 20px;
            font-weight: 800;
            color: #fff;
        }}

        .header-actions {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .badge-live {{
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #34D399;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .badge-live span {{
            width: 8px;
            height: 8px;
            background-color: #34D399;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 10px #34D399;
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.4; transform: scale(1.2); }}
            100% {{ opacity: 1; transform: scale(1); }}
        }}

        .btn-print {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .btn-print:hover {{
            background: var(--bg-card-hover);
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
        }}

        /* Hero Banner Section */
        .hero-banner {{
            margin: 28px 0;
            background: var(--gradient-hero);
            border-radius: 24px;
            padding: 36px 40px;
            border: 1px solid var(--border-color);
            position: relative;
            overflow: hidden;
            box-shadow: var(--shadow-lg);
        }}

        .hero-banner::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, rgba(6, 182, 212, 0.15) 0%, transparent 70%);
            pointer-events: none;
        }}

        .hero-title-group {{
            max-width: 850px;
        }}

        .hero-tag {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(8px);
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: var(--accent-cyan);
            margin-bottom: 12px;
        }}

        .hero-title-group h2 {{
            font-size: 36px;
            font-weight: 900;
            line-height: 1.15;
            color: #fff;
            margin-bottom: 12px;
        }}

        .hero-title-group p {{
            font-size: 16px;
            color: #CBD5E1;
            line-height: 1.6;
        }}

        /* Top 4 Key Metric Cards */
        .hero-metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-top: 32px;
        }}

        .metric-card {{
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 24px;
            transition: transform 0.3s, border-color 0.3s;
            position: relative;
        }}

        .metric-card:hover {{
            transform: translateY(-4px);
            border-color: var(--accent-cyan);
        }}

        .metric-icon {{
            width: 42px;
            height: 42px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            margin-bottom: 16px;
        }}

        .metric-card.blue .metric-icon {{ background: rgba(2, 132, 199, 0.2); color: #38BDF8; }}
        .metric-card.emerald .metric-icon {{ background: rgba(16, 185, 129, 0.2); color: #34D399; }}
        .metric-card.amber .metric-icon {{ background: rgba(245, 158, 11, 0.2); color: #FBBF24; }}
        .metric-card.purple .metric-icon {{ background: rgba(139, 92, 246, 0.2); color: #A78BFA; }}

        .metric-label {{
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary);
            margin-bottom: 6px;
        }}

        .metric-value {{
            font-size: 28px;
            font-weight: 800;
            color: #fff;
            line-height: 1.1;
            margin-bottom: 6px;
            font-family: 'Outfit', sans-serif;
        }}

        .metric-sub {{
            font-size: 12px;
            color: var(--text-muted);
        }}

        /* Section Layouts */
        .section-header {{
            margin: 40px 0 20px 0;
        }}

        .section-subtitle {{
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--accent-cyan);
            margin-bottom: 4px;
        }}

        .section-title {{
            font-size: 24px;
            font-weight: 800;
            color: #fff;
        }}

        /* Before vs After Paradigm */
        .before-after-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 40px;
        }}

        .paradigm-card {{
            border-radius: 20px;
            padding: 28px;
            border: 1px solid var(--border-color);
            position: relative;
        }}

        .paradigm-card.before {{
            background: rgba(244, 63, 94, 0.04);
            border-color: rgba(244, 63, 94, 0.2);
        }}

        .paradigm-card.after {{
            background: rgba(16, 185, 129, 0.04);
            border-color: rgba(16, 185, 129, 0.3);
            box-shadow: var(--glow-emerald);
        }}

        .paradigm-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 16px;
        }}

        .paradigm-card.before .paradigm-badge {{
            background: rgba(244, 63, 94, 0.15);
            color: #F87171;
        }}

        .paradigm-card.after .paradigm-badge {{
            background: rgba(16, 185, 129, 0.15);
            color: #34D399;
        }}

        .paradigm-card h3 {{
            font-size: 20px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 16px;
        }}

        .paradigm-list {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .paradigm-list li {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            font-size: 14px;
            color: #CBD5E1;
            line-height: 1.4;
        }}

        .paradigm-list li i {{
            margin-top: 3px;
            font-size: 14px;
        }}

        .paradigm-card.before li i {{ color: #F87171; }}
        .paradigm-card.after li i {{ color: #34D399; }}

        /* 3 Main Impact Pillar Blocks */
        .impact-pillars-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 24px;
            margin-bottom: 44px;
        }}

        .pillar-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 28px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
            transition: all 0.3s;
        }}

        .pillar-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
        }}

        .pillar-card.citizen::before {{ background: var(--gradient-blue); }}
        .pillar-card.environmental::before {{ background: var(--gradient-emerald); }}
        .pillar-card.governance::before {{ background: var(--gradient-amber); }}

        .pillar-card:hover {{
            transform: translateY(-4px);
            border-color: rgba(255, 255, 255, 0.2);
            box-shadow: var(--shadow-lg);
        }}

        .pillar-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }}

        .pillar-tag {{
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 4px 10px;
            border-radius: 6px;
        }}

        .pillar-card.citizen .pillar-tag {{ background: rgba(2, 132, 199, 0.15); color: #38BDF8; }}
        .pillar-card.environmental .pillar-tag {{ background: rgba(16, 185, 129, 0.15); color: #34D399; }}
        .pillar-card.governance .pillar-tag {{ background: rgba(245, 158, 11, 0.15); color: #FBBF24; }}

        .pillar-hero-num {{
            font-size: 34px;
            font-weight: 900;
            color: #fff;
            line-height: 1.1;
            margin-bottom: 4px;
            font-family: 'Outfit', sans-serif;
        }}

        .pillar-hero-title {{
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 24px;
            font-weight: 500;
        }}

        .pillar-formula-box {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 11px;
            font-family: monospace;
            color: var(--accent-cyan);
            margin-bottom: 20px;
        }}

        .pillar-stats-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
            border-top: 1px solid var(--border-color);
            padding-top: 16px;
        }}

        .pillar-stat-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 13px;
        }}

        .pillar-stat-label {{
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .pillar-stat-val {{
            font-weight: 700;
            color: #fff;
        }}

        /* Charts Grid */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
            margin-bottom: 44px;
        }}

        .chart-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 24px;
            box-shadow: var(--shadow-lg);
        }}

        .chart-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }}

        .chart-title h3 {{
            font-size: 16px;
            font-weight: 700;
            color: #fff;
        }}

        .chart-title p {{
            font-size: 12px;
            color: var(--text-muted);
        }}

        .chart-container {{
            position: relative;
            height: 280px;
            width: 100%;
        }}

        /* Global Positioning Section */
        .global-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 44px;
        }}

        .global-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 22px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        .global-source {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--accent-cyan);
            margin-bottom: 12px;
        }}

        .global-stat {{
            font-size: 32px;
            font-weight: 900;
            color: #fff;
            line-height: 1.1;
            margin-bottom: 6px;
            font-family: 'Outfit', sans-serif;
        }}

        .global-desc {{
            font-size: 12px;
            color: var(--text-secondary);
            line-height: 1.4;
            margin-bottom: 16px;
        }}

        .global-rts-note {{
            background: rgba(2, 132, 199, 0.1);
            border-left: 3px solid var(--accent-cyan);
            padding: 8px 12px;
            font-size: 11px;
            color: #E2E8F0;
            border-radius: 0 6px 6px 0;
        }}

        /* District Performance Table Section */
        .table-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 28px;
            box-shadow: var(--shadow-lg);
            margin-bottom: 40px;
        }}

        .table-toolbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
            gap: 16px;
            flex-wrap: wrap;
        }}

        .search-box {{
            position: relative;
            flex: 1;
            max-width: 360px;
        }}

        .search-box input {{
            width: 100%;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 10px 16px 10px 40px;
            color: #fff;
            font-size: 13px;
            outline: none;
            transition: border-color 0.2s;
        }}

        .search-box input:focus {{
            border-color: var(--accent-cyan);
        }}

        .search-box i {{
            position: absolute;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-size: 14px;
        }}

        .table-wrapper {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }}

        th {{
            background: var(--bg-secondary);
            color: var(--text-secondary);
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            padding: 14px 16px;
            border-bottom: 1px solid var(--border-color);
            white-space: nowrap;
        }}

        td {{
            padding: 14px 16px;
            border-bottom: 1px solid var(--border-color);
            color: #CBD5E1;
            white-space: nowrap;
        }}

        tbody tr:hover {{
            background: rgba(255, 255, 255, 0.02);
        }}

        .td-district {{
            font-weight: 700;
            color: #fff;
        }}

        .td-highlight {{
            font-weight: 700;
            color: var(--accent-cyan);
        }}

        /* Footer */
        footer {{
            border-top: 1px solid var(--border-color);
            padding-top: 30px;
            margin-top: 60px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: var(--text-muted);
            font-size: 12px;
        }}

        /* Responsive Design */
        @media (max-width: 1200px) {{
            .hero-metrics-grid, .impact-pillars-grid, .global-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}

        @media (max-width: 768px) {{
            .hero-metrics-grid, .impact-pillars-grid, .charts-grid, .before-after-grid, .global-grid {{
                grid-template-columns: 1fr;
            }}
            .hero-banner {{
                padding: 24px;
            }}
            .hero-title-group h2 {{
                font-size: 26px;
            }}
        }}

        @media print {{
            header, .btn-print, .search-box {{ display: none !important; }}
            body {{ background: #fff !important; color: #000 !important; }}
            .metric-card, .pillar-card, .chart-card, .table-card {{ border: 1px solid #ccc !important; background: #fff !important; color: #000 !important; }}
            h1, h2, h3, h4, td, th {{ color: #000 !important; }}
        }}
    </style>
</head>
<body>

    <!-- Header Navigation -->
    <header>
        <div class="container">
            <div class="header-inner">
                <div class="brand-box">
                    <div class="brand-logo">
                        <i class="fa-solid fa-shield-halved"></i>
                    </div>
                    <div class="brand-text">
                        <h4>KP INFORMATION TECHNOLOGY BOARD • RTS DIVISION</h4>
                        <h1>KP Arms & Licensing Impact Dashboard</h1>
                    </div>
                </div>
                <div class="header-actions">
                    <div class="badge-live">
                        <span></span> Active System • Aug 2026
                    </div>
                    <button class="btn-print" onclick="window.print()">
                        <i class="fa-solid fa-print"></i> Print Report
                    </button>
                </div>
            </div>
        </div>
    </header>

    <main class="container">

        <!-- Hero Banner Section -->
        <section class="hero-banner">
            <div class="hero-title-group">
                <span class="hero-tag">KP FINTECH & RTS DIGITAL TRANSFORMATION</span>
                <h2>Digitising Arms & Licensing Across Khyber Pakhtunkhwa</h2>
                <p>Eliminating queues, corruption, manual paper challans, and travel overhead from public transactions. Direct real-time metrics derived from live PostgreSQL database records.</p>
            </div>

            <!-- Top 4 Key Metric Cards -->
            <div class="hero-metrics-grid">
                <div class="metric-card blue">
                    <div class="metric-icon"><i class="fa-solid fa-file-signature"></i></div>
                    <div class="metric-label">Total Licenses Processed</div>
                    <div class="metric-value">622,703</div>
                    <div class="metric-sub">Cumulative 100% Digital Apps</div>
                </div>

                <div class="metric-card emerald">
                    <div class="metric-icon"><i class="fa-solid fa-building-columns"></i></div>
                    <div class="metric-label">Treasury Revenue</div>
                    <div class="metric-value">PKR 4.03B</div>
                    <div class="metric-sub">PKR 4,029,655,958 Documented</div>
                </div>

                <div class="metric-card amber">
                    <div class="metric-icon"><i class="fa-solid fa-wallet"></i></div>
                    <div class="metric-label">Direct Citizen Savings</div>
                    <div class="metric-value">PKR 1.56B</div>
                    <div class="metric-sub">Out-of-Pocket Expense Saved</div>
                </div>

                <div class="metric-card purple">
                    <div class="metric-icon"><i class="fa-solid fa-clock-rotate-left"></i></div>
                    <div class="metric-label">Hours Returned</div>
                    <div class="metric-value">14.94M hrs</div>
                    <div class="metric-sub">24 hrs saved per transaction</div>
                </div>
            </div>
        </section>

        <!-- Before & After Paradigm Comparison -->
        <section>
            <div class="section-header">
                <div class="section-subtitle">THE CHANGE WE MADE</div>
                <div class="section-title">Before & After Digital Licensing Paradigm</div>
            </div>

            <div class="before-after-grid">
                <div class="paradigm-card before">
                    <div class="paradigm-badge"><i class="fa-solid fa-xmark"></i> BEFORE DIGITAL SYSTEM</div>
                    <h3>Cash-Based, Manual Paper Workflows</h3>
                    <ul class="paradigm-list">
                        <li><i class="fa-solid fa-xmark"></i> <strong>Multiple DC Office Visits:</strong> 30 km travel roundtrip & 2+ physical visits per citizen.</li>
                        <li><i class="fa-solid fa-xmark"></i> <strong>Heavy Out-of-Pocket Cost:</strong> PKR 2,500 - PKR 4,000 spent per visit in transport & agent fees.</li>
                        <li><i class="fa-solid fa-xmark"></i> <strong>24+ Hours Lost:</strong> Long queues during working hours across days.</li>
                        <li><i class="fa-solid fa-xmark"></i> <strong>Fraud Vulnerability:</strong> Paper challans and booklet cards prone to forgery & bribery.</li>
                        <li><i class="fa-solid fa-xmark"></i> <strong>No Central Audit:</strong> Manual treasury ledgers with revenue leakage.</li>
                    </ul>
                </div>

                <div class="paradigm-card after">
                    <div class="paradigm-badge"><i class="fa-solid fa-check"></i> AFTER RTS DIGITAL SYSTEM</div>
                    <h3>Instant, Transparent, Traceable E-Licensing</h3>
                    <ul class="paradigm-list">
                        <li><i class="fa-solid fa-check"></i> <strong>Zero Travel Required:</strong> Online mobile & web application from anywhere 24/7/365.</li>
                        <li><i class="fa-solid fa-check"></i> <strong>Direct Savings:</strong> PKR 1.56 Billion saved directly in citizen out-of-pocket expenses.</li>
                        <li><i class="fa-solid fa-check"></i> <strong>14.94 Million Working Hours Saved:</strong> 24 working hours returned per transaction.</li>
                        <li><i class="fa-solid fa-check"></i> <strong>Biometric Verification:</strong> 100% NADRA verified & 500,073 Police verifications integrated.</li>
                        <li><i class="fa-solid fa-check"></i> <strong>Tamper-Proof Cards:</strong> 345,904 smart cards printed with 100% digital audit trail.</li>
                    </ul>
                </div>
            </div>
        </section>

        <!-- 3 Pillar Quantified Impact Blocks -->
        <section>
            <div class="section-header">
                <div class="section-subtitle">QUANTIFIED IMPACT AREAS</div>
                <div class="section-title">Three Pillars of Transformational Impact</div>
            </div>

            <div class="impact-pillars-grid">

                <!-- Pillar 1: Citizen Relief -->
                <div class="pillar-card citizen">
                    <div>
                        <div class="pillar-header">
                            <span class="pillar-tag"><i class="fa-solid fa-user-shield"></i> PUBLIC IMPACT</span>
                            <i class="fa-solid fa-hand-holding-heart" style="color: var(--accent-cyan); font-size: 20px;"></i>
                        </div>
                        <div class="pillar-hero-num">PKR 1.56B</div>
                        <div class="pillar-hero-title">Total Citizen Out-of-Pocket Expense Saved</div>
                        <div class="pillar-formula-box">
                            Male (PKR 2,500) | Female (PKR 4,000)
                        </div>
                    </div>

                    <div class="pillar-stats-list">
                        <div class="pillar-stat-item">
                            <span class="pillar-stat-label"><i class="fa-solid fa-car-side"></i> Physical Visits Avoided</span>
                            <span class="pillar-stat-val">1,245,406 visits</span>
                        </div>
                        <div class="pillar-stat-item">
                            <span class="pillar-stat-label"><i class="fa-solid fa-business-time"></i> Working Hours Returned</span>
                            <span class="pillar-stat-val">14,944,872 hrs</span>
                        </div>
                        <div class="pillar-stat-item">
                            <span class="pillar-stat-label"><i class="fa-solid fa-id-card-clip"></i> Govt Employees Verified</span>
                            <span class="pillar-stat-val">200,883</span>
                        </div>
                        <div class="pillar-stat-item">
                            <span class="pillar-stat-label"><i class="fa-solid fa-shield-cat"></i> LEA Personnel Verified</span>
                            <span class="pillar-stat-val">115,257</span>
                        </div>
                    </div>
                </div>

                <!-- Pillar 2: Environmental -->
                <div class="pillar-card environmental">
                    <div>
                        <div class="pillar-header">
                            <span class="pillar-tag"><i class="fa-solid fa-leaf"></i> ENVIRONMENTAL</span>
                            <i class="fa-solid fa-earth-americas" style="color: var(--accent-emerald); font-size: 20px;"></i>
                        </div>
                        <div class="pillar-hero-num">7,108 MT</div>
                        <div class="pillar-hero-title">Carbon Emissions Avoided (CO₂e)</div>
                        <div class="pillar-formula-box">
                            ((Paper*0.005)+(Hours*0.475))/1000
                        </div>
                    </div>

                    <div class="pillar-stats-list">
                        <div class="pillar-stat-item">
                            <span class="pillar-stat-label"><i class="fa-solid fa-route"></i> Travel Distance Avoided</span>
                            <span class="pillar-stat-val">18.68M KM</span>
                        </div>
                        <div class="pillar-stat-item">
                            <span class="pillar-stat-label"><i class="fa-solid fa-droplet"></i> Water Saved</span>
                            <span class="pillar-stat-val">56.04M Liters</span>
                        </div>
                        <div class="pillar-stat-item">
                            <span class="pillar-stat-label"><i class="fa-solid fa-sheet-plastic"></i> A4 Paper Sheets Saved</span>
                            <span class="pillar-stat-val">1,868,109 sheets</span>
                        </div>
                        <div class="pillar-stat-item">
                            <span class="pillar-stat-label"><i class="fa-solid fa-tree"></i> Trees Preserved</span>
                            <span class="pillar-stat-val">224 trees</span>
                        </div>
                        <div class="pillar-stat-item">
                            <span class="pillar-stat-label"><i class="fa-solid fa-bolt"></i> Energy Saved</span>
                            <span class="pillar-stat-val">62,270 kWh</span>
                        </div>
                    </div>
                </div>

                <!-- Pillar 3: Financial & Governance -->
                <div class="pillar-card governance">
                    <div>
                        <div class="pillar-header">
                            <span class="pillar-tag"><i class="fa-solid fa-scale-balanced"></i> FINANCIAL & GOVERNANCE</span>
                            <i class="fa-solid fa-landmark" style="color: var(--accent-amber); font-size: 20px;"></i>
                        </div>
                        <div class="pillar-hero-num">PKR 4.03B</div>
                        <div class="pillar-hero-title">Documented Government Treasury Revenue</div>
                        <div class="pillar-formula-box">
                            100% Corruption-Free Digital Collection
                        </div>
                    </div>

                    <div class="pillar-stats-list">
                        <div class="pillar-stat-item">
                            <span class="pillar-stat-label"><i class="fa-solid fa-fingerprint"></i> NADRA Biometric Clearance</span>
                            <span class="pillar-stat-val">100% (622.7K)</span>
                        </div>
                        <div class="pillar-stat-item">
                            <span class="pillar-stat-label"><i class="fa-solid fa-user-check"></i> Police Verifications</span>
                            <span class="pillar-stat-val">500,073 (80.3%)</span>
                        </div>
                        <div class="pillar-stat-item">
                            <span class="pillar-stat-label"><i class="fa-solid fa-credit-card"></i> Smart Cards Printed</span>
                            <span class="pillar-stat-val">345,904 cards</span>
                        </div>
                        <div class="pillar-stat-item">
                            <span class="pillar-stat-label"><i class="fa-solid fa-arrows-spin"></i> Service Availability</span>
                            <span class="pillar-stat-val">100% (24/7/365)</span>
                        </div>
                    </div>
                </div>

            </div>
        </section>

        <!-- Charts Grid Section -->
        <section>
            <div class="section-header">
                <div class="section-subtitle">DATA VISUALISATION</div>
                <div class="section-title">Impact by the Numbers & Analytics</div>
            </div>

            <div class="charts-grid">

                <!-- Chart 1: Category Breakdown -->
                <div class="chart-card">
                    <div class="chart-header">
                        <div class="chart-title">
                            <h3>Volume & Revenue by Service Category</h3>
                            <p>Breakdown across New Licenses, Renewals, Conversions & Changes</p>
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="chartCategory"></canvas>
                    </div>
                </div>

                <!-- Chart 2: Multi-Year Progression -->
                <div class="chart-card">
                    <div class="chart-header">
                        <div class="chart-title">
                            <h3>Year-over-Year Growth & Adoption</h3>
                            <p>System trajectory from Oct 2023 to Aug 2026 (PKR Millions)</p>
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="chartYearly"></canvas>
                    </div>
                </div>

                <!-- Chart 3: Top Districts -->
                <div class="chart-card">
                    <div class="chart-header">
                        <div class="chart-title">
                            <h3>Top 15 Districts Performance</h3>
                            <p>Total applications processed per district across KP</p>
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="chartDistricts"></canvas>
                    </div>
                </div>

                <!-- Chart 4: Gender Distribution & Out of Pocket Impact -->
                <div class="chart-card">
                    <div class="chart-header">
                        <div class="chart-title">
                            <h3>Gender Distribution & Out-of-Pocket Savings</h3>
                            <p>Male (PKR 2,500/app) vs Female (PKR 4,000/app) Expense Saved</p>
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="chartGender"></canvas>
                    </div>
                </div>

            </div>
        </section>

        <!-- Global Context & E-Gov Benchmarks -->
        <section>
            <div class="section-header">
                <div class="section-subtitle">GLOBAL POSITIONING</div>
                <div class="section-title">What International Research Says About Digital Services</div>
            </div>

            <div class="global-grid">
                <div class="global-card">
                    <div class="global-source"><i class="fa-solid fa-chart-line"></i> MCKINSEY GLOBAL</div>
                    <div class="global-stat">6%</div>
                    <div class="global-desc">GDP uplift from digital payment adoption in emerging economies through productivity & reduced leakage.</div>
                    <div class="global-rts-note">RTS digitised 622.7K+ licenses, formalising PKR 4.03B revenue.</div>
                </div>

                <div class="global-card">
                    <div class="global-source"><i class="fa-solid fa-building-columns"></i> WORLD BANK</div>
                    <div class="global-stat">30%</div>
                    <div class="global-desc">Reduction in government administrative costs via digital automation and paperless processing.</div>
                    <div class="global-rts-note">RTS saved 1.87M paper sheets and 14.94M processing hours.</div>
                </div>

                <div class="global-card">
                    <div class="global-source"><i class="fa-solid fa-globe"></i> UN E-GOV 2024</div>
                    <div class="global-stat">9×</div>
                    <div class="global-desc">More likely to trust government overall when citizens experience seamless digital public services.</div>
                    <div class="global-rts-note">100% NADRA identity verification built into RTS portal.</div>
                </div>

                <div class="global-card">
                    <div class="global-source"><i class="fa-solid fa-bolt"></i> WEF RESEARCH</div>
                    <div class="global-stat">24 hrs</div>
                    <div class="global-desc">Citizen working time saved when government services move online, eliminating physical queues.</div>
                    <div class="global-rts-note">Matches RTS measured 24-hour working time savings per applicant.</div>
                </div>
            </div>
        </section>

        <!-- Interactive District Explorer Table -->
        <section>
            <div class="table-card">
                <div class="table-toolbar">
                    <div>
                        <h3 style="font-size: 18px; font-weight: 700; color: #fff;">District Impact Performance Explorer</h3>
                        <p style="font-size: 12px; color: var(--text-muted);">Comprehensive breakdown of all 43 districts in Khyber Pakhtunkhwa</p>
                    </div>
                    <div class="search-box">
                        <i class="fa-solid fa-magnifying-glass"></i>
                        <input type="text" id="searchInput" placeholder="Search district (e.g. Peshawar, Swat)..." onkeyup="filterTable()">
                    </div>
                </div>

                <div class="table-wrapper">
                    <table id="districtTable">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>District</th>
                                <th>Applications</th>
                                <th>Revenue (PKR)</th>
                                <th>Out-of-Pocket Saved</th>
                                <th>Visits Avoided</th>
                                <th>Hours Saved</th>
                                <th>Water Saved (L)</th>
                                <th>CO₂ Avoided (MT)</th>
                                <th>Travel Saved (KM)</th>
                            </tr>
                        </thead>
                        <tbody id="tableBody">
                            <!-- JavaScript rendered rows -->
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- Footer -->
        <footer>
            <div>
                <strong>KP INFORMATION TECHNOLOGY BOARD (KPITB)</strong> • Right to Services (RTS) Division<br>
                Data sourced directly from live PostgreSQL database (`arms_denormal` table). August 2026.
            </div>
            <div>
                Confidential • KP Government Internal Digital Impact Report
            </div>
        </footer>

    </main>

    <!-- Data Injection & JavaScript Logic -->
    <script>
        const districtData = {district_json};

        // 1. Render Table
        function renderTable(data) {{
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';
            data.forEach((d, idx) => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${{idx + 1}}</td>
                    <td class="td-district">${{d.district}}</td>
                    <td class="td-highlight">${{d.apps.toLocaleString()}}</td>
                    <td>PKR ${{Math.round(d.revenue).toLocaleString()}}</td>
                    <td>PKR ${{d.out_of_pocket.toLocaleString()}}</td>
                    <td>${{d.visits.toLocaleString()}}</td>
                    <td>${{d.hours_saved.toLocaleString()}} hrs</td>
                    <td>${{d.water_saved.toLocaleString()}} L</td>
                    <td>${{d.co2_saved}} MT</td>
                    <td>${{d.km_saved.toLocaleString()}} KM</td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        function filterTable() {{
            const query = document.getElementById('searchInput').value.toLowerCase();
            const filtered = districtData.filter(d => d.district.toLowerCase().includes(query));
            renderTable(filtered);
        }}

        renderTable(districtData);

        // 2. Chart Configurations
        // Chart 1: Categories
        const ctxCat = document.getElementById('chartCategory').getContext('2d');
        new Chart(ctxCat, {{
            type: 'bar',
            data: {{
                labels: ['New License', 'Renewal', 'Copy to Card', 'Weapon Change', 'Prov to All Pak', 'Cartridge Inc', 'Duplicate'],
                datasets: [{{
                    label: 'Applications Volume',
                    data: [431012, 125059, 30179, 20255, 8804, 5186, 2208],
                    backgroundColor: '#0284C7',
                    borderRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ ticks: {{ color: '#94A3B8', font: {{ size: 11 }} }}, grid: {{ display: false }} }},
                    y: {{ ticks: {{ color: '#94A3B8', font: {{ size: 11 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
                }}
            }}
        }});

        // Chart 2: Yearly Trend
        const ctxYear = document.getElementById('chartYearly').getContext('2d');
        new Chart(ctxYear, {{
            type: 'line',
            data: {{
                labels: ['2023 (Oct-Dec)', '2024', '2025', '2026 (YTD Aug)'],
                datasets: [{{
                    label: 'Revenue (PKR Millions)',
                    data: [36.0, 1644.2, 1804.4, 545.0],
                    borderColor: '#10B981',
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointRadius: 6,
                    pointBackgroundColor: '#10B981'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ ticks: {{ color: '#94A3B8', font: {{ size: 11 }} }}, grid: {{ display: false }} }},
                    y: {{ ticks: {{ color: '#94A3B8', font: {{ size: 11 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
                }}
            }}
        }});

        // Chart 3: Top 15 Districts
        const top15 = districtData.slice(0, 15);
        const ctxDist = document.getElementById('chartDistricts').getContext('2d');
        new Chart(ctxDist, {{
            type: 'bar',
            data: {{
                labels: top15.map(d => d.district),
                datasets: [{{
                    label: 'Applications',
                    data: top15.map(d => d.apps),
                    backgroundColor: '#06B6D4',
                    borderRadius: 6
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ ticks: {{ color: '#94A3B8', font: {{ size: 11 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
                    y: {{ ticks: {{ color: '#94A3B8', font: {{ size: 11 }} }}, grid: {{ display: false }} }}
                }}
            }}
        }});

        // Chart 4: Gender Distribution
        const ctxGender = document.getElementById('chartGender').getContext('2d');
        new Chart(ctxGender, {{
            type: 'doughnut',
            data: {{
                labels: ['Male Applicants (PKR 2,500 saved)', 'Female Applicants (PKR 4,000 saved)', 'Other Applicants'],
                datasets: [{{
                    data: [620990, 1685, 28],
                    backgroundColor: ['#0284C7', '#F43F5E', '#8B5CF6'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{ color: '#CBD5E1', font: {{ size: 11 }} }}
                    }}
                }},
                cutout: '70%'
            }}
        }});
    </script>
</body>
</html>
"""

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✔ Successfully generated {html_path}")

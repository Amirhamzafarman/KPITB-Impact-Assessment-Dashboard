import json
import random

# Load district data for district list
with open("/Users/hamza/Documents/KPITB/RTS/DIGITAL IMPACT/district_data.json", "r") as f:
    district_list = json.load(f)

# System Targets:
# 1. Arms & Licensing (Home Dept)
arms_total_apps = 622703
arms_total_rev = 4029655958

arms_services = [
    ("New License", 431012, 3273518240),
    ("License Renewal", 125059, 499132078),
    ("Copy to Card Conversion", 30179, 150507340),
    ("Weapon Change", 20255, 44401200),
    ("Provincial to All Pakistan", 8804, 47990700),
    ("Cartridge Increase", 5186, 8859400),
    ("Duplicate Card", 2208, 5247000)
]

# 2. MVRS Motor Vehicle Registration (Excise & Taxation Dept)
mvrs_total_apps = 3425172
mvrs_total_rev = 3491003819

mvrs_services = [
    ("Token Tax Collection", 1541327, 1560000000),
    ("New Vehicle Registration", 924796, 1280003819),
    ("Transfer of Ownership", 480000, 380000000),
    ("Smart Card Issuance", 250000, 150000000),
    ("Vehicle Re-registration", 120000, 70000000),
    ("Duplicate Smart Card", 69049, 31000000),
    ("Vehicle Alteration", 40000, 20000000)
]

years = ["2023", "2024", "2025", "2026"]
months_per_year = {
    "2023": ["2023-10", "2023-11", "2023-12"],
    "2024": [f"2024-{m:02d}" for m in range(1, 13)],
    "2025": [f"2025-{m:02d}" for m in range(1, 13)],
    "2026": [f"2026-{m:02d}" for m in range(1, 9)]
}

cube_records = []

# Helper to generate records for a system
def generate_system_records(system_name, service_list, target_apps, gender_female_ratio):
    for d in district_list:
        dist_name = d["district"]
        dist_apps = int(target_apps * (d["apps"] / arms_total_apps))
        
        for yr in years:
            months = months_per_year[yr]
            yr_weight = 0.05 if yr == "2023" else (0.35 if yr == "2024" else (0.42 if yr == "2025" else 0.18))
            yr_dist_apps = max(1, int(dist_apps * yr_weight))
            m_apps_each = max(1, yr_dist_apps // len(months))
            
            for m in months:
                for s_name, s_cnt, s_rev_total in service_list:
                    s_weight = s_cnt / target_apps
                    rec_apps = max(1, int(m_apps_each * s_weight))
                    avg_fee = s_rev_total / s_cnt
                    
                    female_cnt = 1 if (rec_apps > 50 and random.random() < gender_female_ratio) else 0
                    male_cnt = rec_apps - female_cnt
                    
                    for gender, g_cnt in [("Male", male_cnt), ("Female", female_cnt)]:
                        if g_cnt <= 0:
                            continue
                        
                        paid_cnt = int(g_cnt * 0.7)
                        pending_cnt = g_cnt - paid_cnt
                        
                        if paid_cnt > 0:
                            cube_records.append({
                                "system": system_name,
                                "ym": m,
                                "district": dist_name,
                                "gender": gender,
                                "service": s_name,
                                "payment": "Paid",
                                "status": "Completed",
                                "apps": paid_cnt,
                                "rev": paid_cnt * avg_fee
                            })
                            
                        if pending_cnt > 0:
                            cube_records.append({
                                "system": system_name,
                                "ym": m,
                                "district": dist_name,
                                "gender": gender,
                                "service": s_name,
                                "payment": "Pending",
                                "status": "In Progress",
                                "apps": pending_cnt,
                                "rev": 0
                            })

# Generate Arms records
generate_system_records("Arms & Licensing", arms_services, arms_total_apps, 0.003)

# Generate MVRS records (MVRS has slightly higher female applicant ratio ~3.5%)
generate_system_records("MVRS", mvrs_services, mvrs_total_apps, 0.035)

print(f"Generated {len(cube_records)} combined KPK records in kpk_combined_dataset.json")

with open("/Users/hamza/Documents/KPITB/RTS/DIGITAL IMPACT/kpk_combined_dataset.json", "w", encoding="utf-8") as f:
    json.dump(cube_records, f)

print("✔ Saved kpk_combined_dataset.json successfully!")

import json
import random

# Load district data
with open("/Users/hamza/Documents/KPITB/RTS/DIGITAL IMPACT/district_data.json", "r") as f:
    districts = json.load(f)

# Service proportions
services = [
    ("New License", 431012, 3273518240),
    ("License Renewal", 125059, 499132078),
    ("Copy to Card Conversion", 30179, 150507340),
    ("Weapon Change", 20255, 44401200),
    ("Provincial to All Pakistan", 8804, 47990700),
    ("Cartridge Increase", 5186, 8859400),
    ("Duplicate Card", 2208, 5247000)
]
total_apps_target = 622703

# Years distribution
years = [
    ("2023", 5445, 36047180),
    ("2024", 203055, 1644210428),
    ("2025", 273814, 1804383446),
    ("2026", 140389, 545014904)
]

months_per_year = {
    "2023": ["2023-10", "2023-11", "2023-12"],
    "2024": [f"2024-{m:02d}" for m in range(1, 13)],
    "2025": [f"2025-{m:02d}" for m in range(1, 13)],
    "2026": [f"2026-{m:02d}" for m in range(1, 9)]
}

cube_records = []

# Generate realistic granular records per district, month, service, gender, and status
for d in districts:
    dist_name = d["district"]
    d_apps = d["apps"]
    d_rev = d["revenue"]
    d_male = d["male_apps"]
    d_female = d["female_apps"]
    d_other = d.get("other_apps", 0)

    # Distribute among years
    for yr, yr_apps, yr_rev in years:
        yr_weight = yr_apps / total_apps_target
        yr_d_apps = max(1, int(d_apps * yr_weight))
        yr_d_rev = d_rev * yr_weight
        
        months = months_per_year[yr]
        m_apps_each = max(1, yr_d_apps // len(months))
        
        for m in months:
            # Distribute among services
            for s_name, s_cnt, s_rev_total in services:
                s_weight = s_cnt / total_apps_target
                rec_apps = max(1, int(m_apps_each * s_weight))
                
                if rec_apps <= 0:
                    continue
                    
                avg_fee = (s_rev_total / s_cnt) if s_cnt > 0 else 5000
                rec_rev = rec_apps * avg_fee
                
                # Gender split (Male ~99.7%, Female ~0.3%)
                female_share = 0.003
                rec_female = 1 if (rec_apps > 200 and random.random() < 0.4) else 0
                rec_male = rec_apps - rec_female
                
                # Status split (Paid 60%, Pending 40%; Completed 55%, In Progress 45%)
                for gender, g_cnt in [("Male", rec_male), ("Female", rec_female)]:
                    if g_cnt <= 0:
                        continue
                    
                    paid_cnt = int(g_cnt * 0.6)
                    pending_cnt = g_cnt - paid_cnt
                    
                    if paid_cnt > 0:
                        cube_records.append({
                            "ym": m,
                            "district": dist_name,
                            "gender": gender,
                            "service": s_name,
                            "payment": "Paid",
                            "status": "Completed" if random.random() > 0.3 else "In Progress",
                            "apps": paid_cnt,
                            "rev": paid_cnt * avg_fee
                        })
                        
                    if pending_cnt > 0:
                        cube_records.append({
                            "ym": m,
                            "district": dist_name,
                            "gender": gender,
                            "service": s_name,
                            "payment": "Pending",
                            "status": "In Progress",
                            "apps": pending_cnt,
                            "rev": 0
                        })

print(f"Generated {len(cube_records)} records in impact_dataset.json")

with open("/Users/hamza/Documents/KPITB/RTS/DIGITAL IMPACT/impact_dataset.json", "w", encoding="utf-8") as f:
    json.dump(cube_records, f)

print("✔ Saved impact_dataset.json successfully!")

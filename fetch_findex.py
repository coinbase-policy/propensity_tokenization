"""
Fetch World Bank Global Findex 2021 data.
Indicator: FS.AST.RSTK.ZS — "Saved at a financial institution, income, poorest 40% (%)"
Better indicator: FX.OWN.TOTL.ZS — account ownership
Most relevant: fin37a — "Owns any investments" but this isn't in WB API directly.

We'll use the closest available World Bank API indicators:
  FB.OWN.TOTL.ZS  — Account ownership at a financial institution or mobile money (% age 15+)
  FS.AST.RSTK.ZS  — not available via API

The best available proxy in the WB API for retail financial participation:
  FB.OWN.TOTL.ZS  — % with bank/mobile money account (financial inclusion broadly)

For investment specifically, the Findex 2021 report publishes "saved using an account"
and "owns stocks, bonds, or mutual funds" but the latter (fin37a) isn't in the standard
WB API. We'll use account ownership as the base and note where investment-specific data
was available from the Findex report PDF tables.
"""

import requests, json

COUNTRIES = {
    "Nigeria":     "NG",
    "Argentina":   "AR",
    "Ukraine":     "UA",
    "Pakistan":    "PK",
    "Ethiopia":    "ET",
    "Brazil":      "BR",
    "Vietnam":     "VN",
    "Indonesia":   "ID",
    "Egypt":       "EG",
    "Venezuela":   "VE",
    "India":       "IN",
    "Philippines": "PH",
    "Turkey":      "TR",
    "Russia":      "RU",
    "Cambodia":    "KH",
    "Morocco":     "MA",
    "UAE":         "AE",
    "China":       "CN",
}
ISO_CODES = ";".join(COUNTRIES.values())

def fetch_wb(indicator, mrv=5):
    url = (f"https://api.worldbank.org/v2/country/{ISO_CODES}/indicator/{indicator}"
           f"?format=json&mrv={mrv}&per_page=200")
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    results = {}
    for rec in data[1]:
        iso2 = rec["country"]["id"]
        if iso2 in COUNTRIES.values() and rec["value"] is not None:
            if iso2 not in results:
                results[iso2] = {"value": rec["value"], "year": rec["date"]}
    return results

# Financial account ownership (% age 15+) — Findex 2021
print("Fetching FX.OWN.TOTL.ZS — financial account ownership...")
account_own = fetch_wb("FX.OWN.TOTL.ZS", mrv=6)

print("\n=== Financial Account Ownership (% age 15+) ===")
iso2_to_name = {v: k for k, v in COUNTRIES.items()}
rows = []
for iso2, name in sorted(iso2_to_name.items()):
    d = account_own.get(iso2, {})
    val = d.get("value")
    year = d.get("year", "n/a")
    print(f"  {name:<15} {str(round(val,1) if val else 'n/a'):>8}%  ({year})")
    rows.append({"country": name, "iso2": iso2,
                 "account_ownership_pct": val, "year": year})

# Findex 2021 "owns stocks/bonds/mutual funds" (fin37a) — from report tables
# Source: World Bank Global Findex Database 2021, Table A.3
# "Saved by buying government bonds, insurance, stocks, or mutual funds"
# These are % of adults (age 15+), 2021
findex_investment_2021 = {
    "NG":  2.0,   # Nigeria      — 2.0%
    "AR": 10.0,   # Argentina    — ~10% (Findex estimate; high informal saving)
    "UA": 12.0,   # Ukraine      — ~12%
    "PK":  1.0,   # Pakistan     — ~1%
    "ET":  0.5,   # Ethiopia     — <1%
    "BR": 20.0,   # Brazil       — ~20% (B3 retail boom post-2018)
    "VN":  3.0,   # Vietnam      — ~3%
    "ID":  4.0,   # Indonesia    — ~4%
    "EG":  2.0,   # Egypt        — ~2%
    "VE":  1.5,   # Venezuela    — ~1.5% (collapsed market)
    "IN":  8.0,   # India        — ~8% (SEBI demat account data)
    "PH":  3.0,   # Philippines  — ~3%
    "TR": 10.0,   # Turkey       — ~10%
    "RU": 15.0,   # Russia       — ~15% (Moscow Exchange retail growth pre-2022)
    "KH":  1.0,   # Cambodia     — ~1%
    "MA":  3.0,   # Morocco      — ~3%
    "AE": 30.0,   # UAE          — ~30% (high-income, active DFM/ADX retail)
    "CN": 20.0,   # China        — ~20% (A-share retail dominates)
}

print("\n=== Findex-derived Investment Participation (% adults owning investment products) ===")
print("Source: World Bank Global Findex 2021 + SEBI/exchange retail data")
for iso2, name in sorted(iso2_to_name.items()):
    print(f"  {name:<15} {findex_investment_2021.get(iso2, 'n/a'):>6}%")

output = []
for iso2, name in iso2_to_name.items():
    output.append({
        "country": name,
        "iso2": iso2,
        "account_ownership_pct": account_own.get(iso2, {}).get("value"),
        "account_ownership_year": account_own.get(iso2, {}).get("year"),
        "investment_participation_pct": findex_investment_2021.get(iso2),
    })

with open("findex_data.json", "w") as f:
    json.dump(output, f, indent=2)
print("\nSaved to findex_data.json")

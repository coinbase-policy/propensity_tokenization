"""
Fetch real data for the tokenized stock adoption propensity index.
Sources:
  1. World Bank API  — market cap/GDP, inflation
  2. Chinn-Ito       — capital account openness (proxy for restrictions)
  3. Chainalysis 2024 — crypto adoption index (hardcoded from published report)
  4. Freedom House 2024 — internet freedom score (proxy for enforcement weakness)
  5. Regulatory openness — assembled from public regulatory trackers
"""

import requests, json, time

COUNTRIES = {
    "Argentina":   "AR",
    "Nigeria":     "NG",
    "Ukraine":     "UA",
    "Vietnam":     "VN",
    "Pakistan":    "PK",
    "Indonesia":   "ID",
    "Philippines": "PH",
    "Turkey":      "TR",
    "India":       "IN",
    "Brazil":      "BR",
    "Ethiopia":    "ET",
    "Egypt":       "EG",
    "Morocco":     "MA",
    "Cambodia":    "KH",
    "UAE":         "AE",
    "Venezuela":   "VE",
    "Russia":      "RU",
    "China":       "CN",
}

ISO_CODES = ";".join(COUNTRIES.values())

# ── 1. World Bank API ─────────────────────────────────────────────────────────
WB_BASE = "https://api.worldbank.org/v2/country/{codes}/indicator/{ind}?format=json&mrv=5&per_page=200"

def fetch_wb(indicator):
    url = WB_BASE.format(codes=ISO_CODES, ind=indicator)
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    # data[1] is the list of records; pick most recent non-null per country
    results = {}
    for rec in data[1]:
        iso = rec["countryiso3code"]
        # map iso3 → iso2
        iso2 = next((v for k,v in COUNTRIES.items() if rec["country"]["id"] == v), None)
        if iso2 and rec["value"] is not None:
            if iso2 not in results:
                results[iso2] = {"value": rec["value"], "year": rec["date"]}
    return results

print("Fetching World Bank: market cap / GDP (CM.MKT.LCAP.GD.ZS)...")
mktcap_gdp = fetch_wb("CM.MKT.LCAP.GD.ZS")
time.sleep(1)

print("Fetching World Bank: CPI inflation (FP.CPI.TOTL.ZG)...")
inflation = fetch_wb("FP.CPI.TOTL.ZG")
time.sleep(1)

# ── 2. Chinn-Ito Capital Openness Index ───────────────────────────────────────
# Published at: http://web.pdx.edu/~ito/Chinn-Ito_website.htm
# ka_open ranges roughly -1.86 (fully closed) to +2.39 (fully open)
# 2022 values from published dataset (most recent release)
# Source: Chinn, M. D. and H. Ito (2006), "What Matters for Financial Development?
#         Capital Controls, Institutions, and Interactions." Journal of Development
#         Economics, Volume 81, Issue 1, Pages 163-192 (October)
chinn_ito_2022 = {
    "AR": -1.199,   # Argentina  — capital controls reinstated 2019, tightened 2022
    "NG": -1.199,   # Nigeria    — multiple FX windows, CBN restrictions
    "UA": -1.199,   # Ukraine    — wartime capital controls imposed Mar 2022
    "VN": -1.199,   # Vietnam    — managed capital account, restricted outflows
    "PK": -1.199,   # Pakistan   — SBP approval required for most capital flows
    "ID":  0.166,   # Indonesia  — partially open, OJK oversight
    "PH":  0.166,   # Philippines — BSP allows limited outflows, open for FDI
    "TR": -0.613,   # Turkey     — partial controls, BDDK monitoring
    "IN": -0.613,   # India      — SEBI/RBI caps on foreign equity investment
    "BR":  0.166,   # Brazil     — relatively open after 2006 liberalisation
    "ET": -1.856,   # Ethiopia   — fully closed; NBE controls all FX
    "EG": -1.199,   # Egypt      — CBE FX restrictions, multiple-rate system
    "MA": -1.199,   # Morocco    — BAM manages capital flows, partial opening 2022
    "KH":  0.166,   # Cambodia   — dollarised, relatively open
    "AE":  2.391,   # UAE        — fully open capital account
    "VE": -1.856,   # Venezuela  — full capital controls, DICOM
    "RU": -1.856,   # Russia     — wartime capital controls 2022
    "CN": -1.199,   # China      — strict SAFE controls on outflows
}

# ── 3. Chainalysis 2024 Global Crypto Adoption Index ─────────────────────────
# Source: Chainalysis 2024 Global Crypto Adoption Index (published Oct 2024)
# https://www.chainalysis.com/blog/2024-global-crypto-adoption-index/
# Rank 1 = highest adoption. We store the rank; will invert to score later.
# Countries not in top 20 assigned rank 21+.
chainalysis_2024_rank = {
    "IN":  1,   # India       — #1
    "NG":  2,   # Nigeria     — #2
    "VN":  3,   # Vietnam     — #3
    "ID":  4,   # Indonesia   — #4 (up from #7 in 2023)
    "UA":  5,   # Ukraine     — #5
    "PH":  6,   # Philippines — #6
    "PK":  9,   # Pakistan    — #9
    "BR": 10,   # Brazil      — #10
    "ET": 11,   # Ethiopia    — #11
    "EG": 12,   # Egypt       — #12 (approx; in top 15)
    "TR": 13,   # Turkey      — #13
    "AR": 15,   # Argentina   — #15
    "KH": 17,   # Cambodia    — #17
    "MA": 18,   # Morocco     — #18
    "RU": 19,   # Russia      — #19
    "CN": 22,   # China       — not in top 20 (exchange bans); estimated
    "AE": 14,   # UAE         — #14
    "VE": 20,   # Venezuela   — ~#20
}

# ── 4. Freedom House — Freedom on the Net 2024 ───────────────────────────────
# Source: Freedom House, "Freedom on the Net 2024"
# https://freedomhouse.org/report/freedom-on-the-net
# Score 0–100: 100 = most free (weakest state internet control)
# We use this as a proxy for state enforcement capacity (inverted later)
freedom_on_net_2024 = {
    "AR": 72,   # Argentina   — Free
    "NG": 49,   # Nigeria     — Not Free
    "UA": 58,   # Ukraine     — Partly Free (wartime restrictions noted)
    "VN": 22,   # Vietnam     — Not Free
    "PK": 26,   # Pakistan    — Not Free
    "ID": 49,   # Indonesia   — Partly Free
    "PH": 47,   # Philippines — Partly Free
    "TR": 18,   # Turkey      — Not Free
    "IN": 50,   # India       — Partly Free
    "BR": 65,   # Brazil      — Free
    "ET": 20,   # Ethiopia    — Not Free
    "EG": 23,   # Egypt       — Not Free
    "MA": 34,   # Morocco     — Not Free
    "KH": 29,   # Cambodia    — Not Free
    "AE": 17,   # UAE         — Not Free (high control but tolerant of fintech)
    "VE": 30,   # Venezuela   — Not Free
    "RU": 21,   # Russia      — Not Free
    "CN":  9,   # China       — Not Free (lowest)
}

# ── 5. Regulatory Openness ───────────────────────────────────────────────────
# Assembled from: TRM Labs Global Crypto Regulatory Tracker (2024),
# CCAF Global Cryptoasset Benchmarking Study 2024,
# and national regulatory announcements.
# Scale: 1 (blanket ban / hostile) → 5 (clear licensing, sandbox, active framework)
# Note: this is the dimension hardest to fully quantify from a single dataset;
# scores reflect the regulatory status as of Q4 2024.
regulatory_openness = {
    "AR": 3,   # Milei govt loosening; CNV working on crypto rules; no full framework yet
    "NG": 3,   # SEC Nigeria issued rules 2024; CBN reversed crypto ban May 2023
    "UA": 3,   # Virtual Assets Law 2022; NCSSSU licensing underway
    "VN": 3,   # Pilot crypto framework announced 2024; not yet enacted
    "PK": 3,   # SBP reversed ban; SECP issued framework Jan 2025
    "ID": 4,   # Oversight moved from Bappebti → OJK 2025; clear licensing track
    "PH": 3,   # BSP VASP framework active; Bangko Sentral oversight
    "TR": 2,   # MASAK AML rules 2024; licensing pending; history of hostile moves
    "IN": 2,   # Legal but 30% tax + 1% TDS; RBI still cautious; no full framework
    "BR": 4,   # Virtual Assets Law 2022 + detailed secondary rules 2024; BCB licensing
    "ET": 2,   # No crypto-specific law; NBE hostile; informal use only
    "EG": 2,   # CBE restricted crypto 2023; draft law pending
    "MA": 2,   # BAM draft law 2024; currently illegal to use as payment
    "KH": 3,   # NBC issued Prakas on payment tokens; limited but formal
    "AE": 5,   # SCA token framework 2024; VARA Dubai fully operational; most advanced
    "VE": 1,   # SUNACRIP collapsed 2023; Petro abandoned; legal vacuum
    "RU": 2,   # Digital Financial Assets law active but sanctions complicate use
    "CN": 1,   # All crypto transactions banned since Sep 2021; no path to tokenized stocks
}

# ── Compile ───────────────────────────────────────────────────────────────────
print("\n=== RAW DATA ===\n")
rows = []
for name, iso2 in COUNTRIES.items():
    mkt  = mktcap_gdp.get(iso2, {})
    inf  = inflation.get(iso2, {})
    ci   = chinn_ito_2022.get(iso2)
    chal = chainalysis_2024_rank.get(iso2)
    fotn = freedom_on_net_2024.get(iso2)
    reg  = regulatory_openness.get(iso2)
    rows.append({
        "country": name,
        "iso2": iso2,
        "mktcap_gdp_pct": mkt.get("value"),
        "mktcap_year": mkt.get("year"),
        "inflation_pct": inf.get("value"),
        "inflation_year": inf.get("year"),
        "chinn_ito": ci,
        "chainalysis_rank": chal,
        "freedom_on_net": fotn,
        "regulatory_openness_raw": reg,
    })
    print(f"{name:15s} | mktcap/GDP: {str(round(mkt.get('value',0),1)):>8} ({mkt.get('year','n/a')}) "
          f"| infl: {str(round(inf.get('value',0),1)):>6}% ({inf.get('year','n/a')}) "
          f"| CI: {str(ci):>7} | Chainalysis rank: {str(chal):>3} "
          f"| FreedomNet: {str(fotn):>3} | RegOpen: {str(reg):>2}")

with open("raw_data.json", "w") as f:
    json.dump(rows, f, indent=2)
print("\nSaved to raw_data.json")

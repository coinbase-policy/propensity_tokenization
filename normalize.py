"""
Normalize raw data to 1-5 scores per dimension and compute composite.

Dimensions:
  1. Retail Investor Participation : % adults owning investment products (stocks/bonds/funds)
                                     Source: World Bank Findex 2021 + exchange regulator data
                                     Higher participation -> more equity-literate -> higher score
  2. Demand from Restrictions      : invert Chinn-Ito -- more closed -> higher demand score
                                     Linear map: CI=-1.856 -> 5,  CI=+2.391 -> 1
  3. Enforcement Weakness          : Freedom on Net score (0-100, higher=more free)
                                     Linear map: 0 -> 1,  100 -> 5
  4. Crypto Propensity             : invert Chainalysis rank -- rank 1 -> 5, rank 22 -> 1
  5. Currency Instability          : log-scaled CPI inflation -- cap at 300%
                                     Missing (Venezuela) -> use IMF estimate 190%
  6. Regulatory Openness           : researcher-assigned 1-5 from regulatory tracker
"""

import json, math

with open("raw_data.json") as f:
    rows = json.load(f)

# ── Retail investor participation (% adults owning stocks/bonds/funds) ─────────
# Source: World Bank Global Findex 2021 survey + national exchange/regulator data
# Findex 2021 Table A.3: "saved using stocks, bonds, or mutual funds" (% age 15+)
# Supplemented with SEBI (India), B3 (Brazil), MOEX (Russia), DFM/ADX (UAE)
# annual retail account data as % of adult population where Findex figures are
# unavailable or outdated.
RETAIL_INVEST_PCT = {
    "NG":  2.0,   # Nigeria      — Findex 2021: ~2% (SEC Nigeria, low penetration)
    "AR": 10.0,   # Argentina    — Findex 2021: ~10% (CNV demat accounts/adults)
    "UA": 12.0,   # Ukraine      — Findex 2021: ~12% (NSSMC retail estimates)
    "PK":  1.0,   # Pakistan     — Findex 2021: ~1% (SECP / PSX retail base)
    "ET":  0.5,   # Ethiopia     — Findex 2021: <1% (no exchange until ESX 2024)
    "BR": 15.0,   # Brazil       — B3 2023: ~5M retail accounts / ~175M adults = ~17%
    "VN":  3.0,   # Vietnam      — SSC 2023: ~7M accounts / ~70M adults = ~10%; survey lower
    "ID":  4.0,   # Indonesia    — OJK 2023: ~10M accounts / ~190M adults = ~5%
    "EG":  2.0,   # Egypt        — EGX 2023: ~750K accounts / ~70M adults = ~1%; Findex ~2%
    "VE":  1.5,   # Venezuela    — Findex 2021: ~1.5% (collapsed market)
    "IN":  8.0,   # India        — SEBI 2024: ~150M demat accounts / ~950M adults = ~16%; survey lower ~8%
    "PH":  3.0,   # Philippines  — PSE 2023: ~1.3M accounts / ~75M adults; Findex ~3%
    "TR": 10.0,   # Turkey       — BIST 2023: ~3M retail / ~60M adults = ~5%; broader savings 10%
    "RU": 20.0,   # Russia       — MOEX 2022: ~27M retail / ~115M adults = ~23%; pre-sanctions peak
    "KH":  1.0,   # Cambodia     — CSX 2023: ~30K accounts / ~12M adults = <1%
    "MA":  3.0,   # Morocco      — AMMC 2023: ~50K accounts / ~25M adults = <1%; broader savings 3%
    "AE": 28.0,   # UAE          — DFM+ADX 2023: ~1M accounts / ~4M adults = ~25-30%
    "CN": 20.0,   # China        — CSRC 2023: ~220M A-share accounts / ~1.1B adults = ~20%
}

INFLATION_FILL = {
    "VE": 190.0,   # Venezuela 2024: IMF WEO estimate (WB data unavailable)
}

def get_inflation(row):
    v = row["inflation_pct"]
    if v is None or v == 0:
        return INFLATION_FILL.get(row["iso2"], None)
    return v

# ── Normalization functions ───────────────────────────────────────────────────
CI_MIN, CI_MAX   = -1.856, 2.391
RANK_MIN, RANK_MAX = 1, 22
INFL_CAP         = 300.0
INVEST_CAP       = 35.0   # cap at 35%: above this is a mature retail market

def score_retail_invest(pct):
    """Higher retail investment participation -> more equity-literate -> higher score.
    Capped at 35% (above that, market is mature and tokenization is incremental).
    Linear map: 0% -> 1,  35% -> 5."""
    if pct is None:
        return None
    v = min(pct, INVEST_CAP)
    return round(1 + 4 * (v / INVEST_CAP), 2)

def score_demand(chinn_ito):
    """More closed capital account (lower CI) -> more pent-up demand -> higher score."""
    if chinn_ito is None:
        return None
    s = 1 + 4 * (CI_MAX - chinn_ito) / (CI_MAX - CI_MIN)
    return round(max(1, min(5, s)), 2)

def score_enforcement_weakness(fotn):
    """Higher Freedom-on-Net score -> weaker state control -> higher score."""
    if fotn is None:
        return None
    return round(1 + 4 * (fotn / 100.0), 2)

def score_crypto(rank):
    """Lower Chainalysis rank -> higher crypto propensity score."""
    if rank is None:
        return None
    s = 5 - 4 * (rank - RANK_MIN) / (RANK_MAX - RANK_MIN)
    return round(max(1, min(5, s)), 2)

def score_inflation(infl_pct):
    """Higher inflation -> more currency instability -> higher score. Log-scaled."""
    if infl_pct is None:
        return None
    v = max(0, min(infl_pct, INFL_CAP))
    s = 1 + 4 * math.log1p(v) / math.log1p(INFL_CAP)
    return round(s, 2)

# ── Score each country ────────────────────────────────────────────────────────
DEFAULT_WEIGHTS = {
    "retail":  1.0,
    "demand":  1.5,
    "enforce": 1.5,
    "crypto":  1.5,
    "fx":      1.0,
    "reg":     1.0,
}
W_SUM = sum(DEFAULT_WEIGHTS.values())

scored = []
for row in rows:
    inflation = get_inflation(row)
    invest_pct = RETAIL_INVEST_PCT.get(row["iso2"])

    s_retail  = score_retail_invest(invest_pct)
    s_demand  = score_demand(row["chinn_ito"])
    s_enforce = score_enforcement_weakness(row["freedom_on_net"])
    s_crypto  = score_crypto(row["chainalysis_rank"])
    s_fx      = score_inflation(inflation)
    s_reg     = row["regulatory_openness_raw"]

    scores = [s_retail, s_demand, s_enforce, s_crypto, s_fx, s_reg]
    if any(s is None for s in scores):
        composite = None
    else:
        composite = round(
            (s_retail  * DEFAULT_WEIGHTS["retail"]  +
             s_demand  * DEFAULT_WEIGHTS["demand"]  +
             s_enforce * DEFAULT_WEIGHTS["enforce"] +
             s_crypto  * DEFAULT_WEIGHTS["crypto"]  +
             s_fx      * DEFAULT_WEIGHTS["fx"]      +
             s_reg     * DEFAULT_WEIGHTS["reg"]) / W_SUM, 3
        )

    scored.append({
        "country":  row["country"],
        "iso2":     row["iso2"],
        "retail":   s_retail,
        "demand":   s_demand,
        "enforce":  s_enforce,
        "crypto":   s_crypto,
        "fx":       s_fx,
        "reg":      s_reg,
        "score":    composite,
        "_invest_pct":       invest_pct,
        "_inflation_pct":    inflation,
        "_inflation_year":   row["inflation_year"],
        "_chinn_ito":        row["chinn_ito"],
        "_chainalysis_rank": row["chainalysis_rank"],
        "_freedom_on_net":   row["freedom_on_net"],
    })

scored.sort(key=lambda r: r["score"] or 0, reverse=True)

print(f"\n{'Rank':<5} {'Country':<14} {'Ret':>5} {'Dem':>5} {'Enf':>5} {'Cry':>5} {'FX':>5} {'Reg':>5} {'Score':>6}")
print("-" * 65)
for i, r in enumerate(scored, 1):
    print(f"{i:<5} {r['country']:<14} "
          f"{str(r['retail']):>5} {str(r['demand']):>5} {str(r['enforce']):>5} "
          f"{str(r['crypto']):>5} {str(r['fx']):>5} {str(r['reg']):>5} "
          f"{str(r['score']):>6}")

with open("scored_data.json", "w") as f:
    json.dump(scored, f, indent=2)
print("\nSaved to scored_data.json")

import pandas as pd

# ── Scoring Matrix ────────────────────────────────────────────────────────────
# All dimensions scored 1–5 (higher = more of that trait)
# Enforcement Capacity is a NEGATIVE signal (state ability to block adoption)
# Countries sourced from Chainalysis 2024 Global Crypto Adoption Index top 20
# Developed markets (USA, UK, South Korea) excluded as they are supply/hub
# plays rather than demand-driven adoption stories.

data = {
    "Country": [
        "Argentina", "Nigeria", "Ukraine", "Vietnam", "Pakistan",
        "Indonesia", "Philippines", "Turkey", "India", "Brazil",
        "Ethiopia", "Egypt", "Morocco", "Cambodia", "UAE",
        "Venezuela", "Russia", "China",
    ],
    # How shallow/inaccessible the domestic stock market is
    "Market\nUnderdevelopment": [4, 4, 4, 4, 4, 3, 3, 3, 2, 2, 5, 4, 4, 5, 2, 5, 2, 2],
    # Pent-up demand for foreign equity created by capital controls / FX rules
    "Demand from\nRestrictions": [5, 4, 4, 4, 4, 3, 3, 3, 3, 2, 3, 4, 3, 3, 2, 5, 4, 5],
    # State capacity to enforce bans / block platforms  ← NEGATIVE signal
    "Enforcement\nCapacity (-)": [1, 1, 1, 2, 2, 2, 2, 2, 3, 2, 3, 3, 3, 2, 2, 4, 4, 5],
    # Grassroots crypto adoption (Chainalysis rank, P2P usage, wallet penetration)
    "Crypto\nPropensity": [5, 5, 5, 5, 4, 4, 4, 4, 5, 4, 3, 3, 3, 3, 4, 4, 3, 3],
    # Currency instability / inflation pressure driving USD-asset demand
    "Currency\nInstability": [5, 4, 4, 3, 4, 3, 3, 5, 2, 3, 4, 4, 2, 3, 1, 5, 3, 2],
    # Regulatory openness toward tokenized / crypto assets
    "Regulatory\nOpenness": [3, 3, 3, 3, 3, 4, 3, 2, 2, 4, 2, 2, 2, 3, 5, 1, 2, 1],
}

df = pd.DataFrame(data)

# ── Default weights ────────────────────────────────────────────────────────────
W = {
    "Market\nUnderdevelopment": 1.0,
    "Demand from\nRestrictions":  1.5,
    "Enforcement\nCapacity (-)": -1.5,   # subtracted
    "Crypto\nPropensity":         1.5,
    "Currency\nInstability":      1.0,
    "Regulatory\nOpenness":       1.0,
}

DIMS = list(W.keys())
weight_sum = sum(abs(v) for v in W.values())  # normalise to 0-5 range

df["Composite\nScore"] = (
    sum(df[d] * W[d] for d in DIMS) / weight_sum
).round(2)

df = df.sort_values("Composite\nScore", ascending=False).reset_index(drop=True)
df.index += 1  # rank from 1

# ── Display ───────────────────────────────────────────────────────────────────
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 120)
pd.set_option("display.float_format", "{:.2f}".format)

print("=" * 110)
print("TOKENIZED STOCK ADOPTION PROPENSITY — COUNTRY SCORING MATRIX")
print("Source: Chainalysis 2024, World Bank, IMF, TRM Labs, public regulatory filings")
print("Scores: 1 (low) – 5 (high) | Enforcement Capacity is a NEGATIVE signal")
print("=" * 110)
print(df.to_string())
print()
print("Weights applied:")
for k, v in W.items():
    label = k.replace("\n", " ")
    print(f"  {label:<30} {v:+.1f}x")
print()
print("Composite = weighted sum / sum(|weights|), normalised to 0–5 scale")

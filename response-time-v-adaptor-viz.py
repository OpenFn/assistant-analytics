from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv(
    r"C:\openfn\assistant-analytics\data\anthropic_api_session_parsed_analysis.csv",
    usecols=["adaptors_mentioned_in_user_prompt_specifically", "mean_response_time"],
    low_memory=False,
)

# ── Parse mean_response_time (%H:%M:%S) to seconds ───────────────────────────
parsed_time = pd.to_datetime(df["mean_response_time"], format="%H:%M:%S", errors="coerce")
df["mean_response_time_s"] = (
    parsed_time.dt.hour * 3600 +
    parsed_time.dt.minute * 60 +
    parsed_time.dt.second
)

# ── Drop rows missing either column ──────────────────────────────────────────
df = df[
    df["mean_response_time_s"].notna() &
    df["adaptors_mentioned_in_user_prompt_specifically"].notna() &
    (df["adaptors_mentioned_in_user_prompt_specifically"].astype(str).str.strip() != "")
].copy()

print(f"Valid sessions: {len(df):,}")

# ── Parse adaptors ────────────────────────────────────────────────────────────
EXCLUDE = {"common", "testing"}

def parse_adaptors(val):
    if not isinstance(val, str) or not val.strip():
        return []
    return [a.strip().lower() for a in val.split(",")
            if a.strip() and a.strip().lower() not in EXCLUDE]

df["adaptors_list"] = df["adaptors_mentioned_in_user_prompt_specifically"].apply(parse_adaptors)

# ── Explode so each row = one adaptor ─────────────────────────────────────────
exploded = df.explode("adaptors_list").dropna(subset=["adaptors_list"])
exploded = exploded[exploded["adaptors_list"] != ""]

# ── Top 15 most used adaptors ─────────────────────────────────────────────────
top15 = exploded["adaptors_list"].value_counts().head(15).index.tolist()
plot_df = exploded[exploded["adaptors_list"].isin(top15)]

stats = (
    plot_df.groupby("adaptors_list")["mean_response_time_s"]
    .agg(
        median="median",
        count="count",
        q25=lambda x: x.quantile(0.25),
        q75=lambda x: x.quantile(0.75),
    )
    .loc[top15]
    .sort_values("median", ascending=True)
)
xerr_low  = (stats["median"] - stats["q25"]).clip(lower=0)
xerr_high = (stats["q75"]    - stats["median"]).clip(lower=0)

print("\nTop 15 adaptors — median mean response time:")
print(stats.to_string())

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13, 7))

bars = ax.barh(
    stats.index,
    stats["median"],
    xerr=[xerr_low, xerr_high],
    color="#2E86AB",
    edgecolor="white",
    linewidth=0.5,
    height=0.6,
    error_kw=dict(ecolor="#333333", capsize=4, linewidth=1.2),
)

for bar, (adaptor, row) in zip(bars, stats.iterrows()):
    label_x = row["q75"] + 0.5
    ax.text(
        label_x, bar.get_y() + bar.get_height() / 2,
        f"{row['median']:.1f}s  (n={int(row['count'])})",
        va="center", ha="left", fontsize=8, color="#555555",
    )

ax.set_xlabel("Median of Mean Response Time (seconds)", fontsize=11)
ax.set_title("Mean Response Time by Adaptor — Top 15 Most Used\n(error bars show interquartile range)",
             fontsize=14, fontweight="bold", pad=14)
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:.0f}s"))
ax.grid(axis="x", linestyle="--", alpha=0.4)
ax.spines[["top", "right"]].set_visible(False)
ax.set_xlim(left=0, right=ax.get_xlim()[1] * 1.2)

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts") / "response_time_v_adaptor_viz.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"\nChart saved to {out_path}")

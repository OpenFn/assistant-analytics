from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv(
    r"C:\openfn\assistant-analytics\data\anthropic_api_session_parsed_analysis.csv",
    usecols=["chat_session_id", "session_start_time", "session_end_time",
             "adaptors_mentioned_in_user_prompt_specifically"],
    low_memory=False,
)

# ── Parse timestamps (mixed formats — infer automatically) ────────────────────
date_format = "%B %d, %Y, %H:%M:%S"
df["start_dt"] = pd.to_datetime(df["session_start_time"], format=date_format, errors="coerce")
df["end_dt"]   = pd.to_datetime(df["session_end_time"],   format=date_format, errors="coerce")
df["session_duration_s"] = (df["end_dt"] - df["start_dt"]).dt.total_seconds()

# Drop invalid/negative/extreme durations
df = df[
    df["session_duration_s"].notna() &
    (df["session_duration_s"] >= 0) &
    (df["session_duration_s"] <= 86400)  # cap at 24 hours
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

# Median session duration per adaptor, with IQR for error bars
stats = (
    plot_df.groupby("adaptors_list")["session_duration_s"]
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

print("\nTop 15 adaptors — median session duration:")
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

# Label each bar with the median value and session count
for bar, (adaptor, row) in zip(bars, stats.iterrows()):
    ax.text(
        bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
        f"{row['median']:.0f}s  (n={int(row['count'])})",
        va="center", ha="left", fontsize=8, color="#555555",
    )

ax.set_xlabel("Median Session Duration (seconds)", fontsize=11)
ax.set_title("Median Session Duration by Adaptor — Top 15 Most Used\n(error bars show interquartile range)",
             fontsize=14, fontweight="bold", pad=14)
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:.0f}s"))
ax.grid(axis="x", linestyle="--", alpha=0.4)
ax.spines[["top", "right"]].set_visible(False)
ax.set_xlim(left=0)

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts") / "session_length_v_adaptor_viz.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"\nChart saved to {out_path}")

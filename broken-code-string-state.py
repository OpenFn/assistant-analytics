import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("input_file", nargs="?", default="staff-chat-messages-filtered.csv")
args = parser.parse_args()

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv(args.input_file, low_memory=False)

# ── Parse timestamps ──────────────────────────────────────────────────────────
df["inserted_at_dt"] = pd.to_datetime(
    df["inserted_at"], format="%B %d, %Y, %H:%M:%S", errors="coerce"
)

# ── Find rows where code column contains )(state) ─────────────────────────────
matches = df[
    df["code"].notna() &
    df["code"].str.contains(r"\)\(state\)", regex=True)
].copy()

print(f"Total occurrences of ')(state)' in code column: {len(matches):,}")

# ── Count per month ───────────────────────────────────────────────────────────
matches["year_month"] = matches["inserted_at_dt"].dt.to_period("M")
monthly = matches.groupby("year_month").size().reset_index(name="count")
monthly["year_month_dt"] = monthly["year_month"].dt.to_timestamp()
monthly["month_label"] = monthly["year_month"].dt.strftime("%b %Y")

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13, 6))
fig.patch.set_facecolor("#F9FAFB")
ax.set_facecolor("#F9FAFB")

bars = ax.bar(
    range(len(monthly)),
    monthly["count"],
    color="#E74C3C",
    edgecolor="white",
    linewidth=0.6,
    width=0.65,
    zorder=3,
)

# Count labels above each bar
for bar, count in zip(bars, monthly["count"]):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + monthly["count"].max() * 0.015,
        str(count),
        ha="center", va="bottom",
        fontsize=9, fontweight="bold", color="#333333",
    )

ax.set_xticks(range(len(monthly)))
ax.set_xticklabels(monthly["month_label"], rotation=40, ha="right", fontsize=9)
ax.set_ylabel("Occurrences", fontsize=11)
ax.set_xlabel("Month", fontsize=11)
ax.set_title('Monthly occurances of ")(state)" in code', fontsize=14, fontweight="bold", pad=14)
ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
ax.set_axisbelow(True)
ax.spines[["top", "right"]].set_visible(False)
ax.set_xlim(-0.5, len(monthly) - 0.5)
ax.set_ylim(bottom=0)

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts") / "broken_code_string_state.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Chart saved to {out_path}")

print("\nMonthly breakdown:")
print(monthly[["year_month", "count"]].to_string(index=False))

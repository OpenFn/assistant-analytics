import argparse
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

# ── Args ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("input_file", nargs="?", default="staff-chat-messages-filtered.csv")
args = parser.parse_args()

# ── Load data ──────────────────────────────────────────────────────────────────
df = pd.read_csv(
    args.input_file,
    low_memory=False,
)

user_df = df[df["role"] == "user"].copy()

# ── Parse timestamps ───────────────────────────────────────────────────────────
DATE_FMT = "%B %d, %Y, %H:%M:%S"

user_df["inserted_at_dt"] = pd.to_datetime(
    user_df["inserted_at"], format=DATE_FMT, errors="coerce"
)
user_df["processing_completed_at_dt"] = pd.to_datetime(
    user_df["processing_completed_at"], format=DATE_FMT, errors="coerce"
)

# ── Compute processing time in seconds ────────────────────────────────────────
user_df["processing_seconds"] = (
    user_df["processing_completed_at_dt"] - user_df["inserted_at_dt"]
).dt.total_seconds()

# Keep only rows where both timestamps are present and duration is non-negative
timed_df = user_df[
    user_df["processing_seconds"].notna() & (user_df["processing_seconds"] >= 0)
].copy()

total_prompts_all = len(timed_df)

# ── Separate outliers (> 30 min = 1800 s) ────────────────────────────────────
OUTLIER_THRESHOLD = 1800  # seconds

outliers_df = timed_df[timed_df["processing_seconds"] > OUTLIER_THRESHOLD].copy()
plot_df     = timed_df[timed_df["processing_seconds"] <= OUTLIER_THRESHOLD].copy()

# Stats calculated from plot_df only (outliers excluded)
total_prompts = len(plot_df)
mean_time     = plot_df["processing_seconds"].mean()
median_time   = plot_df["processing_seconds"].median()

# ── Bin definitions ───────────────────────────────────────────────────────────
# Edges in seconds
bin_edges  = [0, 10, 20, 30, 40, 50, 60, 90, 120, 180, float("inf")]
bin_labels = [
    "0–10 s",
    "10–20 s",
    "20–30 s",
    "30–40 s",
    "40–50 s",
    "50–60 s",
    "60–90 s",
    "90–120 s",
    "2–3 min",
    "5+ min",   # catches 3–30 min band; labelled loosely per the spec
]

# We redefine the last visible bin to capture everything ≤ 1800 s
bin_edges_plot  = [0, 10, 20, 30, 40, 50, 60, 90, 120, 180, OUTLIER_THRESHOLD]

counts, _ = np.histogram(plot_df["processing_seconds"], bins=bin_edges_plot)

# ── Plot ───────────────────────────────────────────────────────────────────────
BLUE = "#2E6FD4"

# Use GridSpec: tall row for chart, short row for outlier note
has_outliers = len(outliers_df) > 0
height_ratios = [7, 1] if has_outliers else [1]
fig = plt.figure(figsize=(14, 9 if has_outliers else 7), constrained_layout=False)
gs  = gridspec.GridSpec(
    2 if has_outliers else 1, 1,
    height_ratios=height_ratios,
    hspace=0.55,
)
ax = fig.add_subplot(gs[0])

x_pos  = np.arange(len(bin_labels))
bar_w  = 0.65

bars = ax.bar(x_pos, counts, width=bar_w, color=BLUE, edgecolor="white",
              linewidth=0.8, zorder=3)

# Count labels above each bar
for bar, count in zip(bars, counts):
    if count > 0:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(counts) * 0.012,
            str(count),
            ha="center", va="bottom",
            fontsize=10, fontweight="bold", color="#1a1a2e",
        )

# ── Axes styling ──────────────────────────────────────────────────────────────
ax.set_xticks(x_pos)
ax.set_xticklabels(bin_labels, fontsize=10, rotation=20, ha="right")
ax.set_ylabel("Number of prompts", fontsize=11)
ax.set_xlabel("Processing time", fontsize=11, labelpad=8)
ax.yaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
ax.set_axisbelow(True)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# ── Title / stats header ──────────────────────────────────────────────────────
def fmt_time(seconds):
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} min"
    return f"{seconds/3600:.1f} h"

header = (
    f"Total user prompts (with timing): {total_prompts}    │    "
    f"Mean: {fmt_time(mean_time)}    │    "
    f"Median: {fmt_time(median_time)}"
)

fig.suptitle(
    "AI Assistant – Prompt Processing Time Distribution",
    fontsize=14, fontweight="bold", y=0.98,
)
ax.set_title(
    header,
    fontsize=10, color="#333333", pad=10,
    bbox=dict(boxstyle="round,pad=0.4", fc="#eef3fc", ec="#adc6f0", lw=1),
)

# ── Outlier footnote in its own dedicated axes row ────────────────────────────
if has_outliers:
    outlier_lines = []
    for _, row in outliers_df.iterrows():
        mins  = row["processing_seconds"] / 60
        label = row.get("id", "unknown")
        outlier_lines.append(f"  • id={label}  |  {mins:.1f} min")

    note = (
        f"⚠  {len(outliers_df)} prompt(s) omitted – processing time > 30 min:\n"
        + "\n".join(outlier_lines)
    )

    ax_note = fig.add_subplot(gs[1])
    ax_note.axis("off")
    ax_note.text(
        0.5, 0.5,
        note,
        ha="center", va="center",
        fontsize=8.5, color="#7a2020",
        family="monospace",
        transform=ax_note.transAxes,
        bbox=dict(boxstyle="round,pad=0.6", fc="#fff4f4", ec="#e8b4b4", lw=1),
    )

fig.subplots_adjust(top=0.84, bottom=0.05, left=0.07, right=0.97)

charts_dir = Path(r"C:\openfn\assistant-analytics\charts")
charts_dir.mkdir(exist_ok=True)
out_path = charts_dir / "response-time-histogram.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Saved → {out_path}")
print(f"\nSummary")
print(f"  Total prompts with timing data : {total_prompts}")
print(f"  Mean processing time           : {fmt_time(mean_time)}")
print(f"  Median processing time         : {fmt_time(median_time)}")
print(f"  Outliers (> 30 min) omitted    : {len(outliers_df)}")

"""
Staff Chat Message Visualisations
Produces three charts:
  1. Monthly message volume
  2. Top systems mentioned in user messages
  3. Session type split (job_code vs workflow_template)
"""

import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import re

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("input_file", nargs="?", default="staff-chat-messages-filtered.csv")
args = parser.parse_args()

INPUT_CSV  = args.input_file
OUTPUT_PNG = Path(r"C:\openfn\assistant-analytics\charts") / "monthly_volume_systems_used.png"

SYSTEMS = [
    "DHIS2", "OpenMRS", "WhatsApp", "Gmail", "OpenCRVS", "FHIR",
    "Salesforce", "Kobo", "SMS", "OpenSPP", "Google Sheets", "PostgreSQL",
    "MySQL", "ODK", "PowerBI", "Slack", "MOSIP", "MongoDB", "OpenAI",
    "Superset", "S3", "Azure", "AWS",
]
TOP_N_SYSTEMS = 15   # how many systems to show in bar chart

# Colour palette
COL_PRIMARY  = "#1D4ED8"   # blue-700
COL_ACCENT   = "#60A5FA"   # blue-400
COL_WARM     = "#93C5FD"   # blue-300
COL_MUTED    = "#DBEAFE"   # blue-100

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading data …")
df = pd.read_csv(INPUT_CSV, low_memory=False)
print(f"  {len(df):,} rows loaded")

# Parse timestamps – format: "September 10, 2024, 15:58:02"
df["inserted_at"] = pd.to_datetime(
    df["inserted_at"], format="%B %d, %Y, %H:%M:%S", errors="coerce"
)

# ── 1. Monthly message volume ─────────────────────────────────────────────────
monthly = (
    df.dropna(subset=["inserted_at"])
      .groupby(df["inserted_at"].dt.to_period("M"))
      .size()
      .reset_index(name="count")
)
monthly["month_label"] = monthly["inserted_at"].dt.strftime("%b %Y")

# ── 2. Top systems mentioned ──────────────────────────────────────────────────
user_content = df[df["role"] == "user"]["content"].dropna()
system_counts = {}
for system in SYSTEMS:
    n = user_content.str.contains(re.escape(system), case=False, na=False).sum()
    if n > 0:
        system_counts[system] = n

system_series = (
    pd.Series(system_counts)
      .sort_values(ascending=True)
      .tail(TOP_N_SYSTEMS)
)

# ── 3. Session type split ─────────────────────────────────────────────────────
session_col = "Ai Chat Sessions - Chat Session__session_type"
valid_types = ["job_code", "workflow_template"]
session_counts = (
    df[session_col]
      .where(df[session_col].isin(valid_types))
      .value_counts()
)

# ── Plot ──────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(18, 14))
fig.patch.set_facecolor("#F9FAFB")

# Shared title
fig.suptitle(
    "AI Workflow Assistant – Usage Analytics",
    fontsize=20, fontweight="bold", color="#111827", y=0.98
)

# Layout: 2 rows, 2 cols – chart 1 spans full top row
gs = fig.add_gridspec(2, 2, hspace=0.45, wspace=0.35,
                      left=0.07, right=0.96, top=0.92, bottom=0.07)

ax1 = fig.add_subplot(gs[0, :])   # monthly – full width
ax2 = fig.add_subplot(gs[1, 0])   # systems
ax3 = fig.add_subplot(gs[1, 1])   # session type

# ── Chart 1: Monthly message volume ──────────────────────────────────────────
x = range(len(monthly))
bars = ax1.bar(x, monthly["count"], color=COL_PRIMARY, alpha=0.85, width=0.65,
               zorder=3)

# Subtle grid
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
ax1.set_axisbelow(True)
ax1.yaxis.grid(True, linestyle="--", alpha=0.5, color="#D1D5DB")
ax1.set_facecolor("#F9FAFB")
ax1.spines[["top", "right", "left"]].set_visible(False)
ax1.spines["bottom"].set_color("#D1D5DB")
ax1.tick_params(axis="y", colors="#6B7280", labelsize=9)

# X-axis labels (show every label, rotate if many)
step = max(1, len(monthly) // 20)
tick_positions = list(range(0, len(monthly), step))
ax1.set_xticks(tick_positions)
ax1.set_xticklabels(
    [monthly["month_label"].iloc[i] for i in tick_positions],
    rotation=40, ha="right", fontsize=9, color="#374151"
)
ax1.set_xlim(-0.7, len(monthly) - 0.3)
ax1.set_ylabel("Messages", fontsize=10, color="#374151", labelpad=8)
ax1.set_title("Monthly Message Volume", fontsize=13, fontweight="bold",
              color="#111827", pad=10, loc="left")

# Peak annotation
peak_idx = monthly["count"].idxmax()
peak_val = monthly["count"].iloc[peak_idx]
ax1.annotate(
    f"Peak: {peak_val:,}",
    xy=(peak_idx, peak_val),
    xytext=(peak_idx + 0.5, peak_val * 1.05),
    arrowprops=dict(arrowstyle="->", color=COL_WARM, lw=1.5),
    fontsize=9, color=COL_WARM, fontweight="bold"
)

# ── Chart 2: Top systems ──────────────────────────────────────────────────────
colours = [COL_ACCENT if i >= len(system_series) - 3 else COL_PRIMARY
           for i in range(len(system_series))]
hbars = ax2.barh(system_series.index, system_series.values,
                 color=colours, alpha=0.85, height=0.65, zorder=3)

ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
ax2.set_axisbelow(True)
ax2.xaxis.grid(True, linestyle="--", alpha=0.5, color="#D1D5DB")
ax2.set_facecolor("#F9FAFB")
ax2.spines[["top", "right", "bottom"]].set_visible(False)
ax2.spines["left"].set_color("#D1D5DB")
ax2.tick_params(axis="x", colors="#6B7280", labelsize=9)
ax2.tick_params(axis="y", colors="#374151", labelsize=9.5)
ax2.set_xlabel("Mentions in user messages", fontsize=10, color="#374151", labelpad=8)
ax2.set_title(f"Top {len(system_series)} Systems Mentioned",
              fontsize=13, fontweight="bold", color="#111827", pad=10, loc="left")

# Value labels on bars
for bar in hbars:
    w = bar.get_width()
    ax2.text(w + max(system_series) * 0.01, bar.get_y() + bar.get_height() / 2,
             f"{int(w):,}", va="center", fontsize=8.5, color="#374151")

# ── Chart 3: Session type donut ───────────────────────────────────────────────
labels = session_counts.index.tolist()
sizes  = session_counts.values.tolist()
total  = sum(sizes)
pie_colours = [COL_PRIMARY, COL_ACCENT]

wedges, texts, autotexts = ax3.pie(
    sizes,
    labels=None,
    colors=pie_colours,
    autopct=lambda p: f"{p:.1f}%\n({int(round(p * total / 100)):,})",
    startangle=90,
    pctdistance=0.75,
    wedgeprops=dict(width=0.55, edgecolor="white", linewidth=2),
    textprops=dict(fontsize=10)
)
for at in autotexts:
    at.set_color("white")
    at.set_fontsize(10)
    at.set_fontweight("bold")

# Legend
legend_patches = [
    mpatches.Patch(color=pie_colours[i], label=f"{labels[i]}  ({sizes[i]:,})")
    for i in range(len(labels))
]
ax3.legend(handles=legend_patches, loc="lower center",
           bbox_to_anchor=(0.5, -0.12), frameon=False,
           fontsize=10, labelcolor="#374151")
ax3.set_title("Session Type Split", fontsize=13, fontweight="bold",
              color="#111827", pad=10, loc="left")

# ── Save ──────────────────────────────────────────────────────────────────────
OUTPUT_PNG.parent.mkdir(exist_ok=True)
plt.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved → {OUTPUT_PNG}")
plt.show()

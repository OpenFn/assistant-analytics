"""
Chat Message Analytics Visualisations
Produces three charts:
  1. Monthly user message volume
  2. Top systems/platforms mentioned in user messages
  3. Session type split (job_code vs workflow_template)
"""

import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import re
from collections import Counter

# ── Args ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("input_file", nargs="?", default="./staff-chat-messages-filtered.csv")
args = parser.parse_args()

# ── Load data ──────────────────────────────────────────────────────────────────
df = pd.read_csv(args.input_file)
df["date"] = pd.to_datetime(df["inserted_at"], format="%B %d, %Y, %H:%M:%S")
df["month"] = df["date"].dt.to_period("M")

user_msgs = df[df["role"] == "user"].copy()

# ── 1. Monthly message volume ──────────────────────────────────────────────────
monthly = user_msgs.groupby("month").size().sort_index()
months_str = [str(m) for m in monthly.index]

# ── 2. Top systems mentioned ───────────────────────────────────────────────────
SYSTEMS = [
    "OpenMRS",    "S3",         "DHIS2",      "Salesforce",
    "FHIR",       "Gmail",      "GitHub",     "OpenCRVS",
    "Webhook",    "Google Sheets", "PostgreSQL", "Sunbird",
    "Slack",      "MySQL",      "HL7",        "Twilio",
    "Google Drive", "QuickBooks", "PowerBI",  "MOSIP",
    "MongoDB",    "Outlook",    "Stripe",     "Shopify",
    "Airtable",   "Zoho",       "FTP",        "SFTP",
]

text = " ".join(user_msgs["content"].dropna().str.lower())
system_counts = {s: text.count(s.lower()) for s in SYSTEMS}
# Keep only those with at least one mention and take top 15
top_systems = sorted(
    [(s, c) for s, c in system_counts.items() if c > 0],
    key=lambda x: -x[1],
)[:15]
sys_labels, sys_values = zip(*top_systems)

# ── 3. Session type split ──────────────────────────────────────────────────────
session_col = "Ai Chat Sessions - Chat Session__session_type"
session_counts = df[session_col].value_counts()
session_labels = [s.replace("_", " ").title() for s in session_counts.index]
session_values = session_counts.values

# ── Colour palette ─────────────────────────────────────────────────────────────
PRIMARY   = "#4361EE"
SECONDARY = "#F72585"
ACCENT    = "#4CC9F0"
BG        = "#F8F9FC"
GRID      = "#E2E6EF"
TEXT      = "#1E2235"
PIE_COLS  = [PRIMARY, ACCENT, "#7209B7", "#3F37C9", "#480CA8"]

# ── Figure layout ──────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(18, 14), facecolor=BG)
fig.suptitle(
    "AI Workflow Assistant — Chat Analytics",
    fontsize=22, fontweight="bold", color=TEXT, y=0.97,
)

# Create grid: top row = monthly chart (full width), bottom row = bar + pie
gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.32,
                      top=0.91, bottom=0.07, left=0.06, right=0.97)
ax_line = fig.add_subplot(gs[0, :])   # spans both columns
ax_bar  = fig.add_subplot(gs[1, 0])
ax_pie  = fig.add_subplot(gs[1, 1])

def style_ax(ax, title):
    ax.set_facecolor(BG)
    ax.set_title(title, fontsize=13, fontweight="bold", color=TEXT, pad=10)
    ax.tick_params(colors=TEXT, labelsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRID)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

# ── Chart 1: Monthly message volume ───────────────────────────────────────────
style_ax(ax_line, "Monthly User Message Volume")

x = range(len(months_str))
ax_line.fill_between(x, monthly.values, alpha=0.15, color=PRIMARY, zorder=1)
ax_line.plot(x, monthly.values, color=PRIMARY, linewidth=2.5, zorder=2)
ax_line.scatter(x, monthly.values, color=PRIMARY, s=45, zorder=3, edgecolors="white", linewidths=1.2)

# Annotate every other point to avoid clutter
for i, (xi, yi) in enumerate(zip(x, monthly.values)):
    if i % 2 == 0:
        ax_line.annotate(
            str(yi), (xi, yi),
            textcoords="offset points", xytext=(0, 8),
            ha="center", fontsize=7.5, color=TEXT, fontweight="bold",
        )

# Format x-axis: show month labels every 2 months
step = max(1, len(months_str) // 10)
ax_line.set_xticks(list(x)[::step])
ax_line.set_xticklabels(months_str[::step], rotation=30, ha="right", fontsize=8.5)
ax_line.set_xlim(-0.5, len(months_str) - 0.5)
ax_line.set_ylabel("Messages", color=TEXT, fontsize=10)
ax_line.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

# ── Chart 2: Top systems mentioned ────────────────────────────────────────────
style_ax(ax_bar, "Top Systems Mentioned in Prompts")

# Gradient-like colours based on value magnitude
norm_vals = [v / sys_values[0] for v in sys_values]
colours = [PRIMARY if n > 0.5 else ACCENT if n > 0.25 else "#90E0EF" for n in norm_vals]

bars = ax_bar.barh(
    list(reversed(sys_labels)),
    list(reversed(sys_values)),
    color=list(reversed(colours)),
    edgecolor="white", linewidth=0.6,
    height=0.65, zorder=2,
)

for bar, val in zip(bars, reversed(sys_values)):
    ax_bar.text(
        bar.get_width() + sys_values[0] * 0.015,
        bar.get_y() + bar.get_height() / 2,
        str(val), va="center", ha="left",
        fontsize=8, color=TEXT, fontweight="bold",
    )

ax_bar.set_xlabel("Mention Count", color=TEXT, fontsize=10)
ax_bar.spines["bottom"].set_color(GRID)
ax_bar.tick_params(axis="y", labelsize=9)
ax_bar.set_xlim(0, sys_values[0] * 1.18)
ax_bar.xaxis.grid(False)
ax_bar.yaxis.grid(False)

# ── Chart 3: Session type split ────────────────────────────────────────────────
ax_pie.set_facecolor(BG)
ax_pie.set_title("Session Type Split", fontsize=13, fontweight="bold", color=TEXT, pad=10)

wedges, texts, autotexts = ax_pie.pie(
    session_values,
    labels=None,
    autopct="%1.1f%%",
    startangle=90,
    colors=PIE_COLS[:len(session_values)],
    pctdistance=0.72,
    wedgeprops={"linewidth": 2, "edgecolor": BG},
)
for at in autotexts:
    at.set_fontsize(13)
    at.set_fontweight("bold")
    at.set_color("white")

ax_pie.legend(
    wedges, [f"{l}  ({v:,})" for l, v in zip(session_labels, session_values)],
    loc="lower center", bbox_to_anchor=(0.5, -0.12),
    fontsize=9.5, frameon=False, labelcolor=TEXT,
)

# Draw a white circle in the middle for a donut look
centre = plt.Circle((0, 0), 0.48, color=BG)
ax_pie.add_patch(centre)
total = sum(session_values)
ax_pie.text(0, 0, f"{total:,}\nsessions", ha="center", va="center",
            fontsize=11, fontweight="bold", color=TEXT)

# ── Save ───────────────────────────────────────────────────────────────────────
charts_dir = Path(r"C:\openfn\assistant-analytics\charts")
charts_dir.mkdir(exist_ok=True)
out_path = charts_dir / "chat_analytics.png"
plt.savefig(out_path, dpi=160, bbox_inches="tight", facecolor=BG)
print(f"Saved to {out_path}")

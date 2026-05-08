from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv(
    r"C:\openfn\assistant-analytics\data\anthropic_api_session_parsed_analysis.csv",
    low_memory=False,
)

COLUMNS = [
    "problem_resolved?",
    "user_frustrated?",
    "user_rude?",
    "user_confused?",
    "assistant_pushback_clarify?",
    "assistant_pushback_impossible?",
    "assistant_admit_mistake?",
    "assistant_apologise?",
    "user_apologise?",
    "user_tone?",
    "user_writing_style?",
    "language?",
    "session_purpose?",
]

VALUE_COLOURS = {
    "YES":       "#2ECC71",
    "NO":        "#E74C3C",
    "UNSURE":    "#BDC3C7",
    "FORMAL":    "#3498DB",
    "CASUAL":    "#F39C12",
    "CONCISE":   "#9B59B6",
    "VERBOSE":   "#1ABC9C",
    "BUILDING":  "#2E86AB",
    "DEBUGGING": "#E67E22",
}
FALLBACK_COLOURS = [
    "#5DADE2", "#A569BD", "#48C9B0", "#F5CBA7", "#85929E",
    "#F1948A", "#82E0AA", "#F8C471", "#AED6F1", "#D7BDE2",
]

def get_colour(value, fallback_idx):
    return VALUE_COLOURS.get(str(value).upper(), FALLBACK_COLOURS[fallback_idx % len(FALLBACK_COLOURS)])

# Valid answers per column derived from claude_prompt.txt
YES_NO_UNSURE = {"YES", "NO", "UNSURE"}
VALID_VALUES = {
    "problem_resolved?":              YES_NO_UNSURE,
    "user_frustrated?":               YES_NO_UNSURE,
    "user_rude?":                     YES_NO_UNSURE,
    "user_confused?":                 YES_NO_UNSURE,
    "assistant_pushback_clarify?":    YES_NO_UNSURE,
    "assistant_pushback_impossible?": YES_NO_UNSURE,
    "assistant_admit_mistake?":       YES_NO_UNSURE,
    "assistant_apologise?":           YES_NO_UNSURE,
    "user_apologise?":                YES_NO_UNSURE,
    "user_tone?":                     {"FORMAL", "CASUAL", "UNSURE"},
    "user_writing_style?":            {"CONCISE", "VERBOSE"},
    "session_purpose?":               {"BUILDING", "DEBUGGING"},
    # language? is open-ended — filter only obviously malformed values
    "language?":                      None,
}

# ── Build percentage tables per column ───────────────────────────────────────
col_data = {}
for col in COLUMNS:
    if col not in df.columns:
        print(f"Warning: column '{col}' not found, skipping.")
        continue
    series = df[col].astype(str).str.strip().str.upper().replace("NAN", "UNSURE")
    valid = VALID_VALUES.get(col)
    if valid is not None:
        before = len(series)
        series = series[series.isin(valid)]
        dropped = before - len(series)
        if dropped:
            print(f"  {col}: dropped {dropped} invalid rows")
    else:
        # language?: keep only plausible language name strings (letters/spaces, ≤30 chars)
        # and exclude values that are valid answers to other columns
        NOT_LANGUAGES = {"YES", "NO", "UNSURE", "FORMAL", "CASUAL", "CONCISE", "VERBOSE", "BUILDING", "DEBUGGING"}
        series = series[
            series.str.match(r"^[A-Z][A-Z \-]{0,29}$", na=False) &
            ~series.isin(NOT_LANGUAGES)
        ]
    col_data[col] = series.value_counts(normalize=True) * 100

# ── Plot ──────────────────────────────────────────────────────────────────────
cols = list(col_data.keys())
n = len(cols)

fig, ax = plt.subplots(figsize=(22, max(6, n * 0.85 + 2)))
fig.patch.set_facecolor("#F8F9FA")
ax.set_facecolor("#F8F9FA")

# Bars occupy 0–100, inline legends start at 103
LEGEND_START = 103
SWATCH_W = 1.5
SWATCH_H = 0.35
CHAR_W = 1.2   # approximate x-units per character

y_positions = list(range(n))

for y, col in zip(y_positions, cols):
    counts = col_data[col].sort_values(ascending=False)
    left = 0.0
    x_leg = LEGEND_START

    for idx, (value, pct) in enumerate(counts.items()):
        colour = get_colour(value, idx)

        # Bar segment
        ax.barh(y, pct, left=left, height=0.6, color=colour, edgecolor="white", linewidth=0.5)
        if pct >= 5:
            ax.text(
                left + pct / 2, y, f"{pct:.0f}%",
                va="center", ha="center", fontsize=8,
                color="white" if pct > 15 else "#333333", fontweight="bold",
            )
        left += pct

        # Inline swatch + label to the right of the bar
        ax.add_patch(mpatches.FancyBboxPatch(
            (x_leg, y - SWATCH_H / 2), SWATCH_W, SWATCH_H,
            boxstyle="square,pad=0", color=colour,
        ))
        label = f"{value} ({pct:.0f}%)"
        ax.text(
            x_leg + SWATCH_W + 0.5, y, label,
            va="center", ha="left", fontsize=7.5, color="#222222",
        )
        x_leg += SWATCH_W + 0.5 + len(label) * CHAR_W + 1.5

ax.set_yticks(y_positions)
ax.set_yticklabels(cols, fontsize=10)
ax.set_xlabel("Percentage (%)", fontsize=11)
ax.set_xlim(0, 200)
ax.set_xticks(range(0, 101, 10))
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}%" if x <= 100 else ""))
ax.set_title("Session Analysis — Percentage Breakdown by Category", fontsize=14, fontweight="bold", pad=14)
ax.grid(axis="x", linestyle="--", alpha=0.4)
ax.spines[["top", "right"]].set_visible(False)
ax.axvline(x=100, color="#cccccc", linewidth=0.8, linestyle="--")

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts\comprehensive_tone_analysis_viz.png")
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Chart saved to {out_path}")

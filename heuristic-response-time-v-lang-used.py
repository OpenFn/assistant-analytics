import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from langdetect import detect, LangDetectException

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument(
    "input_file",
    nargs="?",
    default=r"C:\openfn\assistant-analytics\data\staff-chat-messages-filtered.csv",
)
args = parser.parse_args()

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv(args.input_file, low_memory=False)
user_df = df[df["role"] == "user"].copy()

# ── Parse timestamps & compute response time ──────────────────────────────────
date_format = "%B %d, %Y, %H:%M:%S"
user_df["inserted_at_dt"] = pd.to_datetime(user_df["inserted_at"], format=date_format, errors="coerce")
user_df["processing_completed_at_dt"] = pd.to_datetime(user_df["processing_completed_at"], format=date_format, errors="coerce")
user_df["processing_time_s"] = (
    user_df["processing_completed_at_dt"] - user_df["inserted_at_dt"]
).dt.total_seconds()

user_df = user_df[
    user_df["processing_time_s"].notna() &
    (user_df["processing_time_s"] >= 0) &
    (user_df["processing_time_s"] <= 3600)
].copy()

# ── Detect natural language of each prompt ────────────────────────────────────
SUPPORTED = {"en": "English", "fr": "French", "es": "Spanish"}

def detect_language(text):
    if not isinstance(text, str) or len(text.strip()) < 10:
        return "Other"
    try:
        code = detect(text)
        return SUPPORTED.get(code, "Other")
    except LangDetectException:
        return "Other"

print("Detecting languages … (this may take a moment)")
user_df["language"] = user_df["content"].apply(detect_language)
print("Done.")

# ── Summarise ─────────────────────────────────────────────────────────────────
lang_counts = user_df["language"].value_counts()
print("\nLanguage breakdown:")
print(lang_counts.to_string())

# Only plot languages with enough data points
min_samples = 5
plot_langs = lang_counts[lang_counts >= min_samples].index.tolist()
plot_df = user_df[user_df["language"].isin(plot_langs)].copy()

# Order by median response time ascending
lang_order = (
    plot_df.groupby("language")["processing_time_s"]
    .median()
    .sort_values(ascending=True)
    .index.tolist()
)

# ── Plot: horizontal box plot ─────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13, max(5, len(lang_order) * 0.7 + 2)))

data = [plot_df.loc[plot_df["language"] == lang, "processing_time_s"].values for lang in lang_order]

bp = ax.boxplot(
    data,
    vert=False,
    patch_artist=True,
    widths=0.55,
    medianprops=dict(color="white", linewidth=2),
    whiskerprops=dict(color="#555555"),
    capprops=dict(color="#555555"),
    flierprops=dict(marker="o", markersize=3, alpha=0.3, markeredgewidth=0),
)

colours = ["#2E86AB", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6",
           "#1ABC9C", "#E67E22", "#3498DB", "#E91E63", "#00BCD4",
           "#FF5722", "#8BC34A"]
for patch, colour in zip(bp["boxes"], colours[:len(lang_order)]):
    patch.set_facecolor(colour)
    patch.set_alpha(0.75)
for flier, colour in zip(bp["fliers"], colours[:len(lang_order)]):
    flier.set_markerfacecolor(colour)

# Annotate with sample count
for i, lang in enumerate(lang_order, start=1):
    n = lang_counts[lang]
    ax.text(
        ax.get_xlim()[1] if ax.get_xlim()[1] > 0 else 200,
        i, f"n={n}",
        va="center", ha="left", fontsize=8, color="#555555",
    )

ax.set_yticks(range(1, len(lang_order) + 1))
ax.set_yticklabels(lang_order, fontsize=10)
ax.set_xlabel("Response Time (seconds)", fontsize=11)
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:.0f}s"))
ax.set_title("Response Time vs Prompt Language", fontsize=14, fontweight="bold", pad=14)
ax.grid(axis="x", linestyle="--", alpha=0.4)
ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts") / "heuristic_response_time_vs_language_used.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"\nChart saved to {out_path}")

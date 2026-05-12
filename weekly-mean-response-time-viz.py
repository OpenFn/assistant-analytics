import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("input_file", nargs="?", default=r"C:\openfn\assistant-analytics\data\staff-chat-messages-filtered.csv")
args = parser.parse_args()

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv(args.input_file, low_memory=False)
user_df = df[df['role'] == 'user'].copy()

# ── Parse timestamps ──────────────────────────────────────────────────────────
date_format = '%B %d, %Y, %H:%M:%S'
user_df['inserted_at_dt'] = pd.to_datetime(user_df['inserted_at'], format=date_format, errors='coerce')
user_df['processing_completed_at_dt'] = pd.to_datetime(user_df['processing_completed_at'], format=date_format, errors='coerce')

user_df['processing_time_s'] = (
    user_df['processing_completed_at_dt'] - user_df['inserted_at_dt']
).dt.total_seconds()

user_df = user_df[
    (user_df['processing_time_s'].notna()) &
    (user_df['processing_time_s'] >= 0) &
    (user_df['processing_time_s'] <= 3600)
]

# ── Group by week ─────────────────────────────────────────────────────────────
user_df['week'] = user_df['inserted_at_dt'].dt.to_period('W')
weekly_avg = user_df.groupby('week')['processing_time_s'].mean().reset_index()
weekly_avg['week_dt'] = weekly_avg['week'].dt.to_timestamp()

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(16, 6))

ax.plot(
    weekly_avg['week_dt'],
    weekly_avg['processing_time_s'],
    marker='o',
    linewidth=2,
    markersize=4,
    color='#2E86AB',
    markerfacecolor='white',
    markeredgewidth=1.5,
)

ax.set_title('Weekly Mean User Prompt Processing Time', fontsize=15, fontweight='bold', pad=15)
ax.set_xlabel('Week', fontsize=11)
ax.set_ylabel('Mean Processing Time (seconds)', fontsize=11)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:.0f}s'))
ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d %b %Y'))
ax.xaxis.set_major_locator(plt.matplotlib.dates.WeekdayLocator(byweekday=0))
plt.xticks(rotation=90, ha='right')
ax.grid(axis='y', linestyle='--', alpha=0.5)
ax.set_ylim(bottom=0, top=60)
ax.spines[['top', 'right']].set_visible(False)

# Annotate points that exceed the y cap
for _, row in weekly_avg.iterrows():
    if row['processing_time_s'] > 60:
        ax.annotate(
            f"{row['processing_time_s']:.0f}s",
            (row['week_dt'], 60),
            textcoords='offset points', xytext=(0, 6),
            ha='center', fontsize=7, color='#E74C3C', fontweight='bold',
        )
        ax.plot(row['week_dt'], 60, marker='^', color='#E74C3C', markersize=6)

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts") / "weekly_mean_response_time.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"Chart saved to {out_path}")

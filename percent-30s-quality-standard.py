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

# Filter to user messages only
user_df = df[df['role'] == 'user'].copy()

# ── Parse timestamps ──────────────────────────────────────────────────────────
date_format = '%B %d, %Y, %H:%M:%S'
user_df['inserted_at_dt'] = pd.to_datetime(user_df['inserted_at'], format=date_format, errors='coerce')
user_df['processing_completed_at_dt'] = pd.to_datetime(user_df['processing_completed_at'], format=date_format, errors='coerce')

# ── Compute processing time ───────────────────────────────────────────────────
user_df['processing_time_s'] = (
    user_df['processing_completed_at_dt'] - user_df['inserted_at_dt']
).dt.total_seconds()

# Drop rows where either timestamp is missing, processing time is negative,
# or is a clear outlier (> 1 hour, likely corrupt data)
user_df = user_df[
    (user_df['processing_time_s'].notna()) &
    (user_df['processing_time_s'] >= 0) &
    (user_df['processing_time_s'] <= 3600)
].copy()

# ── Group by week ─────────────────────────────────────────────────────────────
user_df['week'] = user_df['inserted_at_dt'].dt.to_period('W')
weekly = user_df.groupby('week')['processing_time_s'].agg(
    total='count',
    over_30=lambda x: (x > 30).sum(),
).reset_index()
weekly['pct_over_30'] = weekly['over_30'] / weekly['total'] * 100
weekly['week_dt'] = weekly['week'].dt.to_timestamp()

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(16, 6))

ax.plot(
    weekly['week_dt'],
    weekly['pct_over_30'],
    marker='o',
    linewidth=2,
    markersize=4,
    color='#E74C3C',
    markerfacecolor='white',
    markeredgewidth=1.5,
)

ax.axhline(y=50, color='#888888', linestyle='--', linewidth=1, alpha=0.7, label='50% threshold')

ax.set_title('Weekly % of Responses Over 30s', fontsize=15, fontweight='bold', pad=15)
ax.set_xlabel('Week', fontsize=11)
ax.set_ylabel('% of Responses > 30s', fontsize=11)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:.0f}%'))
ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d %b %Y'))
ax.xaxis.set_major_locator(plt.matplotlib.dates.WeekdayLocator(byweekday=0))
plt.xticks(rotation=90, ha='right')
ax.grid(axis='y', linestyle='--', alpha=0.5)
ax.set_ylim(0, 100)
ax.spines[['top', 'right']].set_visible(False)
ax.legend(fontsize=10, framealpha=0.9)

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts") / "percent_30s_quality_standard_viz.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"Chart saved to {out_path}")
print(f"\nWeekly breakdown:")
print(weekly[['week', 'total', 'over_30', 'pct_over_30']].to_string(index=False))

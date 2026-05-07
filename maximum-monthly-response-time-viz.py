import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("input_file", nargs="?", default="staff-chat-messages-filtered.csv")
args = parser.parse_args()

# Load data
df = pd.read_csv(args.input_file, low_memory=False)

# Filter to user messages only
user_df = df[df['role'] == 'user'].copy()

# Parse timestamps
date_format = '%B %d, %Y, %H:%M:%S'
user_df['inserted_at_dt'] = pd.to_datetime(user_df['inserted_at'], format=date_format, errors='coerce')
user_df['processing_completed_at_dt'] = pd.to_datetime(user_df['processing_completed_at'], format=date_format, errors='coerce')

# Compute processing time in seconds
user_df['processing_time_s'] = (
    user_df['processing_completed_at_dt'] - user_df['inserted_at_dt']
).dt.total_seconds()

# Drop rows where either timestamp is missing, processing time is negative,
# or is a clear outlier (> 1 hour, likely corrupt data)
user_df = user_df[
    (user_df['processing_time_s'].notna()) &
    (user_df['processing_time_s'] >= 0) &
    (user_df['processing_time_s'] <= 3600)
]

# Group by year-month and compute mean + top 5 values
user_df['year_month'] = user_df['inserted_at_dt'].dt.to_period('M')

def nth_largest(n):
    return lambda x: x.nlargest(n).iloc[-1] if len(x) >= n else None

monthly = user_df.groupby('year_month')['processing_time_s'].agg(
    mean='mean',
    top1=nth_largest(1),
    top2=nth_largest(2),
    top3=nth_largest(3),
    top4=nth_largest(4),
    top5=nth_largest(5),
).reset_index()
monthly['year_month_dt'] = monthly['year_month'].dt.to_timestamp()

# Plot
fig, ax = plt.subplots(figsize=(13, 6))

lines = [
    ('top1', 'Maximum (1st)',  '#C0392B', 'D', 2.2),
    ('top2', '2nd highest',    '#E67E22', 's', 1.8),
    ('top3', '3rd highest',    '#F1C40F', '^', 1.8),
    ('top4', '4th highest',    '#95A5A6', 'v', 1.8),
    ('top5', '5th highest',    '#BDC3C7', 'P', 1.8),
    ('mean', 'Monthly mean',   '#2E86AB', 'o', 2.2),
]

for col, label, color, marker, lw in lines:
    series = monthly[['year_month_dt', col]].dropna()
    ax.plot(
        series['year_month_dt'],
        series[col],
        marker=marker,
        linewidth=lw,
        markersize=6,
        color=color,
        markerfacecolor='white',
        markeredgewidth=2,
        label=label,
    )

ax.set_title('Monthly Maximum Response Time', fontsize=15, fontweight='bold', pad=15)
ax.set_xlabel('Month', fontsize=11)
ax.set_ylabel('Processing Time (seconds)', fontsize=11)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:.0f}s'))
ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %Y'))
plt.xticks(rotation=45, ha='right')
ax.grid(axis='y', linestyle='--', alpha=0.5)
ax.set_ylim(bottom=0)
ax.spines[['top', 'right']].set_visible(False)
ax.legend(fontsize=10, framealpha=0.9)

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts") / "maximum_monthly_response_time.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"Chart saved to {out_path}")
print("\nMonthly values (seconds):")
print(monthly[['year_month', 'mean', 'top1', 'top2', 'top3', 'top4', 'top5']].to_string(index=False))

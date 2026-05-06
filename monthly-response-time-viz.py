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

# Group by year-month and compute average processing time
user_df['year_month'] = user_df['inserted_at_dt'].dt.to_period('M')
monthly_avg = user_df.groupby('year_month')['processing_time_s'].mean().reset_index()
monthly_avg['year_month_dt'] = monthly_avg['year_month'].dt.to_timestamp()
monthly_avg['avg_minutes'] = monthly_avg['processing_time_s'] / 60

# Plot
fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(
    monthly_avg['year_month_dt'],
    monthly_avg['avg_minutes'],
    marker='o',
    linewidth=2,
    markersize=6,
    color='#2E86AB',
    markerfacecolor='white',
    markeredgewidth=2,
)

# Annotate each point with its value
for _, row in monthly_avg.iterrows():
    ax.annotate(
        f"{row['avg_minutes']:.1f}m",
        (row['year_month_dt'], row['avg_minutes']),
        textcoords='offset points',
        xytext=(0, 10),
        ha='center',
        fontsize=8,
        color='#444',
    )

ax.set_title('Monthly Average User Prompt Processing Time', fontsize=15, fontweight='bold', pad=15)
ax.set_xlabel('Month', fontsize=11)
ax.set_ylabel('Average Processing Time (minutes)', fontsize=11)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:.1f}m'))
ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %Y'))
plt.xticks(rotation=45, ha='right')
ax.grid(axis='y', linestyle='--', alpha=0.5)
ax.set_ylim(bottom=0)
ax.spines[['top', 'right']].set_visible(False)

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts") / "monthly_response_time.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"Chart saved to {out_path}")
print("\nMonthly averages:")
print(monthly_avg[['year_month', 'avg_minutes']].rename(columns={'avg_minutes': 'avg_minutes'}).to_string(index=False))

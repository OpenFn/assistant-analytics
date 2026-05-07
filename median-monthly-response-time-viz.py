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

# Group by year-month and compute median processing time
user_df['year_month'] = user_df['inserted_at_dt'].dt.to_period('M')
monthly_median = user_df.groupby('year_month')['processing_time_s'].median().reset_index()
monthly_median['year_month_dt'] = monthly_median['year_month'].dt.to_timestamp()

# Plot
fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(
    monthly_median['year_month_dt'],
    monthly_median['processing_time_s'],
    marker='o',
    linewidth=2,
    markersize=6,
    color='#2E86AB',
    markerfacecolor='white',
    markeredgewidth=2,
)

# Annotate each point with its value
for _, row in monthly_median.iterrows():
    ax.annotate(
        f"{row['processing_time_s']:.1f}s",
        (row['year_month_dt'], row['processing_time_s']),
        textcoords='offset points',
        xytext=(0, 10),
        ha='center',
        fontsize=8,
        color='#444',
    )

ax.set_title('Monthly Median User Prompt Processing Time', fontsize=15, fontweight='bold', pad=15)
ax.set_xlabel('Month', fontsize=11)
ax.set_ylabel('Median Processing Time (seconds)', fontsize=11)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:.0f}s'))
ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %Y'))
plt.xticks(rotation=45, ha='right')
ax.grid(axis='y', linestyle='--', alpha=0.5)
ax.set_ylim(bottom=0)
ax.spines[['top', 'right']].set_visible(False)

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts") / "median_monthly_response_time.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"Chart saved to {out_path}")
print("\nMonthly medians:")
print(monthly_median[['year_month', 'processing_time_s']].to_string(index=False))

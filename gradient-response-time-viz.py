import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.colors as mcolors
import numpy as np

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
].copy()

user_df = user_df.sort_values('inserted_at_dt')

# Count of values > 300s per month for annotations
user_df['year_month'] = user_df['inserted_at_dt'].dt.to_period('M')
outliers_300 = (
    user_df[user_df['processing_time_s'] > 300]
    .groupby('year_month')
    .size()
    .reset_index(name='count')
)
outliers_300['month_mid'] = outliers_300['year_month'].dt.to_timestamp() + pd.Timedelta(days=15)

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 6))

# Green → red below 60s, red → purple above 60s.
# TwoSlopeNorm maps vcenter (60s) to 0.5, so the colormap midpoint = red.
cmap = mcolors.LinearSegmentedColormap.from_list(
    "rtyg", ["#00CC44", "#FFEE00", "#FF2800"]
)
norm = mcolors.Normalize(vmin=0, vmax=60, clip=True)

scatter = ax.scatter(
    user_df['inserted_at_dt'],
    user_df['processing_time_s'],
    c=user_df['processing_time_s'],
    cmap=cmap,
    norm=norm,
    s=12,
    alpha=0.6,
    linewidths=0,
)

cbar = plt.colorbar(scatter, ax=ax, pad=0.02)
cbar.set_label('Response time (seconds)', fontsize=10)
cbar.ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:.0f}s'))

ax.set_title('Response Time Distribution', fontsize=15, fontweight='bold', pad=15)
ax.set_xlabel('Date', fontsize=11)
ax.set_ylabel('Response Time (seconds)', fontsize=11)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:.0f}s'))
ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %Y'))
plt.xticks(rotation=45, ha='right')
ax.set_ylim(bottom=0, top=100)

# Annotate each month with count of values > 300s
for _, row in outliers_300.iterrows():
    ax.text(
        row['month_mid'], 97,
        f"{row['count']} >300s",
        ha='center', va='top',
        fontsize=7, color='#7D3C98', fontweight='bold',
    )

ax.text(1.0, 1.01, 'Y axis capped at 100s — some outliers not shown',
        transform=ax.transAxes, ha='right', va='bottom',
        fontsize=8, color='#888888', style='italic')
ax.grid(axis='y', linestyle='--', alpha=0.4)
ax.spines[['top', 'right']].set_visible(False)

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts") / "gradient_response_time.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"Chart saved to {out_path}")
print(f"\nTotal data points plotted: {len(user_df):,}")

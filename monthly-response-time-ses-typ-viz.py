import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("input_file", nargs="?", default="staff-chat-messages-filtered.csv")
args = parser.parse_args()

# Load data
df = pd.read_csv(args.input_file, low_memory=False)

# Parse inserted_at — full dataset, no date cutoff
date_format = '%B %d, %Y, %H:%M:%S'
df['inserted_at_dt'] = pd.to_datetime(df['inserted_at'], format=date_format, errors='coerce')

# Filter to user messages in the two session types of interest
session_types = ['job_code', 'workflow_template']
user_df = df[
    (df['role'] == 'user') &
    (df['Ai Chat Sessions - Chat Session__session_type'].isin(session_types))
].copy()

# Parse processing_completed_at and compute processing time in seconds
user_df['processing_completed_at_dt'] = pd.to_datetime(
    user_df['processing_completed_at'], format=date_format, errors='coerce'
)
user_df['processing_time_s'] = (
    user_df['processing_completed_at_dt'] - user_df['inserted_at_dt']
).dt.total_seconds()

# Drop missing / negative / outlier values (> 1 hour likely corrupt)
user_df = user_df[
    user_df['processing_time_s'].notna() &
    (user_df['processing_time_s'] >= 0) &
    (user_df['processing_time_s'] <= 3600)
]

# Monthly average per session type
user_df['year_month'] = user_df['inserted_at_dt'].dt.to_period('M')
monthly = (
    user_df
    .groupby(['Ai Chat Sessions - Chat Session__session_type', 'year_month'])['processing_time_s']
    .mean()
    .reset_index()
)
monthly['avg_seconds'] = monthly['processing_time_s']
monthly['year_month_dt'] = monthly['year_month'].dt.to_timestamp()

# Pivot for easy plotting
pivot = monthly.pivot(index='year_month_dt', columns='Ai Chat Sessions - Chat Session__session_type', values='avg_seconds')

# Plot
fig, ax = plt.subplots(figsize=(13, 6))

colors = {'job_code': '#2E86AB', 'workflow_template': '#E84855'}
labels = {'job_code': 'Job Code', 'workflow_template': 'Workflow Template'}
markers = {'job_code': 'o', 'workflow_template': 's'}

for col in session_types:
    if col not in pivot.columns:
        continue
    series = pivot[col].dropna()
    ax.plot(
        series.index, series.values,
        marker=markers[col], linewidth=2.2, markersize=7,
        color=colors[col], label=labels[col],
        markerfacecolor='white', markeredgewidth=2,
    )
    for x, y in zip(series.index, series.values):
        ax.annotate(
            f'{y:.0f}s',
            (x, y),
            textcoords='offset points',
            xytext=(0, 10),
            ha='center', fontsize=8, color=colors[col],
        )

ax.set_title('Monthly Average User Prompt Processing Time\nby Session Type (Full Dataset)',
             fontsize=14, fontweight='bold', pad=14)
ax.set_xlabel('Month', fontsize=11)
ax.set_ylabel('Average Processing Time (seconds)', fontsize=11)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:.0f}s'))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax.xaxis.set_major_locator(mdates.MonthLocator())
plt.xticks(rotation=45, ha='right')
ax.legend(fontsize=11, framealpha=0.9)
ax.grid(axis='y', linestyle='--', alpha=0.45)
ax.set_ylim(bottom=0)
ax.spines[['top', 'right']].set_visible(False)

# ── Annotation: Systems merged ────────────────────────────────────────────────
import datetime
merge_date = datetime.date(2026, 2, 19)
ax.axvline(x=merge_date, color='#666666', linestyle='--', linewidth=1.5, zorder=4)
ax.text(merge_date, ax.get_ylim()[1], 'Systems merged',
        rotation=90, va='top', ha='right', fontsize=9, color='#666666')

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts") / "monthly_response_time_by_session_type.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"Chart saved to {out_path}")

print('\nMonthly averages (seconds):')
print(pivot.to_string())

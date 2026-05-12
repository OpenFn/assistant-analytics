import argparse
import datetime
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("input_file", nargs="?", default=r"C:\openfn\assistant-analytics\data\staff-chat-messages-filtered.csv")
args = parser.parse_args()

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv(args.input_file, low_memory=False)

date_format = '%B %d, %Y, %H:%M:%S'
df['inserted_at_dt'] = pd.to_datetime(df['inserted_at'], format=date_format, errors='coerce')

session_types = ['job_code', 'workflow_template']
user_df = df[
    (df['role'] == 'user') &
    (df['Ai Chat Sessions - Chat Session__session_type'].isin(session_types))
].copy()

user_df['processing_completed_at_dt'] = pd.to_datetime(
    user_df['processing_completed_at'], format=date_format, errors='coerce'
)
user_df['processing_time_s'] = (
    user_df['processing_completed_at_dt'] - user_df['inserted_at_dt']
).dt.total_seconds()

user_df = user_df[
    user_df['processing_time_s'].notna() &
    (user_df['processing_time_s'] >= 0) &
    (user_df['processing_time_s'] <= 3600)
]

# ── Group by week ─────────────────────────────────────────────────────────────
user_df['week'] = user_df['inserted_at_dt'].dt.to_period('W')
weekly = (
    user_df
    .groupby(['Ai Chat Sessions - Chat Session__session_type', 'week'])['processing_time_s']
    .median()
    .reset_index()
)
weekly['week_dt'] = weekly['week'].dt.to_timestamp()

pivot = weekly.pivot(index='week_dt', columns='Ai Chat Sessions - Chat Session__session_type', values='processing_time_s')

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(18, 6))

colors  = {'job_code': '#2E86AB', 'workflow_template': '#E84855'}
labels  = {'job_code': 'Job Code', 'workflow_template': 'Workflow Template'}
markers = {'job_code': 'o', 'workflow_template': 's'}

for col in session_types:
    if col not in pivot.columns:
        continue
    series = pivot[col].dropna()
    ax.plot(
        series.index, series.values,
        marker=markers[col], linewidth=2, markersize=4,
        color=colors[col], label=labels[col],
        markerfacecolor='white', markeredgewidth=1.5,
    )

merge_date = datetime.date(2026, 2, 19)
ax.axvline(x=merge_date, color='#666666', linestyle='--', linewidth=1.5, zorder=4)
ax.text(merge_date, 88, 'Systems merged',
        rotation=90, va='top', ha='right', fontsize=9, color='#666666')

ax.set_title('Weekly Median User Prompt Processing Time by Session Type',
             fontsize=14, fontweight='bold', pad=14)
ax.set_xlabel('Week', fontsize=11)
ax.set_ylabel('Median Processing Time (seconds)', fontsize=11)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:.0f}s'))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b %Y'))
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0))
plt.xticks(rotation=90, ha='right')
ax.legend(fontsize=11, framealpha=0.9)
ax.grid(axis='y', linestyle='--', alpha=0.45)
ax.set_ylim(bottom=0, top=90)
ax.spines[['top', 'right']].set_visible(False)

# Annotate points that exceed the y cap
for col in session_types:
    if col not in pivot.columns:
        continue
    series = pivot[col].dropna()
    for x, y in zip(series.index, series.values):
        if y > 90:
            ax.annotate(
                f"{y:.0f}s",
                (x, 90),
                textcoords='offset points', xytext=(0, 6),
                ha='center', fontsize=7, color=colors[col], fontweight='bold',
            )
            ax.plot(x, 90, marker='^', color=colors[col], markersize=6)

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts") / "weekly_median_response_time_by_session_type.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"Chart saved to {out_path}")

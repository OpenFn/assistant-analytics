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

# ── Compute response time ─────────────────────────────────────────────────────
user_df['processing_time_s'] = (
    user_df['processing_completed_at_dt'] - user_df['inserted_at_dt']
).dt.total_seconds()

# ── Compute prompt character length ──────────────────────────────────────────
user_df['prompt_length'] = user_df['content'].fillna('').str.len()

# ── Filter valid rows ─────────────────────────────────────────────────────────
user_df = user_df[
    (user_df['processing_time_s'].notna()) &
    (user_df['processing_time_s'] >= 0) &
    (user_df['processing_time_s'] <= 3600) &
    (user_df['prompt_length'] > 0)
].copy()

print(f"Data points plotted: {len(user_df):,}")
print(f"Prompt length — min: {user_df['prompt_length'].min():,}  max: {user_df['prompt_length'].max():,}  median: {user_df['prompt_length'].median():,.0f}")
print(f"Response time — min: {user_df['processing_time_s'].min():.1f}s  max: {user_df['processing_time_s'].max():.1f}s  median: {user_df['processing_time_s'].median():.1f}s")

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13, 7))

ax.scatter(
    user_df['prompt_length'],
    user_df['processing_time_s'],
    s=8,
    alpha=0.35,
    color='#2E86AB',
    linewidths=0,
)

ax.set_title('Response Time vs Prompt Character Length', fontsize=15, fontweight='bold', pad=15)
ax.set_xlabel('Prompt Length (characters)', fontsize=11)
ax.set_ylabel('Response Time (seconds)', fontsize=11)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:.0f}s'))
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
ax.grid(linestyle='--', alpha=0.4)
ax.set_xlim(left=0)
ax.set_ylim(bottom=0)
ax.spines[['top', 'right']].set_visible(False)

plt.tight_layout()
out_path = Path(r"C:\openfn\assistant-analytics\charts") / "response_time_vs_prompt_character_length.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"\nChart saved to {out_path}")

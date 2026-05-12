import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict

SESSION_DIR = r"C:\openfn\assistant-analytics\data\session_parsed"
OUTPUT_PATH = r"C:\openfn\assistant-analytics\charts\response-time-v-sequential-prompts-in-session.png"

DATE_FORMAT = "%B %d, %Y, %H:%M:%S"

response_times_by_position = defaultdict(list)

for filename in os.listdir(SESSION_DIR):
    if not filename.endswith(".csv"):
        continue


    filepath = os.path.join(SESSION_DIR, filename)
    try:
        df = pd.read_csv(filepath)
    except Exception:
        continue

    if "role" not in df.columns or "inserted_at" not in df.columns or "processing_completed_at" not in df.columns:
        continue

    user_rows = df[df["role"] == "user"].copy()

    user_rows["inserted_at"] = pd.to_datetime(user_rows["inserted_at"], format=DATE_FORMAT, errors="coerce")
    user_rows["processing_completed_at"] = pd.to_datetime(user_rows["processing_completed_at"], format=DATE_FORMAT, errors="coerce")

    # Drop rows missing either timestamp
    user_rows = user_rows.dropna(subset=["inserted_at", "processing_completed_at"])
    user_rows = user_rows.sort_values("inserted_at").reset_index(drop=True)

    for i, row in user_rows.iterrows():
        duration = (row["processing_completed_at"] - row["inserted_at"]).total_seconds()
        if duration >= 0:
            response_times_by_position[i + 1].append(duration)

positions = sorted(response_times_by_position.keys())
medians = [np.median(response_times_by_position[p]) for p in positions]
q1s = [np.percentile(response_times_by_position[p], 25) for p in positions]
q3s = [np.percentile(response_times_by_position[p], 75) for p in positions]
counts = [len(response_times_by_position[p]) for p in positions]

filtered = [(p, med, q1, q3, c) for p, med, q1, q3, c in zip(positions, medians, q1s, q3s, counts)]
positions, medians, q1s, q3s, counts = zip(*filtered) if filtered else ([], [], [], [], [])

lower_err = [med - q1 for med, q1 in zip(medians, q1s)]
upper_err = [q3 - med for med, q3 in zip(medians, q3s)]

fig, ax = plt.subplots(figsize=(12, 6))
ax.errorbar(positions, medians, yerr=[lower_err, upper_err], marker="o", linewidth=2,
            color="#2196F3", markersize=5, ecolor="#90CAF9", elinewidth=1.5, capsize=4)
ax.set_xlabel("Sequential Prompt Number Within Session", fontsize=12)
ax.set_ylabel("Median Response Time (seconds)", fontsize=12)
ax.set_title("Median Response Time by Sequential Prompt Position in Session", fontsize=14)
ax.text(0.99, 0.97, "Error bars show interquartile range (Q1–Q3)", transform=ax.transAxes,
        fontsize=8, color="gray", ha="right", va="top")
ax.set_ylim(bottom=0, top=70)
ax.grid(True, alpha=0.3)
ax.set_xticks(positions)

clipped_positions = [p for p, q3 in zip(positions, q3s) if q3 > 70]

for p, med, q3, c in zip(positions, medians, q3s, counts):
    ax.annotate(f"n={c}", (p, med), textcoords="offset points", xytext=(0, 8),
                ha="center", fontsize=7, color="gray")
    if q3 > 70:
        rank = clipped_positions.index(p)
        y_offset = -14 if rank % 2 == 0 else -26
        ax.annotate(f"Q3={q3:.0f}s", (p, 70), textcoords="offset points", xytext=(0, y_offset),
                    ha="center", fontsize=7, color="tomato")

plt.tight_layout()
plt.savefig(OUTPUT_PATH, dpi=150)
print(f"Chart saved to {OUTPUT_PATH}")

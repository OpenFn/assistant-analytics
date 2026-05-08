import argparse
from pathlib import Path
import pandas as pd

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument(
    "input_file",
    nargs="?",
    default=r"C:\openfn\assistant-analytics\data\staff-chat-messages-filtered.csv",
)
args = parser.parse_args()

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading data …")
df = pd.read_csv(args.input_file, low_memory=False)
print(f"  {len(df):,} rows loaded")
df = df[df['role'].isin(['user', 'assistant'])]
print(f"  {len(df):,} rows after filtering to user/assistant roles, {df['chat_session_id'].nunique():,} sessions")

# ── Parse timestamps ──────────────────────────────────────────────────────────
df["inserted_at_dt"] = pd.to_datetime(
    df["inserted_at"], format="%B %d, %Y, %H:%M:%S", errors="coerce"
)

# ── Order sessions by each session's earliest inserted_at ────────────────────
session_start = (
    df.groupby("chat_session_id")["inserted_at_dt"]
    .min()
    .sort_values()
    .reset_index()
)
session_start.columns = ["chat_session_id", "session_start"]

# ── Output directory ──────────────────────────────────────────────────────────
out_dir = Path(r"C:\openfn\assistant-analytics\data\session_parsed")
out_dir.mkdir(parents=True, exist_ok=True)

# ── Write one CSV per session ─────────────────────────────────────────────────
for x, row in enumerate(session_start.itertuples(), start=1):
    session_id = row.chat_session_id
    session_df = (
        df[df["chat_session_id"] == session_id]
        .drop(columns=["inserted_at_dt"])
        .sort_values("inserted_at")
    )
    safe_id = str(session_id).strip().replace("/", "-").replace("\\", "-").replace(":", "-").replace("\n", " ").replace("\r", "")
    filename = out_dir / f"{x} {safe_id}.csv"
    session_df.to_csv(filename, index=False)

    if x % 100 == 0 or x == len(session_start):
        print(f"  Written {x:,} / {len(session_start):,} sessions …")

print(f"\nDone. {len(session_start):,} session files written to: {out_dir}")

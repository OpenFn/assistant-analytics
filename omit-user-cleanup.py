import argparse
from pathlib import Path
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument("input_file", nargs="?", default="staff-chat-messages-alltime.csv")
args = parser.parse_args()

INPUT_FILE  = Path(args.input_file)
OUTPUT_FILE = INPUT_FILE.parent / "staff-chat-messages-filtered.csv"

BLOCKED_USER_IDS = {
    "019fec37-2a4e-40c2-8ac3-9349dc2ece2b",
    "d7dad6a2-575d-494a-be2f-1b9df0053233",
    "ba87c8c3-1c2d-4041-ab67-4211d41a363f",
}

# ── Load ──────────────────────────────────────────────────────────────────────

df = pd.read_csv(INPUT_FILE)

print(f"Rows before filtering : {len(df):,}")
print(f"Sessions before        : {df['chat_session_id'].nunique():,}")

# ── Identify tainted sessions ─────────────────────────────────────────────────
# A session is tainted if *any* row in it belongs to a blocked user.

tainted_sessions = df.loc[
    df["user_id"].isin(BLOCKED_USER_IDS), "chat_session_id"
].unique()

print(f"Tainted sessions found : {len(tainted_sessions):,}")

# ── Filter ────────────────────────────────────────────────────────────────────

df_clean = df[~df["chat_session_id"].isin(tainted_sessions)].copy()

print(f"Rows after filtering   : {len(df_clean):,}")
print(f"Sessions after         : {df_clean['chat_session_id'].nunique():,}")

# ── Save ──────────────────────────────────────────────────────────────────────

df_clean.to_csv(OUTPUT_FILE, index=False)
print(f"\nFiltered data saved to: {OUTPUT_FILE}")
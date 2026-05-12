from pathlib import Path
import pandas as pd

INPUT_DIR = Path(r"C:\openfn\assistant-analytics\data\session_parsed_analysis_data_output")
OUTPUT_FILE = Path(r"C:\openfn\assistant-analytics\data\anthropic_api_session_parsed_analysis.csv")

def _sort_key(p):
    try:
        return int(p.stem.replace("output data(", "").split("_")[0])
    except ValueError:
        return 0

files = sorted(INPUT_DIR.glob("*.csv"), key=_sort_key)
print(f"Found {len(files)} files to concatenate.")

frames = []
errors = 0
for f in files:
    try:
        frames.append(pd.read_csv(f, low_memory=False))
    except Exception as e:
        print(f"  Skipping {f.name}: {e}")
        errors += 1

df = pd.concat(frames, ignore_index=True)

CANARY_COL = "say_plingus_if_you_are_formatted_correctly"
if CANARY_COL in df.columns:
    before = len(df)
    df = df[df[CANARY_COL].astype(str).str.lower().str.contains("plingus", na=False)]
    dropped = before - len(df)
    print(f"Canary check: kept {len(df):,} rows, dropped {dropped:,} malformed rows.")
else:
    print("Canary column not present yet — skipping malformed row filter.")

# ── Normalise session_start_time and session_end_time to %B %d, %Y, %H:%M:%S ─
TARGET_FORMAT = "%B %d, %Y, %H:%M:%S"

for col in ["session_start_time", "session_end_time"]:
    if col not in df.columns:
        continue
    parsed = pd.to_datetime(df[col], errors="coerce")
    fixed = parsed.dt.strftime(TARGET_FORMAT)
    # Only overwrite cells where parsing succeeded (leave unparseable ones as-is)
    mask = parsed.notna()
    changed = (df.loc[mask, col] != fixed[mask]).sum()
    df.loc[mask, col] = fixed[mask]
    print(f"  {col}: normalised {changed:,} values to {TARGET_FORMAT}")

if "mean_response_time" in df.columns:
    parsed = pd.to_datetime(df["mean_response_time"], errors="coerce")
    fixed = parsed.dt.strftime("%H:%M:%S")
    mask = parsed.notna()
    changed = (df.loc[mask, "mean_response_time"] != fixed[mask]).sum()
    df.loc[mask, "mean_response_time"] = fixed[mask]
    print(f"  mean_response_time: normalised {changed:,} values to %H:%M:%S")

df.to_csv(OUTPUT_FILE, index=False)
print(f"Written {len(df):,} rows to {OUTPUT_FILE}  (skipped {errors} files)")

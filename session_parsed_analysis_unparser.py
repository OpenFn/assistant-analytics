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

df.to_csv(OUTPUT_FILE, index=False)
print(f"Written {len(df):,} rows to {OUTPUT_FILE}  (skipped {errors} files)")

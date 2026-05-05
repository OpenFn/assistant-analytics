"""
split_csv.py
------------
Splits a CSV file into multiple chunks, each under a specified size limit.
The original file is never modified — all output files are written to a
separate directory.

Usage:
    python claude-parse.py                          # uses defaults below
    python claude-parse.py my.csv                   # positional input file
    python claude-parse.py --input my.csv           # flag input file
    python claude-parse.py --max-mb 2 --output-dir chunks/
"""

import argparse
import os
import sys
from pathlib import Path
import pandas as pd

# ── Defaults ────────────────────────────────────────────────────────────────
DEFAULT_INPUT  = "staff-chat-messages-filtered.csv"
DEFAULT_MAX_MB = 2
# ─────────────────────────────────────────────────────────────────────────────


def split_csv(input_path: str, max_mb: float, output_dir: str) -> None:
    max_bytes = int(max_mb * 1024 * 1024)

    # ── Validate input ───────────────────────────────────────────────────────
    if not os.path.isfile(input_path):
        sys.exit(f"Error: input file not found: {input_path!r}")

    total_bytes = os.path.getsize(input_path)
    print(f"Input file  : {input_path}")
    print(f"File size   : {total_bytes / 1024 / 1024:.2f} MB")
    print(f"Chunk limit : {max_mb} MB ({max_bytes:,} bytes)")

    if total_bytes <= max_bytes:
        print("File is already within the size limit — no splitting needed.")
        return

    # ── Prepare output directory ─────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)

    # Resolve absolute paths so we can check the output isn't the same file
    input_abs  = os.path.realpath(input_path)
    output_abs = os.path.realpath(output_dir)
    base_name  = os.path.splitext(os.path.basename(input_path))[0]

    # ── Read full CSV ────────────────────────────────────────────────────────
    print("\nReading CSV …")
    df = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    total_rows = len(df)
    print(f"Total rows  : {total_rows:,}  |  Columns: {len(df.columns)}")

    # ── Estimate rows-per-chunk via a binary-search approach ─────────────────
    # Write a temporary sample to measure bytes-per-row, then refine.
    chunk_index   = 1
    row_start     = 0
    files_written = []

    while row_start < total_rows:
        # Initial guess: proportional slice
        remaining_rows  = total_rows - row_start
        remaining_bytes = total_bytes * (remaining_rows / total_rows)
        guess_rows = max(1, int(remaining_rows * max_bytes / remaining_bytes))

        # Binary-search to find the largest slice that fits under max_bytes
        lo, hi = 1, min(guess_rows * 2, remaining_rows)

        while lo < hi:
            mid = (lo + hi + 1) // 2
            chunk_df   = df.iloc[row_start : row_start + mid]
            chunk_csv  = chunk_df.to_csv(index=False)
            chunk_size = len(chunk_csv.encode("utf-8"))

            if chunk_size <= max_bytes:
                lo = mid
            else:
                hi = mid - 1

        # lo is now the max number of rows that fit
        chunk_df  = df.iloc[row_start : row_start + lo]
        out_path  = os.path.join(output_dir, f"{base_name}_part{chunk_index:03d}.csv")

        # Safety check: never overwrite the original
        if os.path.realpath(out_path) == input_abs:
            sys.exit("Error: output path would overwrite the input file. "
                     "Choose a different --output-dir.")

        chunk_df.to_csv(out_path, index=False)
        actual_size = os.path.getsize(out_path)
        print(f"  {os.path.basename(out_path)}  "
              f"rows {row_start+1:,}–{row_start+lo:,}  "
              f"({actual_size / 1024 / 1024:.2f} MB)")

        files_written.append(out_path)
        row_start   += lo
        chunk_index += 1

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\nDone. {len(files_written)} file(s) written to: {output_dir}/")


# ── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split a CSV file into chunks no larger than MAX_MB each."
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default=None,
        help="Path to the input CSV file (positional)"
    )
    parser.add_argument(
        "--input", "-i",
        default=DEFAULT_INPUT,
        help=f"Path to the input CSV file (default: {DEFAULT_INPUT!r})"
    )
    parser.add_argument(
        "--max-mb", "-m",
        type=float,
        default=DEFAULT_MAX_MB,
        dest="max_mb",
        help=f"Maximum size of each output file in MB (default: {DEFAULT_MAX_MB})"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        dest="output_dir",
        help="Directory for the output chunk files (default: same folder as input)"
    )

    args = parser.parse_args()
    input_path = args.input_file or args.input
    output_dir = args.output_dir or str(Path(input_path).parent)
    split_csv(
        input_path = input_path,
        max_mb     = args.max_mb,
        output_dir = output_dir,
    )


if __name__ == "__main__":
    main()
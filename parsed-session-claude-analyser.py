import re
import time
from pathlib import Path
import anthropic

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = Path(r"C:\openfn\assistant-analytics")
PROMPT_FILE   = BASE / "claude_prompt.txt"
ADAPTORS_FILE = BASE / "data" / "adaptors_list.txt"
TEMPLATE_FILE = BASE / "data" / "claude_analysis_output_example_template.csv"
INPUT_DIR     = BASE / "data" / "session_parsed"
OUTPUT_DIR    = BASE / "data" / "session_parsed_analysis_data_output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Load static content ────────────────────────────────────────────────────────
prompt_text   = PROMPT_FILE.read_text(encoding="utf-8")
adaptors_text = ADAPTORS_FILE.read_text(encoding="utf-8")
template_text = TEMPLATE_FILE.read_text(encoding="utf-8")

SYSTEM_TEXT = (
    f"{prompt_text}\n\n"
    f"--- adaptors_list.txt ---\n{adaptors_text}\n\n"
    f"--- claude_analysis_output_example_template.csv ---\n{template_text}"
)

# ── Anthropic client ───────────────────────────────────────────────────────────
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

def extract_csv(text):
    """Strip markdown code fences if Claude wrapped the output in them."""
    match = re.search(r"```(?:csv)?\s*\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()

# ── Session files, sorted numerically ─────────────────────────────────────────
def _sort_key(p):
    try:
        return int(p.stem.split("_")[0])
    except ValueError:
        return 0

session_files = sorted(INPUT_DIR.glob("*.csv"), key=_sort_key)
total = len(session_files)
print(f"Found {total} session files in {INPUT_DIR}")

# ── Process each session ───────────────────────────────────────────────────────
skipped = 0
done = 0
errors = 0

for i, session_path in enumerate(session_files, start=1):
    out_name = f"output data({session_path.stem}).csv"
    out_path = OUTPUT_DIR / out_name

    if out_path.exists():
        skipped += 1
        if skipped <= 3 or skipped % 100 == 0:
            print(f"[{i}/{total}] Already done, skipping: {session_path.name}")
        continue

    session_csv = session_path.read_text(encoding="utf-8", errors="replace")

    print(f"[{i}/{total}] {session_path.name} ...", end=" ", flush=True)

    # Retry loop with exponential backoff
    attempt = 0
    while True:
        try:
            with client.messages.stream(
                model="claude-opus-4-7",
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_TEXT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": f"--- Session CSV ---\n{session_csv}",
                    }
                ],
            ) as stream:
                result = stream.get_final_message()

            output_text = extract_csv(result.content[0].text)
            out_path.write_text(output_text, encoding="utf-8")
            print(f"ok ({len(output_text)} chars)")
            done += 1
            break

        except anthropic.RateLimitError:
            wait = min(60 * (2 ** attempt), 300)
            print(f"rate limited, waiting {wait}s ...", end=" ", flush=True)
            time.sleep(wait)
            attempt += 1

        except Exception as e:
            print(f"ERROR: {e}")
            out_path.with_suffix(".error.txt").write_text(str(e), encoding="utf-8")
            errors += 1
            break

    # Polite pause between requests
    time.sleep(1)

print(f"\nFinished. done={done}  skipped={skipped}  errors={errors}")
print(f"Output: {OUTPUT_DIR}")

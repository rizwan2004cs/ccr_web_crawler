import json
import os

EXTRACTED_FILE = 'data/sections_recovery.jsonl'
RECOVERY_LIST = 'data/recovery_list.txt'
OUTPUT_FILE = 'data/recovery_list_final.txt'

extracted = set()
if os.path.exists(EXTRACTED_FILE):
    with open(EXTRACTED_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                data = json.loads(line)
                extracted.add(data['url'])
            except:
                continue # Skip bad lines

all_recovery = []
if os.path.exists(RECOVERY_LIST):
    with open(RECOVERY_LIST, 'r', encoding='utf-8') as f:
        all_recovery = [l.strip() for l in f if l.strip()]

missing = [u for u in all_recovery if u not in extracted]

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write('\n'.join(missing))

print(f"Missing: {len(missing)}")

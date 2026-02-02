import json
import os

OUTPUT_FILE = 'data/sections_complete.jsonl'
FINAL_FILE = 'data/sections_clean.jsonl'

unique_urls = set()
valid_records = []
success_count = 0
total_lines = 0

print("Cleaning and deduplicating data...")
with open(OUTPUT_FILE, 'r', encoding='utf-8', errors='ignore') as infile:
    for line in infile:
        line = line.strip()
        if not line: continue
        total_lines += 1
        
        try:
            data = json.loads(line)
            url = data.get('url')
            status = data.get('extraction_status')
            
            if url and url not in unique_urls:
                unique_urls.add(url)
                valid_records.append(data)
                if status == 'success':
                    success_count += 1
        except json.JSONDecodeError:
            continue # Skip corrupt lines

print(f"Total Lines Processed: {total_lines}")
print(f"Unique URLs: {len(unique_urls)}")
print(f"Successful Extractions: {success_count}")

with open(FINAL_FILE, 'w', encoding='utf-8') as outfile:
    for record in valid_records:
        outfile.write(json.dumps(record) + '\n')

print(f"Clean data written to {FINAL_FILE}")

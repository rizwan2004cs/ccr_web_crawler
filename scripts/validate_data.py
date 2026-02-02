import json
import collections

INPUT_FILE = "data/sections.jsonl"

def validate():
    print(f"Validating {INPUT_FILE}...")
    
    total = 0
    valid = 0
    missing_title = 0
    missing_text = 0
    empty_text = 0
    external_redirects = 0
    
    seen_urls = set()
    duplicates = 0
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                total += 1
                try:
                    data = json.loads(line)
                    
                    # Check duplication
                    url = data.get('url')
                    if url in seen_urls:
                        duplicates += 1
                    seen_urls.add(url)
                    
                    # Check fields
                    if not data.get('section_title'):
                        missing_title += 1
                    
                    text_html = data.get('text_html')
                    if data.get('extraction_status') == 'external_redirect':
                        external_redirects += 1
                    elif not text_html:
                        missing_text += 1
                    elif len(text_html.strip()) < 10:
                        empty_text += 1
                    else:
                        valid += 1
                        
                except json.JSONDecodeError:
                    print(f"Skipping malformed JSON at line {total}")
    
    except FileNotFoundError:
        print("File not found.")
        return

    print("-" * 30)
    print(f"Total Records: {total}")
    print(f"Unique URLs:   {len(seen_urls)}")
    print(f"Duplicates:    {duplicates}")
    print("-" * 30)
    print(f"Valid Records: {valid}")
    print(f"Redirects:     {external_redirects} (Title 24 etc)")
    print(f"Missing Title: {missing_title}")
    print(f"Missing Text:  {missing_text}")
    print(f"Empty Text:    {empty_text}")
    print("-" * 30)
    
    if valid / total > 0.99:
        print("✅ DATASET HEALTHY")
    else:
        print("⚠️ DATA ISSUES DETECTED")

if __name__ == "__main__":
    validate()

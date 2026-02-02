import json
import collections

def peek():
    try:
        # Open in utf-8 to handle special chars
        deque = collections.deque(open('data/sections.jsonl', encoding='utf-8'), maxlen=10)
        print(f"--- Last {len(deque)} Extracted Sections ---")
        for line in deque:
            try:
                data = json.loads(line)
                sec_num = data.get('section_number', 'N/A')
                title = data.get('section_title', 'N/A')
                # Truncate title if too long
                if len(title) > 60: title = title[:57] + "..."
                
                print(f"[{data.get('extraction_status')}] {sec_num} - {title}")
                print(f"   Link: {data.get('url')}")
            except:
                pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    peek()

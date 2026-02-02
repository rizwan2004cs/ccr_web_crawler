import sys
import os
from bs4 import BeautifulSoup

# Mock class to replicate Extraction logic
class Extractor:
    def __init__(self, html):
        self.soup = BeautifulSoup(html, 'lxml')

    def extract_hierarchy(self):
        hierarchy = {
            "title": None,
            "division": None,
            "chapter": None,
            "subchapter": None,
            "article": None
        }
        
        prelim_container = self.soup.select_one('#co_prelimContainer')
        if not prelim_container:
            print("❌ #co_prelimContainer NOT FOUND")
            return hierarchy
            
        headers = prelim_container.select('.co_prelimHead')
        print(f"Found {len(headers)} headers")
        
        for i, header in enumerate(headers):
            # Debug: what is inside?
            print(f"Header {i} content: {repr(header.contents)}")
            
            text = header.contents[0] if header.contents else ""
            if not isinstance(text, str):
                 print(f"  -> contents[0] is not str: {type(text)}")
                 text = header.text.split('\n')[0].strip()
            
            text = str(text).strip()
            print(f"  -> Extracted text: '{text}'")
            
            if text.startswith('Title'):
                hierarchy['title'] = text
            elif 'Division' in text:
                hierarchy['division'] = text
            elif 'Chapter' in text:
                hierarchy['chapter'] = text
            elif 'Subchapter' in text:
                hierarchy['subchapter'] = text
            elif 'Article' in text:
                hierarchy['article'] = text
        
        return hierarchy

    def extract_citation_short(self):
        print("\n--- Testing Citation ---")
        cite_elem = self.soup.select_one('#co_docHeaderCitation #titleDesc')
        if cite_elem:
            print(f"Match #co_docHeaderCitation #titleDesc: '{cite_elem.get_text(strip=True)}'")
            return cite_elem.get_text(strip=True)
        else:
            print("❌ #co_docHeaderCitation #titleDesc NOT FOUND")

        cite_elem = self.soup.select_one('.co_cmdExpandedcite')
        if cite_elem:
             print(f"Match .co_cmdExpandedcite: '{cite_elem.get_text(strip=True)}'")
             return cite_elem.get_text(strip=True).split(',')[0]
        
        return None

if __name__ == "__main__":
    try:
        filename = sys.argv[1] if len(sys.argv) > 1 else 'debug_page.html'
        print(f"Testing on file: {filename}")
        with open(filename, 'r', encoding='utf-8') as f:
            html = f.read()
        
        ex = Extractor(html)
        h = ex.extract_hierarchy()
        print("\nFinal Hierarchy:", h)
        
        c = ex.extract_citation_short()
        print("Final Citation:", c)

    except FileNotFoundError:
        print("debug_page.html not found")

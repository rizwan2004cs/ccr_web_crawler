"""
CCR Content Extraction (Phase 4.99 - Emergency Repair)
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from bs4 import BeautifulSoup
import sys
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# Force UTF-8 for Windows console/logs
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Configuration
INPUT_FILE = Path("checkpoints/discovered_urls.txt")
OUTPUT_FILE = Path("data/sections_final_5k.jsonl")
CHECKPOINT_FILE = Path("checkpoints/extraction_state.json")
FAILED_FILE = Path("data/failed_extractions.txt")
LOG_FILE = Path("logs/extraction.log")

CHECKPOINT_FREQUENCY = 100
DELAY_SECONDS = 1.0 # Faster for repair
MAX_RETRIES = 3

# Paths
DATA_DIR = Path("data")
LOG_DIR = Path("logs")
CHECKPOINT_DIR = Path("checkpoints")


def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

class SectionExtractor:
    def __init__(self, html: str, url: str):
        self.soup = BeautifulSoup(html, 'lxml')
        self.url = url
    
    def extract_guid(self) -> Optional[str]:
        guid_input = self.soup.select_one('input[name="documentGuid"]')
        if guid_input and guid_input.get('value'):
            return guid_input['value']
        if 'Document/' in self.url:
            parts = self.url.split('Document/')
            if len(parts) > 1:
                return parts[1].split('?')[0]
        return None
    
    def extract_section_number(self) -> Optional[str]:
        title_elem = self.soup.select_one('.co_title')
        if not title_elem: return None
        title_text = title_elem.get_text(strip=True)
        if '§' in title_text and '.' in title_text:
            return title_text.split('.')[0].strip()
        if '§' in title_text:
            words = title_text.split()
            for i, word in enumerate(words):
                if '§' in word and i + 1 < len(words):
                    return f"{word} {words[i+1]}"
        return None
    
    def extract_section_title(self) -> Optional[str]:
        title_elem = self.soup.select_one('#co_docHeaderTitleLine #title')
        if title_elem:
             title_text = title_elem.get_text(strip=True)
             if '§' in title_text and '.' in title_text:
                 parts = title_text.split('.', 1)
                 if len(parts) > 1: return parts[1].strip()
             return title_text
        title_elem = self.soup.select_one('.co_title')
        if not title_elem: return None
        title_text = title_elem.get_text(strip=True)
        if '§' in title_text and '.' in title_text:
            parts = title_text.split('.', 1)
            if len(parts) > 1: return parts[1].strip()
        return title_text
    
    def extract_citation_short(self) -> Optional[str]:
        cite_elem = self.soup.select_one('#co_docHeaderCitation #titleDesc')
        if cite_elem: return cite_elem.get_text(strip=True)
        cite_elem = self.soup.select_one('.co_cmdExpandedcite')
        if cite_elem: return cite_elem.get_text(strip=True).split(',')[0]
        cite_elem = self.soup.select_one('.co_citeString')
        if cite_elem: return cite_elem.get_text(strip=True)
        section_num = self.extract_section_number()
        if section_num:
            hierarchy = self.extract_hierarchy()
            if hierarchy.get('title'):
                title_num = hierarchy['title'].split('.')[0].replace('Title', '').strip()
                return f"{title_num} CCR {section_num}"
        return None
    
    def extract_citation_canonical(self) -> Optional[str]:
        return self.extract_citation_short()
    
    def extract_hierarchy(self) -> Dict[str, Optional[str]]:
        hierarchy = {"title": None, "division": None, "chapter": None, "subchapter": None, "article": None}
        prelim_container = self.soup.select_one('#co_prelimContainer')
        if not prelim_container: return hierarchy
        headers = prelim_container.select('.co_prelimHead')
        for header in headers:
            if not header.contents: continue
            text = str(header.contents[0]).strip()
            if '(' in text: text = text.split('(')[0].strip()
            if text.startswith('Title'): hierarchy['title'] = text
            elif 'Division' in text: hierarchy['division'] = text
            elif 'Chapter' in text: hierarchy['chapter'] = text
            elif 'Subchapter' in text: hierarchy['subchapter'] = text
            elif 'Article' in text: hierarchy['article'] = text
        return hierarchy
    
    def extract_text(self) -> Tuple[Optional[str], Optional[str]]:
        text_elems = self.soup.select('.co_paragraphText')
        if not text_elems:
            body_elem = self.soup.select_one('.co_contentBlock.co_body')
            if body_elem: text_elems = [body_elem]
            else: return None, None
        text_html = "\n".join([str(elem) for elem in text_elems])
        text_plain = "\n\n".join([elem.get_text(separator=' ', strip=True) for elem in text_elems])
        return text_html, text_plain
    
    def extract_currency_notice(self) -> Optional[str]:
        notice_elem = self.soup.select_one('.co_currencyNotice')
        return notice_elem.get_text(strip=True) if notice_elem else None
    
    def is_external_redirect(self) -> bool:
        external_links = self.soup.select('a[href*="dgs.ca.gov"], a[href*="iccsafe.org"], a[href*="nfpa.org"]')
        page_text = self.soup.get_text()
        redirect_keywords = ['redirects to', 'external site', 'building standards commission']
        return len(external_links) > 0 or any(kw in page_text.lower() for kw in redirect_keywords)
    
    def _detect_external_url(self) -> Optional[str]:
        external_links = self.soup.select('a[href*="dgs.ca.gov"], a[href*="iccsafe.org"], a[href*="nfpa.org"]')
        if external_links: return external_links[0].get('href')
        return "https://www.dgs.ca.gov/BSC"

    def extract_all(self) -> Dict:
        if self.is_external_redirect():
            return {
                "url": self.url, "guid": self.extract_guid(), "section_number": self.extract_section_number(),
                "section_title": self.extract_section_title(), "citation_short": None, "citation_canonical": None,
                "hierarchy": self.extract_hierarchy(), "text_html": None, "text_plain": None, "currency_notice": None,
                "extraction_status": "external_redirect", "extraction_note": "Title 24 redirects",
                "external_url": self._detect_external_url(), "extracted_at": datetime.now().isoformat()
            }
        text_html, text_plain = self.extract_text()
        if not text_plain:
            return {
                "url": self.url, "guid": self.extract_guid(), "section_number": self.extract_section_number(),
                "section_title": self.extract_section_title(), "citation_short": None, "citation_canonical": None,
                "hierarchy": self.extract_hierarchy(), "text_html": None, "text_plain": None, "currency_notice": None,
                "extraction_status": "parse_failure", "extraction_note": "Could not extract document text content",
                "external_url": None, "extracted_at": datetime.now().isoformat()
            }
        return {
            "url": self.url, "guid": self.extract_guid(), "section_number": self.extract_section_number(),
            "section_title": self.extract_section_title(), "citation_short": self.extract_citation_short(),
            "citation_canonical": self.extract_citation_canonical(), "hierarchy": self.extract_hierarchy(),
            "text_html": text_html, "text_plain": text_plain, "currency_notice": self.extract_currency_notice(),
            "extraction_status": "success", "extraction_note": None, "external_url": None,
            "extracted_at": datetime.now().isoformat()
        }

def create_failure_record(url: str, error_message: str) -> Dict:
    return {
        "url": url, "guid": None, "section_number": None, "section_title": None,
        "citation_short": None, "citation_canonical": None, "hierarchy": {},
        "text_html": None, "text_plain": None, "currency_notice": None,
        "extraction_status": "parse_failure", "extraction_note": f"Extraction error: {error_message}",
        "external_url": None, "extracted_at": datetime.now().isoformat()
    }

def save_checkpoint(processed_count: int, failed_count: int):
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    state = {"processed_count": processed_count, "failed_count": failed_count, "timestamp": datetime.now().isoformat()}
    with open(CHECKPOINT_FILE, 'w') as f: json.dump(state, f, indent=2)
    logging.info(f"Checkpoint: {processed_count} processed, {failed_count} failed")

def get_resume_position() -> int:
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, 'r') as f: return sum(1 for _ in f)
    return 0

async def extract_section(crawler: AsyncWebCrawler, url: str, delay: float = DELAY_SECONDS) -> Dict:
    await asyncio.sleep(delay)
    logging.info(f"Extracting: {url}")
    try:
        config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=45000, wait_for="css:#co_docHeaderTitleLine", wait_until="networkidle")
        result = await crawler.arun(url=url, config=config)
        if not result.success:
            logging.error(f"Crawl failed for {url}: {result.error_message}")
            return create_failure_record(url, result.error_message)
        extractor = SectionExtractor(result.html, url)
        section_data = extractor.extract_all()
        logging.info(f"✓ Extracted: {section_data.get('section_number', 'N/A')} - {section_data['extraction_status']}")
        return section_data
    except Exception as e:
        logging.error(f"Exception extracting {url}: {e}")
        return create_failure_record(url, str(e))

async def extract_all_sections():
    setup_logging()
    logging.info("Starting CCR content extraction (Repair Run - 25x)")
    
    RECOVERY_FILE = DATA_DIR / "recovery_list_final.txt"
    if not RECOVERY_FILE.exists():
        logging.error(f"Recovery file not found: {RECOVERY_FILE}")
        return
    
    urls = RECOVERY_FILE.read_text(encoding='utf-8').strip().split('\n')
    urls = [u for u in urls if u]
    
    start_index = get_resume_position()
    urls_to_process = urls[start_index:]
    
    logging.info(f"Total Repair URLs: {len(urls)}")
    logging.info(f"Already processed: {start_index}")
    logging.info(f"Remaining: {len(urls_to_process)}")
    
    DATA_DIR.mkdir(exist_ok=True)
    
    browser_config = BrowserConfig(headless=True, verbose=False, extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"])
    
    failed_count = 0
    concurrency_sem = asyncio.Semaphore(20)  # Final Pass: 20x
    write_lock = asyncio.Lock()
    
    async def process_url(crawler, url, idx):
        nonlocal failed_count
        async with concurrency_sem:
            section_data = await extract_section(crawler, url)
            async with write_lock:
                if section_data['extraction_status'] != 'success':
                    failed_count += 1
                    with open(FAILED_FILE, 'a') as f:
                        f.write(f"{url}\t{section_data['extraction_status']}\t{section_data.get('extraction_note', '')}\n")
                with open(OUTPUT_FILE, 'a') as f:
                    f.write(json.dumps(section_data) + '\n')
                if idx % CHECKPOINT_FREQUENCY == 0:
                    save_checkpoint(idx, failed_count)
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            tasks = []
            for i, url in enumerate(urls_to_process, start=start_index + 1):
                task = asyncio.create_task(process_url(crawler, url, i))
                tasks.append(task)
                if len(tasks) >= 20:
                     await asyncio.gather(*tasks)
                     tasks = []
            if tasks: await asyncio.gather(*tasks)
    except KeyboardInterrupt: logging.warning("Extraction interrupted")
    except Exception as e: logging.error(f"Unexpected: {e}"); raise

if __name__ == "__main__":
    asyncio.run(extract_all_sections())

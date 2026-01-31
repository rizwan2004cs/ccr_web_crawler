"""
CCR Content Extraction (Phase 4)

Extracts structured content from discovered CCR section URLs.
Uses validated CSS selectors from Phase 2 to parse HTML and extract
11 fields per schema.json.

Based on phase4_implementation_plan.md
"""

import asyncio
import json
import logging
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


# Configuration
INPUT_FILE = Path("checkpoints/discovered_urls.txt")
OUTPUT_FILE = Path("data/sections.jsonl")
CHECKPOINT_FILE = Path("checkpoints/extraction_state.json")
FAILED_FILE = Path("data/failed_extractions.txt")
LOG_FILE = Path("logs/extraction.log")

CHECKPOINT_FREQUENCY = 100
DELAY_SECONDS = 1.5
MAX_RETRIES = 3

# Paths
DATA_DIR = Path("data")
LOG_DIR = Path("logs")
CHECKPOINT_DIR = Path("checkpoints")


def setup_logging():
    """Configure logging for extraction."""
    LOG_DIR.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )


class SectionExtractor:
    """Handles extraction of a single CCR section from HTML."""
    
    def __init__(self, html: str, url: str):
        """
        Initialize extractor with HTML content.
        
        Args:
            html: Raw HTML content
            url: Source URL
        """
        self.soup = BeautifulSoup(html, 'lxml')
        self.url = url
    
    def extract_guid(self) -> Optional[str]:
        """
        Extract document GUID from hidden input field.
        
        Selector: input[name="documentGuid"]
        """
        guid_input = self.soup.select_one('input[name="documentGuid"]')
        if guid_input and guid_input.get('value'):
            return guid_input['value']
        
        # Fallback: extract from URL
        if 'Document/' in self.url:
            parts = self.url.split('Document/')
            if len(parts) > 1:
                guid = parts[1].split('?')[0]
                return guid
        
        return None
    
    def extract_section_number(self) -> Optional[str]:
        """
        Extract section number (e.g., '§ 1234').
        
        Selector: .co_title
        Format: "§ 1234. Section Title Text" → "§ 1234"
        """
        title_elem = self.soup.select_one('.co_title')
        if not title_elem:
            return None
        
        title_text = title_elem.get_text(strip=True)
        
        # Split on first period to separate number from title
        if '§' in title_text and '.' in title_text:
            section_part = title_text.split('.')[0].strip()
            return section_part
        
        # Handle case with § but no period (edge case)
        if '§' in title_text:
            words = title_text.split()
            # Find § and next word (number)
            for i, word in enumerate(words):
                if '§' in word and i + 1 < len(words):
                    return f"{word} {words[i+1]}"
        
        return None
    
    def extract_section_title(self) -> Optional[str]:
        """
        Extract section title (text after § number).
        
        Selector: .co_title
        Format: "§ 1234. Section Title Text" → "Section Title Text"
        """
        title_elem = self.soup.select_one('.co_title')
        if not title_elem:
            return None
        
        title_text = title_elem.get_text(strip=True)
        
        # Remove section number prefix
        if '§' in title_text and '.' in title_text:
            # Split on first period and take remainder
            parts = title_text.split('.', 1)
            if len(parts) > 1:
                return parts[1].strip()
        
        # Fallback: return full title if can't parse
        return title_text
    
    def extract_citation_short(self) -> Optional[str]:
        """
        Extract short citation.
        
        Selector: .co_citeString
        Example: "17 CCR § 1234"
        """
        cite_elem = self.soup.select_one('.co_citeString')
        if cite_elem:
            return cite_elem.get_text(strip=True)
        
        # Fallback: construct from section number if available
        section_num = self.extract_section_number()
        if section_num:
            # Try to infer title number from hierarchy
            hierarchy = self.extract_hierarchy()
            if hierarchy.get('title'):
                title_num = hierarchy['title'].split('.')[0].replace('Title', '').strip()
                return f"{title_num} CCR {section_num}"
        
        return None
    
    def extract_citation_canonical(self) -> Optional[str]:
        """
        Extract canonical citation (same as short for CCR).
        
        Selector: .co_citeString
        """
        return self.extract_citation_short()
    
    def extract_hierarchy(self) -> Dict[str, Optional[str]]:
        """
        Extract hierarchical structure from breadcrumb.
        
        Selector: .co_breadcrumb a
        Returns: {title, division, chapter, subchapter, article}
        """
        hierarchy = {
            "title": None,
            "division": None,
            "chapter": None,
            "subchapter": None,
            "article": None
        }
        
        breadcrumb_links = self.soup.select('.co_breadcrumb a')
        
        for link in breadcrumb_links:
            text = link.get_text(strip=True)
            
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
    
    def extract_text(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract document text in HTML and plain formats.
        
        Selector: .co_docText
        Returns: (html_content, plain_text)
        """
        doc_text_elem = self.soup.select_one('.co_docText')
        
        if not doc_text_elem:
            return None, None
        
        # HTML version (preserve structure)
        text_html = str(doc_text_elem)
        
        # Plain text version (strip all tags)
        text_plain = doc_text_elem.get_text(separator='\n', strip=True)
        
        return text_html, text_plain
    
    def extract_currency_notice(self) -> Optional[str]:
        """
        Extract currency/update notice.
        
        Selector: .co_currencyNotice
        Example: "Current through Register 2024, No. 1"
        """
        notice_elem = self.soup.select_one('.co_currencyNotice')
        if notice_elem:
            return notice_elem.get_text(strip=True)
        return None
    
    def is_external_redirect(self) -> bool:
        """
        Check if page is an external redirect (Title 24).
        
        Looks for redirect indicators in HTML.
        """
        # Check for external link indicators
        external_links = self.soup.select('a[href*="dgs.ca.gov"], a[href*="iccsafe.org"], a[href*="nfpa.org"]')
        
        # Check page title or content for redirect message
        page_text = self.soup.get_text()
        redirect_keywords = ['redirects to', 'external site', 'building standards commission']
        
        return len(external_links) > 0 or any(kw in page_text.lower() for kw in redirect_keywords)
    
    def extract_all(self) -> Dict:
        """
        Extract all fields and return structured dictionary per schema.json.
        
        Returns:
            Dict with all 11 fields + extraction metadata
        """
        # Check for external redirect first
        if self.is_external_redirect():
            return {
                "url": self.url,
                "guid": self.extract_guid(),
                "section_number": self.extract_section_number(),
                "section_title": self.extract_section_title(),
                "citation_short": None,
                "citation_canonical": None,
                "hierarchy": self.extract_hierarchy(),
                "text_html": None,
                "text_plain": None,
                "currency_notice": None,
                "extraction_status": "external_redirect",
                "extraction_note": "Title 24 redirects to external publisher (DGS/ICC/NFPA)",
                "external_url": self._detect_external_url(),
                "extracted_at": datetime.now().isoformat()
            }
        
        # Normal extraction
        text_html, text_plain = self.extract_text()
        
        # Check if extraction was successful
        if not text_plain:
            return {
                "url": self.url,
                "guid": self.extract_guid(),
                "section_number": self.extract_section_number(),
                "section_title": self.extract_section_title(),
                "citation_short": None,
                "citation_canonical": None,
                "hierarchy": self.extract_hierarchy(),
                "text_html": None,
                "text_plain": None,
                "currency_notice": None,
                "extraction_status": "parse_failure",
                "extraction_note": "Could not extract document text content",
                "external_url": None,
                "extracted_at": datetime.now().isoformat()
            }
        
        # Success case
        return {
            "url": self.url,
            "guid": self.extract_guid(),
            "section_number": self.extract_section_number(),
            "section_title": self.extract_section_title(),
            "citation_short": self.extract_citation_short(),
            "citation_canonical": self.extract_citation_canonical(),
            "hierarchy": self.extract_hierarchy(),
            "text_html": text_html,
            "text_plain": text_plain,
            "currency_notice": self.extract_currency_notice(),
            "extraction_status": "success",
            "extraction_note": None,
            "external_url": None,
            "extracted_at": datetime.now().isoformat()
        }
    
    def _detect_external_url(self) -> Optional[str]:
        """Detect external redirect URL."""
        external_links = self.soup.select('a[href*="dgs.ca.gov"], a[href*="iccsafe.org"], a[href*="nfpa.org"]')
        if external_links:
            return external_links[0].get('href')
        return "https://www.dgs.ca.gov/BSC"  # Default Title 24 URL


async def extract_section(crawler: AsyncWebCrawler, url: str, delay: float = DELAY_SECONDS) -> Dict:
    """
    Fetch and extract a single section.
    
    Args:
        crawler: Crawl4AI crawler instance
        url: Section URL to extract
        delay: Delay before request
        
    Returns:
        Extracted section data dictionary
    """
    await asyncio.sleep(delay)
    
    logging.info(f"Extracting: {url}")
    
    try:
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=30000,
            wait_until="networkidle",
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if not result.success:
            logging.error(f"Crawl failed for {url}: {result.error_message}")
            return create_failure_record(url, result.error_message)
        
        # Extract content
        extractor = SectionExtractor(result.html, url)
        section_data = extractor.extract_all()
        
        logging.info(f"✓ Extracted: {section_data.get('section_number', 'N/A')} - {section_data['extraction_status']}")
        
        return section_data
    
    except Exception as e:
        logging.error(f"Exception extracting {url}: {e}")
        return create_failure_record(url, str(e))


def create_failure_record(url: str, error_message: str) -> Dict:
    """Create a record for failed extraction."""
    return {
        "url": url,
        "guid": None,
        "section_number": None,
        "section_title": None,
        "citation_short": None,
        "citation_canonical": None,
        "hierarchy": {
            "title": None,
            "division": None,
            "chapter": None,
            "subchapter": None,
            "article": None
        },
        "text_html": None,
        "text_plain": None,
        "currency_notice": None,
        "extraction_status": "parse_failure",
        "extraction_note": f"Extraction error: {error_message}",
        "external_url": None,
        "extracted_at": datetime.now().isoformat()
    }


def save_checkpoint(processed_count: int, failed_count: int):
    """Save extraction progress."""
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    
    state = {
        "processed_count": processed_count,
        "failed_count": failed_count,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    
    logging.info(f"Checkpoint: {processed_count} processed, {failed_count} failed")


def get_resume_position() -> int:
    """Determine where to resume extraction (count existing output lines)."""
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, 'r') as f:
            return sum(1 for _ in f)
    return 0


async def extract_all_sections():
    """
    Main extraction loop.
    
    Reads discovered URLs and extracts content for each.
    """
    setup_logging()
    logging.info("Starting CCR content extraction")
    
    # Load URLs
    if not INPUT_FILE.exists():
        logging.error(f"Input file not found: {INPUT_FILE}")
        logging.error("Run Phase 3 (discovery.py) first to generate discovered URLs")
        return
    
    urls = INPUT_FILE.read_text().strip().split('\n')
    urls = [u for u in urls if u]  # Remove empty lines
    
    # Resume from checkpoint
    start_index = get_resume_position()
    urls_to_process = urls[start_index:]
    
    logging.info(f"Total URLs: {len(urls)}")
    logging.info(f"Already processed: {start_index}")
    logging.info(f"Remaining: {len(urls_to_process)}")
    
    # Ensure output directory exists
    DATA_DIR.mkdir(exist_ok=True)
    
    # Browser config
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    
    failed_count = 0
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for i, url in enumerate(urls_to_process, start=start_index + 1):
                # Extract section
                section_data = await extract_section(crawler, url)
                
                # Track failures
                if section_data['extraction_status'] != 'success':
                    failed_count += 1
                    
                    # Log failed URL
                    with open(FAILED_FILE, 'a') as f:
                        f.write(f"{url}\t{section_data['extraction_status']}\t{section_data.get('extraction_note', '')}\n")
                
                # Append to JSON Lines file
                with open(OUTPUT_FILE, 'a') as f:
                    f.write(json.dumps(section_data) + '\n')
                
                # Checkpoint every N sections
                if i % CHECKPOINT_FREQUENCY == 0:
                    save_checkpoint(i, failed_count)
    
    except KeyboardInterrupt:
        logging.warning("Extraction interrupted by user")
    
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        save_checkpoint(start_index + len(urls_to_process), failed_count)
        raise
    
    finally:
        # Final checkpoint
        total_processed = start_index + len(urls_to_process)
        save_checkpoint(total_processed, failed_count)
        
        # Summary
        logging.info("="*60)
        logging.info("Extraction complete!")
        logging.info(f"Total sections processed: {total_processed}")
        logging.info(f"Failed extractions: {failed_count}")
        logging.info(f"Success rate: {((total_processed - failed_count) / total_processed * 100):.1f}%")
        logging.info(f"Output: {OUTPUT_FILE}")
        logging.info("="*60)


def extract():
    """Synchronous wrapper for async extraction."""
    asyncio.run(extract_all_sections())


if __name__ == "__main__":
    extract()

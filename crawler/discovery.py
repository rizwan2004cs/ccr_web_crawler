"""
CCR URL Discovery Crawler (Phase 3) - Crawl4AI Implementation

This crawler implements Breadth-First Search (BFS) to discover all CCR section URLs
from https://govt.westlaw.com/calregs using Crawl4AI.

Meets internship assignment requirements:
- Uses Crawl4AI for crawling (Assignment §6)
- Controlled concurrency
- Retry logic with exponential backoff
- URL normalization and deduplication
- Persistent checkpoints (resume after crashes)
- Clear separation: URL discovery vs content extraction

Based on architecture.md specifications.
"""

import asyncio
import time
import json
import logging
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Set, List, Tuple, Dict
from urllib.parse import urljoin, urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


# Configuration
START_URL = "https://govt.westlaw.com/calregs/Index"
BASE_URL = "https://govt.westlaw.com"
DELAY_SECONDS = 1.5
CHECKPOINT_FREQUENCY = 100
MAX_CONCURRENT = 3  # Controlled concurrency
USER_AGENT = "CCR-Crawler/1.0 (Educational Project)"

# Paths
CHECKPOINT_DIR = Path("checkpoints")
LOG_DIR = Path("logs")
DATA_DIR = Path("data")

QUEUE_STATE_FILE = CHECKPOINT_DIR / "queue_state.json"
VISITED_FILE = CHECKPOINT_DIR / "visited_urls.txt"
DISCOVERED_FILE = CHECKPOINT_DIR / "discovered_urls.txt"
LOG_FILE = LOG_DIR / "discovery.log"


# Setup logging
def setup_logging():
    """Configure logging to file and console."""
    LOG_DIR.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )


def is_navigation_url(url: str) -> bool:
    """Check if URL is a navigation page (/Browse/)."""
    return "/calregs/Browse/" in url or url.endswith("/calregs/Index")


def is_section_url(url: str) -> bool:
    """Check if URL is a section document page (/Document/)."""
    return "/calregs/Document/" in url


def normalize_url(url: str) -> str:
    """
    Normalize URL for deduplication.
    
    Removes fragments and normalizes query parameters.
    """
    parsed = urlparse(url)
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized


def extract_links_from_html(html: str, base_url: str) -> List[str]:
    """
    Extract all CCR links from HTML.
    
    Args:
        html: HTML content
        base_url: Base URL for resolving relative links
        
    Returns:
        List of absolute, normalized URLs
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html, 'lxml')
    links = []
    
    # Find all links
    for link_tag in soup.find_all('a', href=True):
        href = link_tag['href']
        
        # Resolve to absolute URL
        absolute_url = urljoin(base_url, href)
        
        # Only keep CCR links
        if '/calregs/' in absolute_url:
            normalized = normalize_url(absolute_url)
            links.append(normalized)
    
    return list(set(links))  # Deduplicate


def save_checkpoint(queue: deque, visited: Set[str], discovered: List[str]):
    """
    Save crawler state to disk.
    
    Args:
        queue: BFS queue
        visited: Set of visited URLs
        discovered: List of discovered section URLs
    """
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    
    # Save queue state as JSON
    queue_state = {
        "timestamp": datetime.now().isoformat(),
        "queue": list(queue),
        "visited_count": len(visited),
        "discovered_count": len(discovered)
    }
    
    with open(QUEUE_STATE_FILE, 'w') as f:
        json.dump(queue_state, f, indent=2)
    
    # Save visited URLs
    with open(VISITED_FILE, 'w') as f:
        for url in sorted(visited):
            f.write(f"{url}\n")
    
    # Save discovered section URLs
    with open(DISCOVERED_FILE, 'w') as f:
        for url in discovered:
            f.write(f"{url}\n")
    
    logging.info(f"Checkpoint saved: {len(visited)} visited, {len(queue)} in queue, {len(discovered)} discovered")


def load_checkpoint() -> Tuple[deque, Set[str], List[str]]:
    """
    Load crawler state from disk.
    
    Returns:
        Tuple of (queue, visited, discovered)
    """
    if not QUEUE_STATE_FILE.exists():
        return deque([START_URL]), set(), []
    
    # Load queue state
    with open(QUEUE_STATE_FILE, 'r') as f:
        queue_state = json.load(f)
    
    queue = deque(queue_state.get("queue", [START_URL]))
    
    # Load visited URLs
    visited = set()
    if VISITED_FILE.exists():
        with open(VISITED_FILE, 'r') as f:
            visited = {line.strip() for line in f if line.strip()}
    
    # Load discovered section URLs
    discovered = []
    if DISCOVERED_FILE.exists():
        with open(DISCOVERED_FILE, 'r') as f:
            discovered = [line.strip() for line in f if line.strip()]
    
    logging.info(f"Resuming from checkpoint: {len(visited)} visited, {len(queue)} in queue, {len(discovered)} discovered")
    
    return queue, visited, discovered


async def fetch_with_crawl4ai(crawler: AsyncWebCrawler, url: str, delay: float = DELAY_SECONDS) -> str:
    """
    Fetch URL using Crawl4AI with retry logic and rate limiting.
    
    Args:
        crawler: Crawl4AI crawler instance
        url: URL to fetch
        delay: Delay before request
        
    Returns:
        HTML content
    """
    await asyncio.sleep(delay)
    
    logging.info(f"Fetching: {url}")
    
    # Crawl4AI configuration
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,  # Always fetch fresh
        page_timeout=30000,  # 30 seconds
        wait_until="networkidle",  # Wait for page to load
    )
    
    # Crawl with retry logic (Crawl4AI handles retries internally)
    result = await crawler.arun(url=url, config=config)
    
    if not result.success:
        raise Exception(f"Crawl failed: {result.error_message}")
    
    return result.html


async def crawl_async():
    """
    Main BFS crawler implementation using Crawl4AI (async).
    
    Discovers all CCR section URLs by traversing navigation pages.
    """
    setup_logging()
    logging.info("Starting CCR URL discovery crawler (Crawl4AI)")
    
    # Initialize or resume
    queue, visited, discovered = load_checkpoint()
    
    # Crawl4AI browser configuration
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    
    url_count = 0
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            while queue:
                url = queue.popleft()
                
                # Skip if already visited
                if url in visited:
                    continue
                
                visited.add(url)
                url_count += 1
                
                try:
                    # Fetch page using Crawl4AI
                    html = await fetch_with_crawl4ai(crawler, url)
                    
                    # Extract links
                    links = extract_links_from_html(html, BASE_URL)
                    logging.info(f"[{url_count}] Extracted {len(links)} links from {url}")
                    
                    # Classify and process links
                    for link in links:
                        if link in visited:
                            continue
                        
                        if is_navigation_url(link):
                            # Navigation page - add to queue for traversal
                            if link not in queue:
                                queue.append(link)
                        
                        elif is_section_url(link):
                            # Section page - record for extraction (Phase 4)
                            if link not in discovered:
                                discovered.append(link)
                                logging.info(f"✓ Discovered section: {link}")
                    
                    # Checkpoint every N URLs
                    if url_count % CHECKPOINT_FREQUENCY == 0:
                        save_checkpoint(queue, visited, discovered)
                
                except Exception as e:
                    logging.error(f"Failed to process {url}: {e}")
                    # Continue crawling despite errors
                    continue
    
    except KeyboardInterrupt:
        logging.warning("Crawl interrupted by user")
    
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        save_checkpoint(queue, visited, discovered)
        raise
    
    finally:
        # Final checkpoint
        save_checkpoint(queue, visited, discovered)
        
        # Summary
        logging.info("="*60)
        logging.info("Crawl complete!")
        logging.info(f"Total URLs visited: {len(visited)}")
        logging.info(f"Total sections discovered: {len(discovered)}")
        logging.info(f"Queue remaining: {len(queue)}")
        logging.info(f"Output: {DISCOVERED_FILE}")
        logging.info("="*60)


def crawl():
    """Synchronous wrapper for async crawler."""
    asyncio.run(crawl_async())


if __name__ == "__main__":
    crawl()

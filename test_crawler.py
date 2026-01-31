"""
Test script for Crawl4AI-based discovery crawler - Limited crawl for validation

This script tests the discovery crawler on a small subset:
- Crawls only limited URLs to validate logic
- Stops after discovering 10 section URLs or visiting 50 URLs
- Useful for validating implementation before full crawl
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from crawler.discovery import *


async def test_crawl_limited_async():
    """
    Run a limited crawl for testing purposes.
    
    Stops after:
    - 50 URLs visited, OR
    - 10 sections discovered
    """
    setup_logging()
    logging.info("Starting LIMITED test crawl (max 50 URLs, 10 sections) [Crawl4AI]")
    
    # Fresh start for testing
    queue = deque([START_URL])
    visited = set()
    discovered = []
    
    MAX_URLS = 50
    MAX_SECTIONS = 10
    
    url_count = 0
    
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            while queue and url_count < MAX_URLS and len(discovered) < MAX_SECTIONS:
                url = queue.popleft()
                
                if url in visited:
                    continue
                
                visited.add(url)
                url_count += 1
                
                try:
                    html = await fetch_with_crawl4ai(crawler, url, delay=1.0)  # Faster for testing
                    links = extract_links_from_html(html, BASE_URL)
                    
                    logging.info(f"[{url_count}/{MAX_URLS}] Extracted {len(links)} links")
                    
                    for link in links:
                        if link in visited:
                            continue
                        
                        if is_navigation_url(link):
                            if link not in queue:
                                queue.append(link)
                        
                        elif is_section_url(link):
                            if link not in discovered:
                                discovered.append(link)
                                logging.info(f"✓ Section discovered ({len(discovered)}/{MAX_SECTIONS}): {link}")
                
                except Exception as e:
                    logging.error(f"Error: {e}")
                    continue
    
    except KeyboardInterrupt:
        logging.warning("Test interrupted")
    
    # Results
    print("\n" + "="*60)
    print("TEST CRAWL RESULTS (Crawl4AI)")
    print("="*60)
    print(f"URLs visited: {len(visited)}")
    print(f"Sections discovered: {len(discovered)}")
    print(f"Queue remaining: {len(queue)}")
    print("\nDiscovered sections:")
    for i, url in enumerate(discovered[:5], 1):
        print(f"  {i}. {url}")
    if len(discovered) > 5:
        print(f"  ... and {len(discovered) - 5} more")
    print("="*60)
    print("\n✓ If sections were discovered, crawler logic is working!")
    print("✓ Ready for full crawl: python crawler/discovery.py")


def test_crawl_limited():
    """Synchronous wrapper for async test."""
    asyncio.run(test_crawl_limited_async())


if __name__ == "__main__":
    test_crawl_limited()

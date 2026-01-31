"""
Test Phase 4 extraction on sample HTML files

Tests the SectionExtractor class on known HTML samples from Phase 2.
Validates that CSS selectors work correctly before running full extraction.
"""

import sys
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from crawler.extraction import SectionExtractor


def test_extraction_on_sample(html_file: Path):
    """Test extraction on a single HTML sample."""
    print(f"\n{'='*60}")
    print(f"Testing: {html_file.name}")
    print('='*60)
    
    # Read HTML
    html_content = html_file.read_text(encoding='utf-8')
    
    # Create a fake URL for testing
    test_url = f"https://govt.westlaw.com/calregs/Document/TEST?viewType=FullText"
    
    # Extract
    extractor = SectionExtractor(html_content, test_url)
    section_data = extractor.extract_all()
    
    # Display results
    print(f"✓ GUID: {section_data['guid']}")
    print(f"✓ Section Number: {section_data['section_number']}")
    print(f"✓ Section Title: {section_data['section_title']}")
    print(f"✓ Citation: {section_data['citation_short']}")
    print(f"✓ Hierarchy:")
    for level, value in section_data['hierarchy'].items():
        if value:
            print(f"  - {level}: {value}")
    print(f"✓ Currency Notice: {section_data['currency_notice']}")
    print(f"✓ Extraction Status: {section_data['extraction_status']}")
    
    # Check text extraction
    if section_data['text_plain']:
        text_preview = section_data['text_plain'][:200].replace('\n', ' ')
        print(f"✓ Text Preview: {text_preview}...")
        print(f"✓ Text Length: {len(section_data['text_plain'])} chars")
    else:
        print("✗ Text extraction failed!")
    
    # Validate required fields
    required_fields = ['guid', 'section_number', 'section_title', 'hierarchy', 'extracted_at']
    missing = [f for f in required_fields if not section_data.get(f)]
    
    if missing:
        print(f"\n⚠️  Missing required fields: {missing}")
    else:
        print(f"\n✓ All required fields present")
    
    # Check schema compliance for success status
    if section_data['extraction_status'] == 'success':
        if section_data.get('text_plain'):
            print("✓ Schema valid for success status")
        else:
            print("✗ Missing text_plain for success status!")
    
    return section_data


def main():
    """Test extraction on all samples."""
    print("\n" + "="*60)
    print("PHASE 4 EXTRACTION TEST")
    print("Testing on Phase 2 HTML samples")
    print("="*60)
    
    # Find sample HTML files
    samples_dir = Path("samples")
    
    if not samples_dir.exists():
        print(f"\n✗ Samples directory not found: {samples_dir}")
        print("Run Phase 2 first to collect HTML samples")
        return
    
    html_files = list(samples_dir.glob("*.htm")) + list(samples_dir.glob("*.html"))
    
    if not html_files:
        print(f"\n✗ No HTML files found in {samples_dir}")
        return
    
    print(f"\nFound {len(html_files)} sample files")
    
    # Test on first 3 samples
    test_files = html_files[:3]
    results = []
    
    for html_file in test_files:
        try:
            result = test_extraction_on_sample(html_file)
            results.append(result)
        except Exception as e:
            print(f"\n✗ Error processing {html_file.name}: {e}")
    
    # Summary
    print(f"\n\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    print(f"Files tested: {len(results)}")
    
    success_count = sum(1 for r in results if r['extraction_status'] == 'success')
    print(f"Successful extractions: {success_count}/{len(results)}")
    
    # Show extraction status distribution
    statuses = {}
    for r in results:
        status = r['extraction_status']
        statuses[status] = statuses.get(status, 0) + 1
    
    print(f"\nExtraction status distribution:")
    for status, count in statuses.items():
        print(f"  - {status}: {count}")
    
    if success_count == len(results):
        print(f"\n✓ All tests passed! Extraction logic is working correctly.")
        print(f"✓ Ready for full extraction run.")
    else:
        print(f"\n⚠️  Some extractions failed. Review the errors above.")
    
    # Save one sample to JSON for inspection
    if results:
        sample_output = Path("data/sample_extraction.json")
        sample_output.parent.mkdir(exist_ok=True)
        
        with open(sample_output, 'w') as f:
            json.dump(results[0], f, indent=2)
        
        print(f"\n✓ Sample output saved to: {sample_output}")
    
    print("="*60)


if __name__ == "__main__":
    main()

# CCR Site Reconnaissance Notes

## Purpose
Document technical observations about the CCR website structure, behavior, and edge cases discovered during manual exploration (Phase 1).

---

## URL Pattern Examples

### Navigation URLs (Container Pages)

**Title Level:**
```
https://govt.westlaw.com/calregs/Browse/Home/California/CaliforniaCodeofRegulations?guid=I...
```

**Division Level:**
```
https://govt.westlaw.com/calregs/Browse/Home/California/CaliforniaCodeofRegulations?guid=I...
```

**Chapter Level:**
```
https://govt.westlaw.com/calregs/Browse/Home/California/CaliforniaCodeofRegulations?guid=I...
```

**Article Level:**
```
https://govt.westlaw.com/calregs/Browse/Home/California/CaliforniaCodeofRegulations?guid=I...
```

### Section URLs (Content Pages)

**Document Page:**
```
https://govt.westlaw.com/calregs/Document/I7A6B47D0FD4311ECBA0CE8BD2C3F45C2?viewType=FullText
```

---

## Findings (Phase 1 Complete — 2026-01-31)

### JavaScript Requirements ✅
- [x] **Architecture:** Fully server-side rendered (SSR)
- [x] **Navigation pages:** Server-rendered HTML
- [x] **Section pages:** Server-rendered HTML with full text embedded
- [x] **Tools tested:** Browser DevTools (F12 → Network tab), disabled cache, monitored XHR/fetch
- [x] **Key observation:** Every navigation triggered a GET request for HTML documents
- [x] **No hidden APIs:** No XHR, fetch(), or JSON API calls observed at any level
- [x] **JavaScript role:** UI/accessibility only, NOT content loading
- [x] **Offline test:** Saved HTML pages readable without JavaScript
- [x] **Conclusion:** ✅ **Static HTTP scraping is sufficient (requests + BeautifulSoup/lxml)**

**Implication:** Browser automation (Selenium/Playwright/Puppeteer) is **NOT required**

### Site Entry Point
- [x] **Canonical entry:** https://govt.westlaw.com/calregs/Index
- [x] **Purpose:** Serves full Table of Contents (list of all Titles)
- [x] **Format:** Server-rendered HTML
- [x] **Crawl start:** Begin here and follow links hierarchically

### Hierarchy Verified
- [x] **Full traversal tested:** Index → Title → Division → Chapter → Subchapter → Article → Section
- [x] **Deepest level tested:** Individual Section pages (e.g., § 1031.2)
- [x] **Observation:** Hierarchy depth varies (not all paths have Subchapter/Article levels)

### Section Content Delivery
- [x] **URL pattern:** `/calregs/Document/{GUID}?viewType=FullText`
- [x] **Content location:** Full regulation text embedded in HTML response
- [x] **Extraction method:** Parse HTML directly (no API calls needed)
- [x] **Verification:** Saved pages offline, content fully readable

### robots.txt ✅
- [x] **URL tested:** https://govt.westlaw.com/robots.txt
- [x] **Result:** No standard robots.txt file (returns HTML instead)
- [x] **Conclusion:** ✅ **No explicit crawling restrictions**
- [x] **Best practice:** Implement polite delays (1-2 sec) regardless

### Pagination
- [ ] **Status:** Not yet verified
- [ ] **Question:** Do navigation pages (Browse) paginate long lists?
- [ ] **Test approach:** Find a Title/Chapter with many children
- [ ] **Next step:** Check for "Next Page" or pagination controls in HTML

### Rate Limiting
- [ ] **Status:** Not yet tested
- [ ] **Testing approach:** Monitor response times for sequential requests
- [ ] **Best practice:** Add polite delay (1-2 seconds) between requests regardless
- [ ] **Recommended delay:** **1.5 seconds** (to be verified during crawling)

### Edge Cases Discovered
- [x] **Variable hierarchy depth:** Not all paths include Division/Subchapter/Article
- [ ] **Missing sections:** TBD (check for gaps in section numbering)
- [ ] **Duplicate sections:** TBD
- [ ] **Dead links:** TBD
- [ ] **Unusual formatting:** TBD
- [ ] **PDF attachments:** TBD (some regulations may reference external PDFs)
- [x] **Title 24 external redirect:** Title 24 (Building Standards Code) redirects to external publisher platforms (DGS/ICC/NFPA), not extractable via Westlaw

---

## Edge Case: Title 24 (Building Standards Code)

### Discovery Date: 2026-01-31

**Finding:**
Title 24 behaves differently from all other CCR titles (1–23, 25–28).

**Behavior:**
- Westlaw listing shows "Title 24. Building Standards Code"
- Selecting Title 24 redirects externally to:
  - California Building Standards Commission: https://www.dgs.ca.gov/BSC
  - ICC Digital Codes: https://codes.iccsafe.org/
  - NFPA platforms
- **No CCR Document pages exist for Title 24 on Westlaw**

**Platforms characteristics:**
- Publisher-controlled (not Westlaw)
- Partially paywalled / login-gated
- Cannot be crawled with standard CCR approach

**Design Decision:**
- **Detect and record:** Yes (mark as `extraction_status: "external_redirect"`)
- **Extract text:** No (respects access controls, legal safety)
- **Report coverage:** Yes (transparent about limitation)
- **RAG agent handling:** Flag when applicable, never quote/hallucinate content

**Impact:**
- **27 of 28 Titles** fully extractable (96.4% title coverage)
- **Estimated ~99%+ section coverage** from extractable titles
- No silent omissions (user explicitly informed)

**See `architecture.md` for full implementation strategy.**

---

## Sample Hierarchy Paths Tested

### Path 1:
```
Title: ___
  └─ Division: ___
       └─ Chapter: ___
            └─ Article: ___
                 └─ Section: ___
```

### Path 2:
```
Title: ___
  └─ Chapter: ___ (no Division)
       └─ Section: ___ (no Article)
```

---

## HTML Structure Notes (Phase 2 Complete)

### Validated CSS Selectors

Based on inspection of 5 sample section pages, the following selectors are **stable and consistent**:

**Section Title:**
- Selector: `h1#co_docHeaderTitleLine > span#title`
- Example: `§ 1031.2. Advisory Committee.`

**Short Citation:**
- Selector: `#co_docHeaderCitation #titleDesc`
- Example: `2 CA ADC § 1031.2`

**Canonical Citation:**
- Selector: `.co_cmdExpandedcite`
- Example: `Cal. Admin. Code tit. 2, § 1031.2, 2 CA ADC § 1031.2`

**Hierarchy Breadcrumb:**
- Selector: `#co_prelimContainer .co_prelimHead`
- Structure: Nested divs representing Title → Division → Chapter → Subchapter → Article
- Variable depth: Not all sections have all levels

**Section Body Text:**
- Selector: `.co_contentBlock.co_section .co_paragraphText`
- May contain multiple `.co_paragraphText` elements

**Currency Notice:**
- Selector: `.co_includeCurrencyBlock`
- Example: `This database is current through 1/9/26 Register 2026, No. 2.`

**Hidden Metadata (GUID):**
- Selector: `input[id^="co_document_metaInfo_"]`
- Attribute: `value` (JSON string)
- Contains: `docGuid`, `titleText`, `contentType`

### Key Structural Observations

✅ **Semantic class names:** Not position-dependent, reducing breakage risk  
✅ **Consistent across samples:** All 5 samples follow identical structure  
✅ **Server-rendered:** Full content in initial HTML response  
✅ **No dynamic loading:** JavaScript not required for extraction  
✅ **Stable IDs:** `co_` prefixed IDs are consistent  

### Navigation Signals

**BFS Control Points:**
- Breadcrumb links: For hierarchy navigation
- "Documents in Sequence" link: Linear navigation (not recommended)
- TOC links: Table of Contents return

**Recommendation:** Use hierarchy links for BFS traversal (more reliable than linear)

---

## Next Actions
- [ ] Manually visit and document 5 different Title pages
- [ ] Follow at least 3 complete paths (Title → Section)
- [ ] Save raw HTML samples
- [ ] Update this document with findings

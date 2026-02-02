# Changelog

All notable changes to this project will be documented in this file.

## [0.1.3] - 2026-02-02

### Added
- **Unified Scraper Architecture**: Refactored the entire scraping core into a generic, config-driven system (`extractor.py`). Specialized methods have been replaced by flexible `json` and `html` strategies in `job_scraper.py`.
- **PDF/Extra Link Support**: Added support for extracting secondary links (like PDF descriptions) from job postings using regex.
  - Added a new **Secondary Link Button** to the job card in the UI when extra links are present.
- **Studios Menu Actions**: Added **"Enable All"** and **"Disable All"** actions to the Studios menu for bulk visibility control.
- **Config Auto-Reload**: Implemented MD5 hash monitoring for `studios.json` to automatically reload settings when the file is modified externally.

### Changed
- **UI Interactions**: 
  - Clicking the studio logo in the header now opens the main **Website** instead of the careers page in some cases.
  - Studios menu checkboxes now dynamically sync with bulk enable/disable actions.
  
### Fixed
- **Stability**: Fixed `NoneType` crashes in the scraper and UI when location or link data is missing.
- **Extractor**: Improved handling of empty selectors and attributes to prevent extraction failures.

## [0.1.2] - 2026-02-02

### Added
- **RSS Strategy**: Full implementation of RSS feed scraping in `JobScraper`.
- **POST Strategy**: Support for JSON POST requests with specialized `form_data` (form-encoded) payload support and custom headers.
- **Advanced Mappings**: 
  - Added `split` transformation to extract sub-strings from titles or locations.
  - Added `regex` extraction support for all mapping fields.
  - Added `split_items` for parsing multiple jobs from a single HTML container (e.g., Luma Pictures).
- **Studio Support**: Added/Updated configurations for:
  - Digital Domain (RSS)
  - Luma Pictures (HTML - Complex)
  - Trixter (HTML)
  - Wētā FX (HTML - Tailwind)
  - Titmouse (HTML - Airtable)
  - Eyeline (Lever)
  - Ghost VFX (Disabled via flag)
  - Mainframe Studios (BambooHR)
  - Flying Wild Hog (POST JSON)
- **Disabled Flag**: Added `disabled` property in `studios.json` to exclude studios without deleting their config.

### Fixed
- **RSS Link Extraction**: Fixed issues with BeautifulSoup's `html.parser` ignoring `<link>` content. Added guid and regex fallbacks.
- **CSS Selectors**: Added escaping for Tailwind-style colons (e.g., `md:flex`) in selectors.
- **Unicode Support**: Fixed `UnicodeDecodeError` in `test_scraper.py` when reading JSON on Windows.
- **Validation**: Fixed trailing commas and duplicate keys in `studios.json`.

## [0.1.1] - 2026-01-30

### Fixed
- corrected logo loading errors and HTTP 403/404 handling.
- Refined UI styles for job widgets and scroll areas.

## [0.1.0] - 2026-01-29

### Added
- Initial project release with basic JSON and HTML scraping strategies.
- Support for Greenhouse, SmartRecruiters, and basic HTML portals.
- Maya integration and dockable UI.

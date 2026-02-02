# Changelog

All notable changes to this project will be documented in this file.

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

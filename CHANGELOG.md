# Changelog

All notable changes to this project will be documented in this file.

## [0.1.9] - 2026-02-12

### Added
- **New Studio Integrations**:
  - **Gaming & Animation**: Added support for **Bohemia Interactive, CD Projekt RED, Techland, Warhorse Studios, Digic Pictures, UPP, and PFX**.
- **Scraper Enhancements**:
  - **Dynamic Link Parsing**: Implemented `find_next_sibling` logic to handle studios with detached application links (e.g., **Little Zoo Studio**).
  - **Enhanced Locations**: Added robust default location handling for studios with fixed offices (**Digic Pictures, Techland, Illusorium**).

### Fixed
- **Scraper Stability**:
  - **DNEG**: Migrated to a more stable JSON-based API for job extraction.
  - **Link Extraction**: Improved link resolution for TalentSoft and SmartRecruiters portals.
- **UI & Branding**:
  - **Refined Styles**: Minimalist border updates and improved typography contrast for job listings.
  - **Feedback**: Added contextual "No jobs found" messages that include the active search query.
  - **Logos**: Fixed 403/404 errors for several studio icons and updated logos for **Eyeline** and **WildBrain**.

## [0.1.8] - 2026-02-07

### Added
- **New Studio Integrations**:
  - **Kojima Productions**: Added support for fetching jobs via their dynamic JSON POST endpoint.
  - **Squeeze Studio**: Implemented `json_text` scraping strategy to extract embedded configuration data.
  - **Liquid Development**: Added integration via Workable API.
- **Scraper Enhancements**:
  - **Detailed `json_text` Configuration**: Added `unescape` option to handle HTML-encoded JSON strings (e.g., in `data-` attributes).

### Fixed
- **UI Interactivity**: Resolved an issue where clicking checkable actions in the `ScrollableMenu` would not toggle their state or trigger updates.
- **Squeeze Scraper**: Fixed JSON parsing by unescaping HTML entities in the embedded data.

## [0.1.7] - 2026-02-06

### Added
- **Scrollable Studios Menu**: Replacing the standard multi-column menu with a custom `ScrollableMenu` widget designed for long lists.
  - **Search Integration**: Pinned search box at the top of the menu with live filtering and I-beam cursor support.
  - **Alphabetical Separation**: Dynamic section headers (A, B, C...) that intelligently filter with search results.
  - **Custom Scrolling**: Overlay scroll arrow buttons for mouse-over scrolling interaction.
- **Bulk Actions**: Specific "Enable All" and "Disable All" actions fixed at the bottom of the studio list.

### Changed
- **Menu UX**: Fixed menu sizing to dynamically "shrink to fit" content, removing empty space.
- **Performance**: Optimized menu filtering and resizing with iterative calculations to prevent UI lag.
- **Styles**: Updated styling for empty state buttons and menu items to match the dark theme better.

## [0.1.6] - 2026-02-06

### Added
- **New Studio Integration**:
  - **WildBrain**: TalentSoft careers portal integration with HTML scraping strategy.
- **JSON_TEXT Strategy**: New scraping strategy for extracting embedded JavaScript variables from HTML pages (e.g., `window.allOffers`, `jobsData`).
  - Implemented for **Wētā FX** and **Superprod** studios.
- **Default Location Handling**: Enhanced location mapping to support default values when location data is missing or empty.

### Changed
- **Configuration Cleanup**: Removed redundant `website` fields from studio configurations where they duplicated the `careers_url`.
  - Affected studios: Disney, ILM, Goodbye Kansas, Important Looking Pirates VFX, The Third Floor, Rise FX, Titmouse, 3Doubles Producciones.
- **Logo Updates**: 
  - Updated WildBrain logo to use higher quality stacked version.
  - Improved Brown Bag Films website URL to point directly to the careers portal.

### Fixed
- **Wētā FX Scraper**: Migrated from HTML to JSON_TEXT strategy to properly extract job data from embedded JavaScript.
- **Superprod Scraper**: Configured JSON_TEXT strategy to parse `window.allOffers` variable.
- **Link Prefixing**: Ensured proper URL construction for TalentSoft-based career portals.

## [0.1.5] - 2026-02-04

### Added
- **Major Studio Integrations**:
  - **Ubisoft**: Algolia API integration with custom payloads and pagination handling.
  - **Cinesite**: BambooHR JSON integration covering London, Montreal, and Vancouver.
  - **Image Engine**: BambooHR JSON integration.
  - **Riot Games**: Robust HTML scraping for their global careers portal.
  - **Platige Image**: Smart extraction of location from titles with fallback logic.
  - **One of Us**: Workable API integration with POST strategy.
- **Scraper Core Enhancements**:
  - **Mapping Fallbacks**: Support for a `default` field in mappings.
  - **Automatic Filtering**: Added logic to skip "Unknown" or generic placeholder job postings.
- **UI & UX Improvements**:
  - **Refined Empty States**: Better handling of "No results", "No enabled studios", and "Initial loading" states.
  - **Zero-Latency Placeholders**: `EmptyStateWidget` now initializes instantly with a "Checking for jobs..." state to eliminate UI flicker.

### Changed
- **Branding Updates**: Updated Scanline VFX to **Eyeline Studios**.
- **Performance**: Optimized logo worker to be more resilient to network timeouts.

### Fixed
- **Logo Downloads**: Resolved 403 Forbidden error during icon download.
- **Platige Mappings**: Fixed title/location separation logic.
- **Flying Wild Hog**: Cleaned up unnecessary headers.

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

# JobUI_mac Bug Fixes Summary

## Issues Fixed

### 1. Location Extraction for Milk VFX, 3Doubles, and Titmouse
**Problem:** The `find_previous` selector was not working correctly to extract locations from previous sibling elements.

**Solution:** Improved the `find_previous` implementation in `JobScraper.swift` to properly traverse previous siblings and match elements by both selector and tag name.

**File Modified:** `/Users/aleha/Documents/Programming/GitHub/JobUI_mac/Services/JobScraper.swift`

**Changes:**
- Enhanced the `applyMappingHTML` method to traverse all previous siblings
- Added support for matching elements by tag name directly
- Now correctly extracts location data from h2/h3 headers that appear before job listings

### 2. Logo Caching Collision Bug
**Problem:** Studios with the same logo filename (e.g., `logo.svg`) were sharing the same cached file, causing Twin Pines, Brown Bag, and Sony Imageworks to all display the Wild Child logo.

**Solution:** Changed the cache key from using just the filename to using the studio ID.

**Files Modified:** 
- `/Users/aleha/Documents/Programming/GitHub/JobUI_mac/Services/ImageCache.swift`
- `/Users/aleha/Documents/Programming/GitHub/JobUI_mac/ui/StudioColumnView.swift`

**Changes:**
- Modified `loadImageData` to accept a `studioId` parameter and use it as the cache filename
- Updated `CachedAsyncImage` to accept and pass the studio ID
- Cache files are now named like `{studioId}.{extension}` (e.g., `risefx.png`, `trixter.svg`)
- Removed MD5 hashing code as it's no longer needed

### 3. Hide Empty Checkbox
**Problem:** The Mac version was missing the "Hide Empty" checkbox that exists in the Python version.

**Solution:** Added a "Hide Empty" toggle in the toolbar that filters out studios with no matching jobs.

**Files Modified:** 
- `/Users/aleha/Documents/Programming/GitHub/JobUI_mac/ui/ContentView.swift`

**Changes:**
- Added `@State private var hideEmpty = false` state variable
- Added Toggle control in the toolbar next to the search field
- Implemented filtering logic in `StudioGridView` to hide studios with no matching jobs when enabled
- Added `filteredJobs` helper function to compute matching jobs per studio

## Notes for Little Zoo

The Little Zoo studio configuration in `studios.json` uses:
```json
"container": "div.sqs-block.markdown-block h2"
```

This selector directly targets `h2` elements as containers. The current implementation should handle this correctly as it extracts text from the element itself when no specific mapping is provided. If issues persist, the selector may need to be adjusted to target the parent container instead.

## Testing Recommendations

1. **Clear the image cache** to ensure all logos are re-downloaded with the new hashing system:
   - Delete the contents of `~/Library/Caches/ImageCache/`
   
2. **Test the following studios** to verify fixes:
   - **Milk VFX**: Verify locations are extracted correctly
   - **3Doubles**: Verify locations are extracted correctly  
   - **Titmouse**: Verify locations are extracted correctly
   - **Twin Pines**: Verify correct logo is displayed
   - **Brown Bag Films**: Verify correct logo is displayed
   - **Sony Pictures Imageworks**: Verify correct logo is displayed
   - **Rise FX**: Verify correct logo is displayed
   - **Trixter**: Verify correct logo is displayed
   - **Little Zoo**: Verify job titles are extracted correctly

3. **Test Hide Empty checkbox**:
   - Enable "Hide Empty" and verify studios with no jobs are hidden
   - Disable "Hide Empty" and verify all enabled studios are shown
   - Test with search filter to ensure it works in combination

## Important Notes

- **DO NOT MODIFY studios.json** - All configurations are correct in the JSON file
- The Mac version now properly accommodates the existing studios.json format
- Logo caching is now URL-specific, preventing cross-contamination between studios

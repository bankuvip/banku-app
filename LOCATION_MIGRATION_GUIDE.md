# Location Two-Column Migration Guide

## Overview
The Item table now uses two columns for location:
1. **`location_raw`** - Stores raw input (coordinates like "25.2685839,55.3192154", Google Maps URL, or plain text)
2. **`location`** - Stores formatted result (e.g., "Dubai, UAE" or "Cairo, Egypt")

## Database Migration SQL

### For MySQL/MariaDB:
```sql
-- Add new location_raw column
ALTER TABLE item ADD COLUMN location_raw VARCHAR(500) NULL AFTER images_media;

-- Migrate existing location data to location_raw (backup)
UPDATE item SET location_raw = location WHERE location IS NOT NULL;

-- Update location column to be longer (for formatted strings)
ALTER TABLE item MODIFY COLUMN location VARCHAR(200);

-- For existing items: Try to parse and format locations
-- (This can be done via a Python script or manually updated)
```

### For SQLite:
```sql
-- SQLite doesn't support ALTER COLUMN easily, so we need to recreate the table
-- This is more complex and should be done carefully with a backup first
```

## How It Works

### When Creating Items (Chatbot Flow):
1. User provides location input (coordinates, URL, or text) → saved in `location_raw`
2. System processes via `parse_location()` function → converts to "City, Country" format
3. Formatted result → saved in `location` column

### Display:
- All templates use `item.location` which now shows the formatted version
- Raw data is preserved in `location_raw` for reference/debugging

## Benefits
✅ Clean display: Users see "Dubai, UAE" instead of "25.2685839,55.3192154"  
✅ Data preservation: Original input (coordinates/URL) is saved for reference  
✅ Better search: Can search/filter by city/country easily  
✅ Future-proof: Can improve geocoding without losing original data  

## Files Modified
- `models.py` - Added `location_raw` column, updated `location` column
- `routes/chatbot.py` - Added location processing logic using `parse_location()`
- Templates - No changes needed (already use `item.location`)

## Next Steps
1. Run database migration SQL
2. (Optional) Backfill existing items: Process `location_raw` → `location` for items created before migration
3. Test with new item creation via chatbot

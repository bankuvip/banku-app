# Database Migration: SearchAnalytics Table Enhancement - MariaDB

## Overview
The `search_analytics` table has been enhanced to track comprehensive search data including dates, filters, and results.

**Important:** The `search_term` column **already exists** in the database, so it's **NOT included** in this migration script.

## New Columns to Add

The following columns need to be added to the `search_analytics` table (MariaDB):

```sql
-- Add new columns for enhanced search tracking
-- Note: search_term column already exists, do NOT add it
ALTER TABLE search_analytics 
ADD COLUMN bank_type VARCHAR(50) NULL AFTER id,
ADD COLUMN bank_slug VARCHAR(100) NULL AFTER bank_type,
ADD COLUMN category_filter VARCHAR(200) NULL AFTER search_term,
ADD COLUMN location_filter VARCHAR(200) NULL AFTER category_filter,
ADD COLUMN date_from DATE NULL AFTER location_filter,
ADD COLUMN date_to DATE NULL AFTER date_from,
ADD COLUMN min_price FLOAT NULL AFTER date_to,
ADD COLUMN max_price FLOAT NULL AFTER min_price,
ADD COLUMN results_count INT DEFAULT 0 AFTER max_price,
ADD COLUMN session_id VARCHAR(255) NULL AFTER user_id,
ADD COLUMN ip_address VARCHAR(45) NULL AFTER session_id;
```

## MariaDB Migration Script

Run this complete SQL script in your MariaDB database:

```sql
-- ============================================
-- SearchAnalytics Table Migration for MariaDB
-- ============================================
-- Note: search_term column already exists - do NOT add it

-- Add new columns (excluding search_term)
ALTER TABLE search_analytics 
ADD COLUMN bank_type VARCHAR(50) NULL AFTER id,
ADD COLUMN bank_slug VARCHAR(100) NULL AFTER bank_type,
ADD COLUMN category_filter VARCHAR(200) NULL AFTER search_term,
ADD COLUMN location_filter VARCHAR(200) NULL AFTER category_filter,
ADD COLUMN date_from DATE NULL AFTER location_filter,
ADD COLUMN date_to DATE NULL AFTER date_from,
ADD COLUMN min_price FLOAT NULL AFTER date_to,
ADD COLUMN max_price FLOAT NULL AFTER min_price,
ADD COLUMN results_count INT DEFAULT 0 AFTER max_price,
ADD COLUMN session_id VARCHAR(255) NULL AFTER user_id,
ADD COLUMN ip_address VARCHAR(45) NULL AFTER session_id;
```

## Add Indexes for Better Performance

After adding the columns, add indexes to improve query performance:

```sql
-- ============================================
-- Add Indexes (MariaDB)
-- ============================================
-- Note: MariaDB doesn't support IF NOT EXISTS for CREATE INDEX
-- If index already exists, you'll get a "Duplicate key name" error (safe to ignore)

-- Index on search_term (for popular searches query)
CREATE INDEX idx_search_term ON search_analytics(search_term);

-- Index on user_id (for user-specific analytics)
CREATE INDEX idx_user_id_search ON search_analytics(user_id);

-- Index on created_at (for date range queries)
CREATE INDEX idx_created_at_search ON search_analytics(created_at);

-- Index on bank_slug (for bank-specific popular searches)
CREATE INDEX idx_bank_slug ON search_analytics(bank_slug);
```

**Note:** If you get "Duplicate key name" errors when creating indexes, those indexes already exist and can be ignored.

## Safe Migration (Check Before Adding)

If you want to verify which columns already exist before running the migration:

```sql
-- Check existing columns
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'search_analytics'
ORDER BY ORDINAL_POSITION;
```

Or check individual columns:

```sql
-- Check if specific columns exist
SHOW COLUMNS FROM search_analytics LIKE 'bank_type';
SHOW COLUMNS FROM search_analytics LIKE 'bank_slug';
SHOW COLUMNS FROM search_analytics LIKE 'category_filter';
SHOW COLUMNS FROM search_analytics LIKE 'location_filter';
SHOW COLUMNS FROM search_analytics LIKE 'date_from';
SHOW COLUMNS FROM search_analytics LIKE 'date_to';
SHOW COLUMNS FROM search_analytics LIKE 'min_price';
SHOW COLUMNS FROM search_analytics LIKE 'max_price';
SHOW COLUMNS FROM search_analytics LIKE 'results_count';
SHOW COLUMNS FROM search_analytics LIKE 'session_id';
SHOW COLUMNS FROM search_analytics LIKE 'ip_address';
```

**If any of the above return rows, those columns already exist.** Only run `ALTER TABLE` for columns that don't exist.

## Verification

After running the migration, verify the table structure:

```sql
-- Show full table structure
DESCRIBE search_analytics;

-- Or get detailed column information
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_TYPE
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'search_analytics'
ORDER BY ORDINAL_POSITION;
```

## Expected Final Structure

The table should have these columns:

### Existing Columns (Already in Database):
- `id` (primary key)
- `search_term` ✅ **ALREADY EXISTS** - Do NOT add
- `item_type` (legacy)
- `filter_field` (legacy)
- `filter_value` (legacy)
- `search_count` (legacy)
- `last_searched` (legacy)
- `user_id` (foreign key)
- `created_at` (timestamp)

### New Columns (To Be Added):
- `bank_type` ✅ NEW - VARCHAR(50)
- `bank_slug` ✅ NEW - VARCHAR(100)
- `category_filter` ✅ NEW - VARCHAR(200)
- `location_filter` ✅ NEW - VARCHAR(200)
- `date_from` ✅ NEW - DATE
- `date_to` ✅ NEW - DATE
- `min_price` ✅ NEW - FLOAT
- `max_price` ✅ NEW - FLOAT
- `results_count` ✅ NEW - INT (default 0)
- `session_id` ✅ NEW - VARCHAR(255)
- `ip_address` ✅ NEW - VARCHAR(45)

## Error Handling

If you encounter errors:

### "Duplicate column name" error:
- **Action:** The column already exists, skip it or remove it from the ALTER TABLE statement
- **Solution:** Check which columns exist first, then only add missing ones

### "Duplicate key name" error (for indexes):
- **Action:** The index already exists
- **Solution:** Safe to ignore, the index is already there

### "Unknown column 'search_term'" error:
- **Action:** This means search_term doesn't exist (unexpected)
- **Solution:** Check your database schema, you may need to add it:
  ```sql
  ALTER TABLE search_analytics ADD COLUMN search_term VARCHAR(200) NULL;
  ```

## Notes

- ✅ **`search_term` column already exists** - **DO NOT** attempt to add it in this migration
- Old columns (`item_type`, `filter_field`, `filter_value`, `search_count`, `last_searched`) are kept for backward compatibility
- New columns are all nullable (`NULL`) to support existing data
- Indexes improve query performance for the popular searches feature
- All date-related fields use `DATE` type (not DATETIME) for date range filtering

## Migration Checklist

- [ ] Backup your database before running migration
- [ ] Verify `search_term` column exists (it should)
- [ ] Run ALTER TABLE to add new columns
- [ ] Run CREATE INDEX statements (ignore duplicate key errors)
- [ ] Verify table structure with DESCRIBE or INFORMATION_SCHEMA
- [ ] Test the application to ensure search analytics are being saved

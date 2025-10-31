# SearchAnalytics Table - Full Schema (After Migration)

## Table Name
`search_analytics`

## Complete Column Structure

| Column Name | Data Type | Nullable | Default | Description |
|------------|-----------|----------|---------|-------------|
| `id` | INT | NO | AUTO_INCREMENT | Primary key |
| `bank_type` | VARCHAR(50) | YES | NULL | Type of bank (items, users, organizations) - **NEW** |
| `bank_slug` | VARCHAR(100) | YES | NULL | Slug of the specific bank being searched - **NEW** |
| `item_type` | VARCHAR(50) | YES | NULL | Legacy field (kept for backward compatibility) |
| `search_term` | VARCHAR(200) | YES | NULL | The actual search query text - **EXISTS** |
| `category_filter` | VARCHAR(200) | YES | NULL | Category filter value if used - **NEW** |
| `location_filter` | VARCHAR(200) | YES | NULL | Location filter value if used - **NEW** |
| `date_from` | DATE | YES | NULL | Start date for date range filter - **NEW** |
| `date_to` | DATE | YES | NULL | End date for date range filter - **NEW** |
| `min_price` | FLOAT | YES | NULL | Minimum price filter - **NEW** |
| `max_price` | FLOAT | YES | NULL | Maximum price filter - **NEW** |
| `results_count` | INT | YES | 0 | Number of results returned - **NEW** |
| `filter_field` | VARCHAR(100) | YES | NULL | Legacy field name - **LEGACY** |
| `filter_value` | VARCHAR(200) | YES | NULL | Legacy field value - **LEGACY** |
| `search_count` | INT | YES | 1 | Legacy search count - **LEGACY** |
| `last_searched` | DATETIME | YES | CURRENT_TIMESTAMP | Legacy last searched timestamp - **LEGACY** |
| `user_id` | INT | YES | NULL | Foreign key to `user.id` |
| `session_id` | VARCHAR(255) | YES | NULL | Session ID for anonymous users - **NEW** |
| `ip_address` | VARCHAR(45) | YES | NULL | IP address of the searcher - **NEW** |
| `created_at` | DATETIME | YES | CURRENT_TIMESTAMP | When the search was performed |

## CREATE TABLE Statement (Full Schema)

```sql
CREATE TABLE IF NOT EXISTS search_analytics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bank_type VARCHAR(50) NULL,
    bank_slug VARCHAR(100) NULL,
    item_type VARCHAR(50) NULL,
    search_term VARCHAR(200) NULL,
    category_filter VARCHAR(200) NULL,
    location_filter VARCHAR(200) NULL,
    date_from DATE NULL,
    date_to DATE NULL,
    min_price FLOAT NULL,
    max_price FLOAT NULL,
    results_count INT DEFAULT 0,
    filter_field VARCHAR(100) NULL,
    filter_value VARCHAR(200) NULL,
    search_count INT DEFAULT 1,
    last_searched DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INT NULL,
    session_id VARCHAR(255) NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraint
    CONSTRAINT fk_search_analytics_user 
        FOREIGN KEY (user_id) 
        REFERENCES user(id) 
        ON DELETE SET NULL,
    
    -- Indexes
    INDEX idx_search_term (search_term),
    INDEX idx_user_id_search (user_id),
    INDEX idx_created_at_search (created_at),
    INDEX idx_bank_slug (bank_slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## Indexes

| Index Name | Columns | Type | Purpose |
|-----------|---------|------|---------|
| `PRIMARY` | `id` | PRIMARY KEY | Unique identifier |
| `idx_search_term` | `search_term` | INDEX | For popular searches queries |
| `idx_user_id_search` | `user_id` | INDEX | For user-specific analytics |
| `idx_created_at_search` | `created_at` | INDEX | For date range queries |
| `idx_bank_slug` | `bank_slug` | INDEX | For bank-specific popular searches |
| `fk_search_analytics_user` | `user_id` | FOREIGN KEY | Links to user table |

## Foreign Key Relationships

- **`user_id`** → `user.id` (ON DELETE SET NULL)
  - When a user is deleted, their search analytics records remain but `user_id` is set to NULL

## Column Descriptions

### New Columns (Added in This Migration)

1. **`bank_type`** (VARCHAR(50))
   - Stores the type of bank: 'items', 'users', or 'organizations'
   - Example: 'items', 'products', 'services'

2. **`bank_slug`** (VARCHAR(100))
   - Stores the unique slug identifier of the bank being searched
   - Used for bank-specific popular searches
   - Example: 'products-bank', 'services-bank'

3. **`category_filter`** (VARCHAR(200))
   - Stores the category filter value if user applied a category filter
   - Example: 'Technology', 'Furniture'

4. **`location_filter`** (VARCHAR(200))
   - Stores the location filter value if user applied a location filter
   - Example: 'Dubai, UAE', 'Cairo, Egypt'

5. **`date_from`** (DATE)
   - Start date for date range filter
   - Format: YYYY-MM-DD
   - Example: '2025-01-01'

6. **`date_to`** (DATE)
   - End date for date range filter
   - Format: YYYY-MM-DD
   - Example: '2025-12-31'

7. **`min_price`** (FLOAT)
   - Minimum price filter value
   - Example: 100.50

8. **`max_price`** (FLOAT)
   - Maximum price filter value
   - Example: 1000.00

9. **`results_count`** (INT, DEFAULT 0)
   - Number of results returned for this search
   - Helps identify zero-result searches

10. **`session_id`** (VARCHAR(255))
    - Session ID for tracking anonymous users
    - Useful for analytics on non-logged-in users

11. **`ip_address`** (VARCHAR(45))
    - IPv4 or IPv6 address of the searcher
    - Stored for analytics and security purposes

### Existing Columns (Already in Database)

1. **`id`** (INT, PRIMARY KEY)
   - Auto-incrementing primary key

2. **`search_term`** (VARCHAR(200))
   - The actual search query text
   - **Already exists** - not added in this migration

3. **`user_id`** (INT, FOREIGN KEY)
   - Links to the user who performed the search
   - NULL for anonymous users

4. **`created_at`** (DATETIME)
   - Timestamp when search was performed

### Legacy Columns (Kept for Backward Compatibility)

1. **`item_type`** (VARCHAR(50))
   - Legacy field from old analytics system

2. **`filter_field`** (VARCHAR(100))
   - Legacy field name

3. **`filter_value`** (VARCHAR(200))
   - Legacy field value

4. **`search_count`** (INT, DEFAULT 1)
   - Legacy search count field

5. **`last_searched`** (DATETIME)
   - Legacy timestamp field

## Sample Data Structure

```json
{
    "id": 1,
    "bank_type": "items",
    "bank_slug": "products-bank",
    "item_type": null,
    "search_term": "laptop",
    "category_filter": "Technology",
    "location_filter": "Dubai, UAE",
    "date_from": "2025-01-01",
    "date_to": "2025-12-31",
    "min_price": 500.00,
    "max_price": 2000.00,
    "results_count": 15,
    "filter_field": null,
    "filter_value": null,
    "search_count": 1,
    "last_searched": "2025-10-30 10:30:00",
    "user_id": 5,
    "session_id": "abc123def456",
    "ip_address": "192.168.1.100",
    "created_at": "2025-10-30 10:30:00"
}
```

## Query Examples

### Get Popular Searches for a Bank
```sql
SELECT search_term, COUNT(*) as search_count
FROM search_analytics
WHERE bank_slug = 'products-bank'
  AND search_term IS NOT NULL
  AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY search_term
ORDER BY search_count DESC
LIMIT 10;
```

### Get Zero-Result Searches
```sql
SELECT search_term, created_at, user_id
FROM search_analytics
WHERE results_count = 0
  AND search_term IS NOT NULL
ORDER BY created_at DESC
LIMIT 50;
```

### Get Search Analytics for a User
```sql
SELECT search_term, category_filter, location_filter, results_count, created_at
FROM search_analytics
WHERE user_id = 5
ORDER BY created_at DESC
LIMIT 20;
```

### Get Searches by Date Range
```sql
SELECT search_term, COUNT(*) as count, AVG(results_count) as avg_results
FROM search_analytics
WHERE created_at BETWEEN '2025-10-01' AND '2025-10-31'
  AND search_term IS NOT NULL
GROUP BY search_term
ORDER BY count DESC;
```

## Data Types Summary

- **INT**: `id`, `results_count`, `search_count`, `user_id`
- **VARCHAR**: All text fields (various lengths)
- **FLOAT**: `min_price`, `max_price`
- **DATE**: `date_from`, `date_to`
- **DATETIME**: `created_at`, `last_searched`

## Character Set & Collation

- **Engine**: InnoDB
- **Character Set**: utf8mb4
- **Collation**: utf8mb4_unicode_ci

## Notes

- All new columns are **nullable** to support existing data
- Default values: `results_count = 0`, `search_count = 1`
- Timestamps use `CURRENT_TIMESTAMP` as default
- Foreign key uses `ON DELETE SET NULL` to preserve analytics data when users are deleted
- Indexes are optimized for common query patterns (popular searches, user analytics, date ranges)


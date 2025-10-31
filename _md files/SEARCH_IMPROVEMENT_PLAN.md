# Bank Search Improvement Plan - Final

## Approved Changes

### Items Bank Search ✅

**Fields to Add:**
1. ✅ `short_description` - Important summary text
2. ✅ `tags` (JSON array) - User-defined keywords (critical!)
3. ✅ `category` - Classification field
4. ✅ `subcategory` - Secondary classification
5. ✅ `location` - Geographic information

**Fields NOT to Add:**
- ❌ `owner_name` - Removed per feedback
- ❌ `creator` - Removed per feedback

### Profiles Bank Search ✅

**Fields to Add:**
1. ✅ `profile_type` - Person, Expert, Company, etc. (user requested)
2. ✅ `location` - Geographic information

**Fields NOT to Add:**
- ❌ `website` - Removed per feedback

### Organizations Bank Search ✅

**Current fields are good** - No changes needed

---

## Implementation Plan

### Phase 1: Core Improvements (Immediate - 30-45 minutes)

#### Step 1.1: Case-Insensitive Search
- Change all `.contains()` to `.ilike()` for case-insensitive matching
- Applies to: Items, Profiles, Organizations

#### Step 1.2: Expand Items Search Fields
Add these fields to item search:
```python
Item.short_description.ilike(f'%{search}%'),
Item.category.ilike(f'%{search}%'),
Item.subcategory.ilike(f'%{search}%'),
Item.location.ilike(f'%{search}%'),
cast(Item.tags, db.Text).ilike(f'%{search}%')  # Tags JSON search
```

#### Step 1.3: Expand Profiles Search Fields
Add these fields to profile search:
```python
Profile.location.ilike(f'%{search}%'),
Profile.profile_type.ilike(f'%{search}%'),
# Also search profile_type display name if available
```

---

### Phase 2: Enhanced Search (Optional - 1-2 hours)

#### Step 2.1: Basic Relevance Ranking
Prioritize matches:
- Title matches = highest priority
- Tag matches = high priority  
- Short description = medium priority
- Other fields = lower priority

#### Step 2.2: Multi-Keyword Search
Support multiple words: "laptop computer" finds items with both words

---

## Implementation Steps

### Step-by-Step Code Changes

**File: `routes/banks.py`**

#### 1. Items Bank Search (handle_item_bank function)

**Current Code (Line ~273-279):**
```python
if search:
    query = query.filter(
        or_(
            Item.title.contains(search),
            Item.description.contains(search)
        )
    )
```

**New Code:**
```python
if search:
    search_lower = search.lower().strip()
    query = query.filter(
        or_(
            Item.title.ilike(f'%{search_lower}%'),
            Item.detailed_description.ilike(f'%{search_lower}%'),
            Item.short_description.ilike(f'%{search_lower}%'),
            Item.category.ilike(f'%{search_lower}%'),
            Item.subcategory.ilike(f'%{search_lower}%'),
            Item.location.ilike(f'%{search_lower}%'),
            cast(Item.tags, db.Text).ilike(f'%{search_lower}%')
        )
    )
```

#### 2. Profiles Bank Search (handle_user_bank function)

**Current Code (Line ~457-466):**
```python
if search:
    query = query.filter(
        or_(
            Profile.name.contains(search),
            User.first_name.contains(search),
            User.last_name.contains(search),
            User.username.contains(search),
            Profile.description.contains(search)
        )
    )
```

**New Code:**
```python
if search:
    search_lower = search.lower().strip()
    query = query.filter(
        or_(
            Profile.name.ilike(f'%{search_lower}%'),
            User.first_name.ilike(f'%{search_lower}%'),
            User.last_name.ilike(f'%{search_lower}%'),
            User.username.ilike(f'%{search_lower}%'),
            Profile.description.ilike(f'%{search_lower}%'),
            Profile.location.ilike(f'%{search_lower}%'),
            Profile.profile_type.ilike(f'%{search_lower}%')
        )
    )
```

#### 3. Organizations Bank Search (handle_organization_bank function)

**Current Code (Line ~539-545):**
```python
if search:
    query = query.filter(
        or_(
            Organization.name.contains(search),
            Organization.description.contains(search),
            Organization.location.contains(search)
        )
    )
```

**New Code:**
```python
if search:
    search_lower = search.lower().strip()
    query = query.filter(
        or_(
            Organization.name.ilike(f'%{search_lower}%'),
            Organization.description.ilike(f'%{search_lower}%'),
            Organization.location.ilike(f'%{search_lower}%')
        )
    )
```

---

## Required Imports

Add to top of `routes/banks.py`:
```python
from sqlalchemy import cast
```

---

## Testing Checklist

After implementation, test:

### Items Bank:
- [ ] Search "laptop" finds items with "laptop" in title ✅
- [ ] Search "laptop" finds items with "laptop" in tags ✅
- [ ] Search "laptop" finds items with "laptop" in short_description ✅
- [ ] Search "laptop" finds items with "laptop" in category ✅
- [ ] Search "LAPTOP" (uppercase) finds "laptop" items (case-insensitive) ✅
- [ ] Search "Dubai" finds items in Dubai location ✅

### Profiles Bank:
- [ ] Search "expert" finds profiles with profile_type "expert" ✅
- [ ] Search "person" finds profiles with profile_type "person" ✅
- [ ] Search "Cairo" finds profiles with location "Cairo" ✅
- [ ] Case-insensitive search works ✅

### Organizations Bank:
- [ ] Case-insensitive search works ✅

---

## Expected Results

### Before:
- Items: Only title + description searched (2 fields)
- Profiles: 5 fields searched (missing profile_type and location)
- Case-sensitive only
- Tags completely ignored

### After:
- Items: 7 fields searched (title, descriptions, category, subcategory, location, tags)
- Profiles: 7 fields searched (includes profile_type and location)
- Case-insensitive search
- Tags are searchable
- Better coverage and user experience

---

## Performance Considerations

1. **Tags JSON Search:**
   - Converting JSON to text for search may be slower
   - Consider adding a full-text index later
   - For now, acceptable performance for most use cases

2. **Indexes:**
   - Ensure indexes exist on frequently searched columns:
     - `Item.title`, `Item.category`, `Item.subcategory`, `Item.location`
     - `Profile.name`, `Profile.profile_type`, `Profile.location`
   - Check with: `SHOW INDEXES FROM item;` (MySQL) or similar

3. **Query Performance:**
   - Using `ilike` with `%search%` pattern doesn't use indexes efficiently
   - But acceptable for current scale
   - Future improvement: Full-text search indexes

---

## Rollout Plan

1. **Phase 1 (Now):**
   - ✅ Implement case-insensitive search
   - ✅ Add approved fields to search
   - ✅ Test thoroughly
   - ✅ Deploy

2. **Phase 2 (Future - Optional):**
   - Relevance ranking
   - Multi-keyword search
   - Search analytics

---

## Summary

**Changes:**
- Items: +5 fields (short_description, tags, category, subcategory, location)
- Profiles: +2 fields (profile_type, location)
- Organizations: Case-insensitive only
- All: Case-insensitive search

**Estimated Time:** 30-45 minutes
**Impact:** High - Significantly better search results
**Risk:** Low - Backward compatible changes


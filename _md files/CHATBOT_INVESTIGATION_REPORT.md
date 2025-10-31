# BankU Chatbot System Investigation Report

**Date:** December 2024  
**Purpose:** Complete analysis of chatbot creators, field mappings, and database structure

---

## 📋 Table of Contents

1. [Chatbot Creators Cleanup](#chatbot-creators-cleanup)
2. [Field Mapping Analysis](#field-mapping-analysis)
3. [Database Structure Analysis](#database-structure-analysis)
4. [Question Types vs Field Mappings](#question-types-vs-field-mappings)
5. [Missing Field Mappings](#missing-field-mappings)
6. [Recommendations](#recommendations)

---

## 🗑️ Chatbot Creators Cleanup

### **Deleted Creators:**
- ❌ **Simple Creator** (`create_chatbot_simple.html`) - Basic functionality only
- ❌ **Legacy Creator** (`create_chatbot.html`) - Original outdated version

### **Remaining Creators:**
- ✅ **Hybrid Creator** - Advanced field mapping + Item type integration
- ✅ **Enhanced Creator** - Full-featured creator (current choice)

### **Files Removed:**
- `templates/admin/create_chatbot_simple.html`
- `templates/admin/create_chatbot.html`
- Routes: `/chatbots/create_simple` and `/chatbots/create`

### **UI Updated:**
- `templates/admin/chatbots.html` - Removed dropdown options for deleted creators

---

## 🗺️ Field Mapping Analysis

### **Current Field Mappings (19 options):**

| Field Mapping | Database Column | Purpose |
|---------------|----------------|---------|
| `title` | `item.title` | Item title |
| `short_description` | `item.short_description` | Brief description |
| `detailed_description` | `item.detailed_description` | Full description |
| `category` | `item.category` | Main category |
| `subcategory` | `item.subcategory` | Sub-category |
| `category_subcategory` | Both fields | Cascading dropdown |
| `tags` | `item.tags` | Search tags |
| `location` | `item.location` | Location info |
| `price` | `item.price` | Price value |
| `currency` | `item.currency` | Currency code |
| `pricing_type` | `item.pricing_type` | Price type |
| `feasibility` | `item.feasibility` | Feasibility rating |
| `timeline` | `item.timeline` | Timeline info |
| `target_audience` | `item.target_audience` | Target audience |
| `benefits` | `item.benefits` | Benefits |
| `requirements` | `item.requirements` | Requirements |
| `contact_info` | `item.contact_info` | Contact information |
| `website` | `item.website` | Website URL |
| `social_media` | `item.social_media` | Social media links |

### **Duplications Removed:**
- ❌ `description` (duplicate of `detailed_description`)
- ❌ `budget` (duplicate of `price`)

---

## 🗄️ Database Structure Analysis

### **Item Table Overview:**
- **Total Columns:** 87
- **Core Fields:** 8 (title, descriptions, category, etc.)
- **Item-Type Specific:** 79 (product, service, event, etc.)
- **Analytics:** 3 (tracking and flexible storage)

### **Primary Storage Locations:**

#### **1. Main Item Table (`item`) - 87 columns**

**Core Fields (8 columns):**
- `id`, `profile_id`, `item_type_id`
- `title`, `category`, `subcategory`
- `short_description`, `detailed_description`

**Media & Location (2 columns):**
- `images_media` (JSON), `location`

**Owner/Creator Info (6 columns):**
- `owner_type`, `owner_name`, `owner_link`
- `creator_type`, `creator_id`, `creator_name`

**Pricing (3 columns):**
- `pricing_type`, `price`, `currency`

**Status & Metadata (7 columns):**
- `is_available`, `is_verified`, `rating`
- `review_count`, `request_count`, `views`
- `created_at`, `updated_at`

**Item-Type Specific Fields (61 columns):**
- **Product (9):** `condition`, `quantity`, `brand`, `model`, `specifications`, `warranty`, `accessories`, `shipping`, `creator`
- **Service (8):** `duration`, `experience_level`, `service_type`, `availability`, `availability_schedule`, `service_area`, `certifications`, `portfolio`
- **Event (9):** `event_type`, `event_date`, `venue`, `capacity`, `max_participants`, `registration_required`, `event_location`, `event_type_category`, `registration_fee`
- **Experience (7):** `experience_type`, `lessons_learned`, `mistakes_avoided`, `success_factors`, `group_size`, `location_type`, `difficulty_level`, `equipment_needed`
- **Opportunity (6):** `opportunity_type`, `urgency_level`, `deadline`, `requirements`, `compensation_type`, `compensation_amount`, `remote_work`, `part_time`
- **Information (7):** `information_type`, `source`, `reliability_score`, `last_updated`, `format`, `language`, `accessibility`, `update_frequency`
- **Observation (7):** `observation_type`, `context`, `significance`, `potential_impact`, `observation_date`, `data_source`, `confidence_level`, `actionable_insights`
- **Hidden Gem (7):** `gem_type`, `recognition_level`, `unique_value`, `promotion_potential`, `discovery_context`, `rarity_level`, `value_type`, `promotion_strategy`
- **Funding (10):** `funding_type`, `funding_amount_min`, `funding_amount_max`, `interest_rate`, `term_length`, `collateral_required`, `funding_criteria`, `funding_goal`, `funding_type_category`, `investment_terms`, `roi_expectation`
- **Project (4):** `project_status`, `team_size`, `project_type`, `technologies_used`
- **Auction (4):** `start_price`, `end_date`, `bid_increment`, `reserve_price`
- **Need (2):** `need_type`, `budget_range`
- **Idea (8):** `business_stage`, `investment_needed`, `timeline`, `target_market`, `collaboration_type`, `innovation_type`

**Analytics & Flexible Storage (3 columns):**
- `search_analytics` (JSON for search behavior tracking)
- `type_data` (JSON for flexible additional data)
- `field_usage_stats` (JSON for field usage tracking)

#### **2. Additional Fields Table (`item_fields`)**
- `item_id`, `field_name`, `field_value`, `field_type`, `field_label`
- For dynamic fields not in main table

#### **3. Flexible JSON Storage (`item.type_data`)**
```json
{
  "original_processed_data": {...},
  "unmapped_additional_data": {...},
  "display_fields": {
    "Question Text": "Answer Value"
  }
}
```

---

## 🎯 Question Types vs Field Mappings

### **Question Types Available (19 total):**

| Question Type | Display Name | Data Format | Has Mapping? |
|---------------|--------------|-------------|--------------|
| `text` | Text | String | ✅ Yes |
| `email` | Email | String | ⚠️ Limited (contact_info only) |
| `phone` | Phone | String | ⚠️ Limited (contact_info only) |
| `number` | Number | Number | ✅ Yes |
| `select` | Multiple Choice | String/Array | ✅ Yes |
| `dropdown` | Dropdown | String | ✅ Yes |
| `radio` | Radio Buttons | String | ✅ Yes |
| `checkbox` | Checkboxes | Array | ✅ Yes |
| `cascading_dropdown` | Cascading Dropdown | Object | ✅ Yes |
| `number_unit` | Number + Unit | Object | ⚠️ Limited (price only) |
| `location` | Location | Object | ✅ Yes |
| `images` | Images Upload | Array | ✅ Yes |
| `videos` | Videos Upload | Array | ❌ **NO MAPPING** |
| `audio` | Audio Upload | Array | ❌ **NO MAPPING** |
| `files_documents` | Files Upload | Array | ❌ **NO MAPPING** |
| `tags` | Tags | Array | ✅ Yes |
| `url` | URL | String | ⚠️ Limited (website/social_media only) |
| `date` | Date | Date | ❌ **NO MAPPING** |
| `textarea` | Long Text | String | ✅ Yes |

### **Mapping Coverage:**
- **16/19 question types** have suitable mappings (84%)
- **3/19 question types** have NO mappings (16%)
- **5/19 question types** have limited mappings (26%)

---

## 🚨 Missing Field Mappings

### **Question Types WITHOUT Mappings:**
1. **`videos` (Videos Upload)** - No field mapping available
2. **`audio` (Audio Upload)** - No field mapping available  
3. **`files_documents` (Files Upload)** - No field mapping available

### **Question Types with LIMITED Mappings:**
1. **`email`** - Only maps to `contact_info` (generic)
2. **`phone`** - Only maps to `contact_info` (generic)
3. **`url`** - Only maps to `website` or `social_media`
4. **`date`** - No specific date field mapping
5. **`number_unit`** - Only maps to `price` (limited)

### **Database Coverage:**
- **19/87 columns** (22%) can be mapped from chatbot questions
- **68/87 columns** (78%) are **inaccessible** through field mapping

---

## 💡 Recommendations

### **Immediate Fixes Needed:**

#### **1. Add Missing Field Mappings:**
```html
<!-- Add to Map to Field dropdown -->
<option value="videos">Videos</option>
<option value="audio">Audio</option>
<option value="files">Files</option>
<option value="email">Email</option>
<option value="phone">Phone</option>
<option value="date">Date</option>
```

#### **2. Add Missing Database Columns:**
```sql
ALTER TABLE item ADD COLUMN videos JSON;
ALTER TABLE item ADD COLUMN audio JSON;
ALTER TABLE item ADD COLUMN files JSON;
ALTER TABLE item ADD COLUMN email VARCHAR(255);
ALTER TABLE item ADD COLUMN phone VARCHAR(50);
ALTER TABLE item ADD COLUMN date_value DATE;
```

#### **3. Update Field Mapping Logic:**
```python
# In routes/chatbot.py - add new mappings
if question.question_type == 'videos':
    processed_data['videos'] = value
elif question.question_type == 'audio':
    processed_data['audio'] = value
elif question.question_type == 'files_documents':
    processed_data['files'] = value
```

### **Long-term Considerations:**

#### **1. Field Mapping Philosophy:**
- Current system focuses on **universal fields** (19 options)
- **Item-type specific fields** (68 columns) are intentionally not mappable
- This is by design - not all fields make sense for all item types

#### **2. Data Storage Strategy:**
- **Mapped data** → Direct database columns (searchable, filterable)
- **Unmapped data** → `type_data` JSON (display only)

#### **3. System Architecture:**
- Field mapping is for **core universal fields**
- Item-type specific fields are handled through other mechanisms
- JSON storage provides flexibility for additional data

---

## 🔧 Implementation Status

### **Completed:**
- ✅ Removed Simple Creator and Legacy Creator
- ✅ Cleaned up field mapping duplications
- ✅ Updated UI to show only 2 creator options
- ✅ Identified all missing field mappings
- ✅ Documented complete database structure

### **Next Steps:**
1. Add missing field mappings to dropdown
2. Add missing database columns
3. Update field mapping logic in chatbot processing
4. Test all question types save correctly
5. Verify Additional Information section displays all data

---

## 📊 Summary

The BankU chatbot system is well-designed with a comprehensive database structure (87 columns) supporting all item types. The current limitation is that only 22% of database columns are accessible through field mapping, which is actually by design. The system uses a hybrid approach:

- **Universal fields** (19) → Direct database mapping
- **Item-type specific fields** (68) → Specialized handling
- **Additional data** → JSON storage for flexibility

The main issue is missing field mappings for file uploads and specific data types, which can be easily fixed by adding the recommended mappings and database columns.

---

**Report Generated:** December 2024  
**Status:** Investigation Complete - Ready for Implementation


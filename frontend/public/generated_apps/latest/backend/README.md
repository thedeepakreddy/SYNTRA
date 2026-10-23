# MenuItem Full-Stack Backend Service

Autonomously engineered by the **SYNTRA Multi-Agent Engineering Organization**.

## System Overview
- **Framework**: FastAPI (async ASGI)
- **Database**: SQLite (aiosqlite driver) with SQLAlchemy 2.0 ORM
- **Validation**: Pydantic v2 schemas
- **Test Runner**: Pytest + pytest-asyncio + HTTPX ASGITransport
- **Mission Objective**: Act as a full-stack web developer and UI/UX designer. Build an interactive, mobile-responsive web-based menu for a modern Indian restaurant named "Tandoor & Spice". 

### 1. Structure & Scale (30 Items Total)
Create 6 distinct categories with exactly 5 items in each category (total of 30 items):

1. Appetizers & Street Chaat (5 items)
   - Samosa Chaat
   - Pani Puri Shots
   - Palak Chaat
   - Vegetable Pakora
   - Dahi Bhalla

2. Tandoor & Grills (5 items)
   - Tandoori Chicken (Half/Full)
   - Paneer Tikka
   - Murgh Malai Kebab
   - Tandoori Lamb Chops
   - Tandoori Prawns

3. Rich Curries & Masalas (5 items)
   - Butter Chicken (Murgh Makhani)
   - Palak Paneer
   - Lamb Rogan Josh
   - Chana Masala
   - Chicken Tikka Masala

4. Biryanis & Rice Specialties (5 items)
   - Hyderabadi Chicken Dum Biryani
   - Lucknowi Lamb Biryani
   - Subz Biryani (Vegetable)
   - Jeera Rice
   - Saffron Pulao

5. Breads & Accompaniments (5 items)
   - Garlic Butter Naan
   - Tandoori Roti
   - Laccha Paratha
   - Onion Kulcha
   - Cucumber Raita

6. Desserts & Drinks (5 items)
   - Gulab Jamun
   - Rasmalai
   - Mango Lassi
   - Masala Chai
   - Kulfi (Pistachio)

### 2. Required Data Schema per Item
Each of the 30 items must include:
- id: unique string/number
- name: Dish name (with Hindi subtitle in parentheses if applicable)
- category: Category name
- description: Engaging, sensory 1–2 sentence description
- price: Realistic USD or EUR price
- spiceLevel: Scale of 0 to 3 chili icons (0 = Mild, 1 = Medium, 2 = Hot, 3 = Indian Hot)
- dietaryTags: Array of badges (e.g., "Vegetarian", "Vegan-friendly", "Gluten-Free", "Chef's Special")
- allergens: Array (e.g., "Dairy", "Nuts", "Gluten")
- image: High-quality placeholder or real food image URL

### 3. Interactive UI & Features Required
- Sticky Category Navigation: Quick-filter tabs or a sidebar to jump smoothly between the 6 categories or view "All Items".
- Live Search & Filter Bar: 
  - Search input by dish name or ingredient.
  - Toggle filters for Dietary (Vegetarian, Vegan, Gluten-Free) and Spice Level.
- Interactive Item Detail Modal: Clicking any dish opens a clean popup showing a larger view, full description, ingredient breakdown, spice rating, and allergen warnings.
- Interactive Order / "Build Your Tray" Cart:
  - Users can click "Add to Tray" on any item, adjust quantities (+/-), add special cooking notes, and see a running subtotal.
  - A slide-out "Your Tray" drawer with a summary list and a mock "Submit Order / Generate QR summary" button.
- Aesthetic & Theme:
  - Warm, modern Indian aesthetic (rich saffron/terracotta accents, deep charcoal/cream background, clean typography).
  - Smooth micro-animations and responsive layout (works seamlessly on mobile phones and desktop browsers).

## Quickstart

```bash
# 1. Install dependencies
pip install fastapi uvicorn sqlalchemy aiosqlite pydantic pytest pytest-asyncio httpx

# 2. Run the application
uvicorn main:app --reload --port 8000

# 3. Access Swagger OpenAPI Docs
open http://localhost:8000/docs

# 4. Run automated test suite
pytest test_api.py -v
```

## REST API Specification
- `GET /health` — Service health probe
- `GET /api/v1/menu_items` — Search, filter, and paginate records
- `GET /api/v1/menu_items/stats` — Real-time telemetry and aggregation metrics
- `GET /api/v1/menu_items/{id}` — Fetch single record by UUID
- `POST /api/v1/menu_items` — Create a new validated record
- `PUT /api/v1/menu_items/{id}` — Update record
- `DELETE /api/v1/menu_items/{id}` — Delete record

# Artworks Web Application - Architecture Document

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Use Case View (Scenarios)](#2-use-case-view-scenarios)
3. [Logical View](#3-logical-view)
4. [Process View](#4-process-view)
5. [Development View](#5-development-view)
6. [Physical / Deployment View](#6-physical--deployment-view)
7. [Data View](#7-data-view)
8. [Security View](#8-security-view)
9. [API Reference](#9-api-reference)
10. [Technology Stack](#10-technology-stack)
11. [Configuration & Environment](#11-configuration--environment)
12. [Known Constraints & Trade-offs](#12-known-constraints--trade-offs)

---

## 1. Executive Summary

The Artworks Web Application is a full-stack system for managing and showcasing an art gallery's inventory. It consists of two independently deployed services:

- **Frontend** (`artworks-ui`): A React single-page application hosted on Vercel
- **Backend** (`artworks-api`): A FastAPI REST service hosted on Render

Both services are protected by a shared-password authentication scheme using an `X-API-Key` header. The backend persists data in a MongoDB Atlas cloud database.

**Live URLs:**

| Service  | URL                                          |
|----------|----------------------------------------------|
| Frontend | https://artworks-ui.vercel.app               |
| Backend  | https://artworks-api-xjds.onrender.com       |
| API Docs | https://artworks-api-xjds.onrender.com/docs  |

---

## 2. Use Case View (Scenarios)

The Use Case View captures who interacts with the system and what they can do.

### 2.1 Actors

| Actor           | Description                                                     |
|-----------------|-----------------------------------------------------------------|
| Visitor         | Unauthenticated user — sees only the password screen            |
| Authenticated User | User who has entered the correct shared password            |
| Health Monitor  | External service (e.g., uptime checker) hitting the root `/` endpoint |

### 2.2 Use Cases

```
                        ┌──────────────────────┐
                        │  Artworks Web App    │
                        └──────────┬───────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
   ┌─────▼─────┐          ┌───────▼───────┐         ┌───────▼───────┐
   │  Visitor   │          │ Authenticated │         │Health Monitor │
   └─────┬─────┘          │     User      │         └───────┬───────┘
         │                 └───────┬───────┘                 │
   ┌─────▼─────┐                  │                   ┌─────▼─────┐
   │ Enter      │     ┌───────────┼───────────┐       │ GET /     │
   │ Password   │     │           │           │       │ (health)  │
   └───────────┘     │           │           │       └───────────┘
                ┌─────▼───┐ ┌────▼────┐ ┌────▼────┐
                │Browse   │ │Create/  │ │Delete   │
                │Artworks │ │Edit     │ │Artwork  │
                │+ Filter │ │Artwork  │ │         │
                └─────────┘ └─────────┘ └─────────┘
                                │
                         ┌──────▼──────┐
                         │  Logout     │
                         └─────────────┘
```

### 2.3 User Flows

**Flow 1 — First Visit (Authentication)**
1. User navigates to the frontend URL
2. Password screen renders (no stored session)
3. User enters the shared password
4. Frontend sends `GET /artworks` with `X-API-Key` header
5. Backend validates key, returns `200` with artworks data
6. Frontend stores password in `sessionStorage`, renders main dashboard

**Flow 2 — Browse & Filter**
1. Authenticated user views artwork grid (3-column responsive layout)
2. User selects a type filter (e.g., "watercolor") or availability filter
3. Frontend re-fetches with query parameters (`?type=watercolor&available=true`)
4. Grid updates to show filtered results

**Flow 3 — Create Artwork**
1. User clicks "+ Add Artwork" button
2. Modal form appears with empty fields
3. User fills in title, description, types, price, dimensions, year, image URL
4. Frontend sends `POST /artworks` with form data and `X-API-Key`
5. Backend creates record with auto-generated 8-char ID, returns created artwork
6. Modal closes, grid refreshes

**Flow 4 — Edit Artwork**
1. User clicks "Edit" on an artwork card
2. Modal form appears pre-populated with existing values
3. User modifies fields
4. Frontend sends `PUT /artworks/{id}` with updated data
5. Backend applies partial update, returns updated artwork
6. Modal closes, grid refreshes

**Flow 5 — Delete Artwork**
1. User clicks "Delete" on an artwork card
2. Browser `confirm()` dialog appears
3. On confirmation, frontend sends `DELETE /artworks/{id}`
4. Backend removes record, returns success message
5. Grid refreshes

**Flow 6 — Session Expiry / Logout**
- Closing the browser tab clears `sessionStorage`, requiring re-authentication
- Clicking "Logout" clears `sessionStorage` and returns to password screen
- If any API call returns `401`, the frontend auto-logs out

---

## 3. Logical View

The Logical View describes the system's key abstractions and their relationships.

### 3.1 High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React SPA)                     │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Password     │  │ Dashboard    │  │ Modal Form            │  │
│  │ Screen       │  │              │  │ (Create / Edit)       │  │
│  │              │  │ ┌──────────┐ │  │                       │  │
│  │ - input      │  │ │ Header   │ │  │ - title, description  │  │
│  │ - submit     │  │ │ + Logout │ │  │ - types (multi-sel)   │  │
│  │ - error msg  │  │ ├──────────┤ │  │ - price, year         │  │
│  │              │  │ │ Filters  │ │  │ - dimensions          │  │
│  └──────────────┘  │ ├──────────┤ │  │ - image URL           │  │
│                    │ │ Artwork  │ │  │ - available checkbox   │  │
│                    │ │ Grid     │ │  │                       │  │
│                    │ │ (Cards)  │ │  │ [Cancel] [Create/     │  │
│                    │ └──────────┘ │  │          Update]      │  │
│                    └──────────────┘  └───────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ apiFetch() — wrapper that attaches X-API-Key header      │   │
│  │ getApiKey() — reads from sessionStorage                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS (JSON)
                             │ X-API-Key header
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                        │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Middleware Stack                        │  │
│  │  1. CORSMiddleware (allow all origins)                    │  │
│  │  2. APIKeyMiddleware (validate X-API-Key)                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Route Handlers                          │  │
│  │                                                            │  │
│  │  GET  /              → root (health check, API info)       │  │
│  │  GET  /artworks      → list with filters                   │  │
│  │  GET  /artworks/{id} → get single artwork                  │  │
│  │  POST /artworks      → create new artwork                  │  │
│  │  PUT  /artworks/{id} → update existing artwork             │  │
│  │  DELETE /artworks/{id} → delete artwork                    │  │
│  │  GET  /types         → list unique artwork types           │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   Pydantic Models                          │  │
│  │  Artwork / ArtworkCreate / ArtworkUpdate / ArtworksResponse│  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   Data Access Layer                        │  │
│  │  PyMongo → MongoDB Atlas (artworks_db.artworks)            │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Domain Model

```
┌──────────────────────────────┐
│          Artwork             │
├──────────────────────────────┤
│ id: string (8-char UUID)     │
│ title: string                │
│ description: string          │
│ types: string[]              │
│ price: float                 │
│ dimensions: string           │
│ year: int                    │
│ available: bool              │
│ image_url: string            │
└──────────────────────────────┘

Known types: watercolor, mixed-media, large-canvas,
             featured, acrylic, oil, print
```

### 3.3 Frontend State Model

```
App Component State
├── Authentication
│   ├── apiKey (string)          ← mirrors sessionStorage
│   ├── passwordInput (string)   ← controlled input
│   ├── loginError (string)      ← error message
│   └── loggingIn (bool)         ← loading flag
├── Data
│   ├── artworks (Artwork[])     ← from GET /artworks
│   ├── types (string[])         ← from GET /types
│   ├── loading (bool)
│   └── error (string | null)
├── Filters
│   ├── filterType (string)
│   └── filterAvailable (string)
├── Modal
│   ├── showModal (bool)
│   └── editingArtwork (Artwork | null)
└── Form
    └── formData (ArtworkCreate)
```

---

## 4. Process View

The Process View describes runtime behavior, concurrency, and request flows.

### 4.1 Request Lifecycle

```
Browser                    Vercel CDN              Render                 MongoDB Atlas
  │                           │                      │                        │
  │── GET artworks-ui.vercel.app ──▶│                │                        │
  │◀── static HTML/JS/CSS ───│                      │                        │
  │                           │                      │                        │
  │── GET /artworks ──────────────────────────────▶ │                        │
  │   (X-API-Key header)      │                      │                        │
  │                           │              CORSMiddleware                   │
  │                           │              APIKeyMiddleware                 │
  │                           │              (validate key)                   │
  │                           │                      │── find(query) ────────▶│
  │                           │                      │◀── documents ─────────│
  │                           │                      │                        │
  │◀── 200 JSON ─────────────────────────────────── │                        │
  │                           │                      │                        │
```

### 4.2 Authentication Flow

```
┌──────────┐                    ┌──────────┐                  ┌──────────┐
│ Browser  │                    │ Frontend │                  │ Backend  │
└────┬─────┘                    └────┬─────┘                  └────┬─────┘
     │  navigate to app              │                             │
     │──────────────────────────────▶│                             │
     │                               │                             │
     │  render password screen       │                             │
     │◀──────────────────────────────│                             │
     │                               │                             │
     │  submit password              │                             │
     │──────────────────────────────▶│                             │
     │                               │  GET /artworks              │
     │                               │  X-API-Key: <password>      │
     │                               │────────────────────────────▶│
     │                               │                             │
     │                               │  200 OK (valid)             │
     │                               │◀────────────────────────────│
     │                               │                             │
     │                               │  sessionStorage.set(key)    │
     │                               │  setState(apiKey)           │
     │  render dashboard             │                             │
     │◀──────────────────────────────│                             │
     │                               │                             │

     ─ ─ ─ ─ ─  ON LOGOUT  ─ ─ ─ ─ ─

     │  click Logout                 │                             │
     │──────────────────────────────▶│                             │
     │                               │  sessionStorage.remove()    │
     │                               │  setState(apiKey='')        │
     │  render password screen       │                             │
     │◀──────────────────────────────│                             │
```

### 4.3 Middleware Pipeline

Every incoming HTTP request to the backend traverses this pipeline:

```
Incoming Request
      │
      ▼
┌─────────────────────┐
│  CORSMiddleware     │  Adds Access-Control-* headers
│  (outermost)        │  Handles OPTIONS preflight
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  APIKeyMiddleware   │  Checks X-API-Key header
│                     │  Exempt: /, /docs, /redoc,
│                     │          /openapi.json, OPTIONS
│                     │  Returns 401 if invalid
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  FastAPI Router     │  Matches path → handler
│                     │  Pydantic validation
│                     │  Returns JSON response
└─────────────────────┘
```

Note: In Starlette/FastAPI, middleware added later wraps earlier middleware. `APIKeyMiddleware` is added after `CORSMiddleware`, so CORS headers are applied even to 401 responses — this is correct and necessary for the browser to read the error.

---

## 5. Development View

The Development View describes source code organization, build processes, and developer workflows.

### 5.1 Repository Structure

```
GitHub: aravindmurari/
├── artworks-api/                    (private repo)
│   ├── main.py                      Single-file FastAPI app (284 lines)
│   ├── requirements.txt             Python dependencies (5 packages)
│   ├── data/
│   │   └── artworks.json            Seed data (6 artworks)
│   ├── render.yaml                  Render deployment blueprint
│   ├── .env                         Local secrets (gitignored)
│   └── .gitignore
│
└── artworks-ui/                     (private repo)
    ├── src/
    │   ├── main.jsx                 React entry point
    │   ├── App.jsx                  Entire app in one component (587 lines)
    │   ├── App.css                  Empty (Tailwind used instead)
    │   └── index.css                Tailwind import + body reset
    ├── index.html                   HTML shell
    ├── package.json                 Node dependencies
    ├── vite.config.js               Vite build config
    ├── tailwind.config.js           Tailwind content paths
    ├── postcss.config.js            PostCSS plugin config
    ├── eslint.config.js             Linting rules
    └── .gitignore
```

### 5.2 Local Development Setup

**Backend:**
```bash
cd ~/artworks-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Create .env with MONGODB_URI and API_KEY
uvicorn main:app --reload        # http://localhost:8000
```

**Frontend:**
```bash
cd ~/artworks-ui
npm install
npm run dev                       # http://localhost:5173
```

The frontend defaults `API_URL` to `http://localhost:8000` when `VITE_API_URL` is not set, so both services work together locally out of the box.

### 5.3 Build Pipeline

**Backend** — No build step. Python source is interpreted directly.

**Frontend:**
```
src/*.jsx  ──▶  Vite (esbuild)  ──▶  dist/
                    │                  ├── index.html
                    │                  └── assets/
                    │                      ├── index-*.css  (13.6 KB gzipped: 3.6 KB)
                    │                      └── index-*.js   (205 KB gzipped: 63 KB)
                    │
              Tailwind CSS (PostCSS)
              scans src/ for utility classes
              tree-shakes unused styles
```

### 5.4 Dependency Overview

**Backend (Python):**

| Package        | Purpose                              |
|----------------|--------------------------------------|
| fastapi        | Web framework, routing, validation   |
| uvicorn        | ASGI server                          |
| pydantic       | Request/response model validation    |
| pymongo        | MongoDB driver                       |
| python-dotenv  | Load .env file                       |

**Frontend (Node.js):**

| Package            | Purpose                          |
|--------------------|----------------------------------|
| react              | UI library                       |
| react-dom          | DOM rendering                    |
| vite               | Build tool & dev server          |
| tailwindcss        | Utility-first CSS framework      |
| postcss            | CSS transformation pipeline      |
| autoprefixer       | CSS vendor prefixing             |
| eslint             | Code linting                     |

---

## 6. Physical / Deployment View

### 6.1 Deployment Architecture

```
┌─────────────┐     HTTPS      ┌──────────────────┐
│   Browser   │ ◀──────────── │   Vercel CDN      │
│             │               │   (Edge Network)   │
│             │               │                    │
│  React SPA  │               │  artworks-ui       │
│  (client)   │               │  Static files:     │
│             │               │  HTML, JS, CSS     │
└──────┬──────┘               └──────────────────-─┘
       │
       │  HTTPS (API calls)
       │  X-API-Key header
       │
       ▼
┌──────────────────┐           ┌──────────────────┐
│   Render         │           │  MongoDB Atlas    │
│   (Oregon, US)   │           │  (Cloud)          │
│                  │  pymongo  │                   │
│  artworks-api    │──────────▶│  Cluster0         │
│  Python/uvicorn  │           │  artworks_db      │
│  Free tier       │           │    .artworks      │
└──────────────────┘           └──────────────────┘
```

### 6.2 Infrastructure Details

| Component      | Provider       | Plan   | Region          | URL                                        |
|----------------|----------------|--------|-----------------|---------------------------------------------|
| Frontend       | Vercel         | Free   | Edge (global)   | https://artworks-ui.vercel.app              |
| Backend        | Render         | Free   | Oregon, US      | https://artworks-api-xjds.onrender.com      |
| Database       | MongoDB Atlas  | Free   | Cloud           | cluster0.tomkter.mongodb.net                |
| Source Code    | GitHub         | Free   | —               | github.com/aravindmurari/artworks-*         |

### 6.3 Deployment Triggers

| Service  | Trigger                              | Method                     |
|----------|--------------------------------------|----------------------------|
| Backend  | Push to `main` on `artworks-api`     | Render Blueprint auto-sync |
| Backend  | Manual                               | Render dashboard button    |
| Frontend | `vercel --prod` CLI                  | Vercel CLI deploy          |
| Frontend | Manual                               | Vercel dashboard           |

### 6.4 Free Tier Constraints

| Constraint                    | Impact                                              |
|-------------------------------|-----------------------------------------------------|
| Render free tier spin-down    | First request after 15 min idle takes 30-50 seconds |
| Render 750 free hours/month   | Sufficient for a single low-traffic service         |
| MongoDB Atlas 512 MB storage  | Sufficient for artwork metadata                     |
| Vercel 100 GB bandwidth/month | More than enough for a small SPA                    |

---

## 7. Data View

### 7.1 Database Schema

**Database:** `artworks_db`
**Collection:** `artworks`

| Field       | Type       | Required | Default   | Notes                            |
|-------------|------------|----------|-----------|----------------------------------|
| `_id`       | ObjectId   | auto     | auto      | MongoDB internal ID (stripped from API responses) |
| `id`        | string     | yes      | generated | 8-character UUID prefix          |
| `title`     | string     | yes      | —         |                                  |
| `description` | string   | yes      | —         |                                  |
| `types`     | string[]   | yes      | —         | e.g., ["watercolor", "featured"] |
| `price`     | float      | yes      | —         | USD, must be >= 0                |
| `dimensions`| string     | yes      | —         | e.g., "16x20 inches"            |
| `year`      | int        | yes      | —         | 1900-2099                        |
| `available` | bool       | yes      | true      |                                  |
| `image_url` | string     | yes      | ""        | Full URL to image                |

### 7.2 MongoDB Queries Used

| Operation        | MongoDB Method                   | Query Pattern                              |
|------------------|----------------------------------|--------------------------------------------|
| List (filtered)  | `collection.find(query)`         | `{types: {$regex}, available, price: {$gte/$lte}, year}` |
| Count total      | `collection.count_documents({})` | No filter                                  |
| Get by ID        | `collection.find_one()`          | `{id: artwork_id}`                         |
| Create           | `collection.insert_one()`        | Full document                              |
| Update           | `collection.find_one_and_update()` | `{id}, {$set: partial_data}`             |
| Delete           | `collection.find_one_and_delete()` | `{id: artwork_id}`                       |
| Distinct types   | `collection.distinct("types")`   | All unique values in types arrays          |

### 7.3 Seed Data

The application ships with 6 seed artworks in `data/artworks.json`. On first startup, if the `artworks` collection is empty, these are automatically inserted.

| ID | Title               | Types                              | Price  | Year | Available |
|----|---------------------|------------------------------------|--------|------|-----------|
| 1  | Misty Sunlight      | watercolor, featured               | $450   | 2024 | Yes       |
| 2  | Urban Dreams        | mixed-media, large-canvas          | $800   | 2024 | Yes       |
| 3  | Morning Bloom       | watercolor                         | $320   | 2023 | Yes       |
| 4  | Ethereal Landscape  | watercolor, mixed-media, featured  | $650   | 2024 | No        |
| 5  | Ocean's Whisper     | watercolor, large-canvas, featured | $1,200 | 2024 | Yes       |
| 6  | Abstract Emotions   | mixed-media                        | $550   | 2023 | Yes       |

---

## 8. Security View

### 8.1 Authentication Mechanism

```
┌─────────────────────────────────────────────────────────┐
│                  Authentication Flow                     │
│                                                         │
│  Shared password (API_KEY env var on backend)            │
│                     │                                    │
│                     ▼                                    │
│  User enters password in frontend login screen           │
│                     │                                    │
│                     ▼                                    │
│  Frontend sends as X-API-Key HTTP header                 │
│                     │                                    │
│                     ▼                                    │
│  Backend APIKeyMiddleware compares against API_KEY        │
│                     │                                    │
│              ┌──────┴──────┐                             │
│              │             │                             │
│          Match          No Match                         │
│              │             │                             │
│         Pass through   Return 401                        │
│         to handler     JSON error                        │
│                                                         │
│  On success: password stored in sessionStorage           │
│  (cleared on tab close or explicit logout)               │
└─────────────────────────────────────────────────────────┘
```

### 8.2 Protected vs. Public Endpoints

| Endpoint          | Method  | Auth Required | Rationale                        |
|-------------------|---------|---------------|----------------------------------|
| `/`               | GET     | No            | Health check / API info          |
| `/docs`           | GET     | No            | Swagger UI for testing           |
| `/redoc`          | GET     | No            | Alternative API docs             |
| `/openapi.json`   | GET     | No            | OpenAPI spec (needed by /docs)   |
| `/artworks`       | GET     | **Yes**       | List artworks                    |
| `/artworks/{id}`  | GET     | **Yes**       | Get single artwork               |
| `/artworks`       | POST    | **Yes**       | Create artwork                   |
| `/artworks/{id}`  | PUT     | **Yes**       | Update artwork                   |
| `/artworks/{id}`  | DELETE  | **Yes**       | Delete artwork                   |
| `/types`          | GET     | **Yes**       | List types                       |
| `*`               | OPTIONS | No            | CORS preflight requests          |

### 8.3 Security Considerations

| Area                  | Current State                          | Notes                                     |
|-----------------------|----------------------------------------|-------------------------------------------|
| Auth method           | Shared password via header             | Simple but sufficient for friend/co-worker access |
| Password storage      | `sessionStorage` (client)              | Cleared on tab close, not persisted        |
| Transport             | HTTPS enforced by Vercel/Render        | Passwords encrypted in transit             |
| CORS                  | `allow_origins=["*"]`                  | Should restrict to Vercel domain in production |
| API key in env        | Server-side only, not in client code   | User types it in, never bundled in JS      |
| `.env` gitignored     | Yes                                    | Credentials not in source control          |
| Swagger UI            | Publicly accessible with Authorize btn | Useful for development, could restrict     |
| Rate limiting         | None                                   | Could add for brute-force protection       |
| Input validation      | Pydantic models on backend             | Type and constraint checking               |

### 8.4 Graceful Session Handling

The frontend handles expired or invalid sessions gracefully:
- If any `apiFetch()` call returns HTTP 401, the app clears `sessionStorage` and resets to the password screen
- This covers cases where the `API_KEY` is rotated on the backend while a user has an old key stored

---

## 9. API Reference

### Base URL
- Local: `http://localhost:8000`
- Production: `https://artworks-api-xjds.onrender.com`

### Authentication
All endpoints (except exempted ones) require:
```
X-API-Key: <shared-password>
```

### Endpoints

#### `GET /`
Health check and API information.
```json
{
  "message": "Welcome to the Artworks API",
  "docs": "/docs",
  "endpoints": { ... }
}
```

#### `GET /artworks`
List artworks with optional filters.

| Parameter   | Type   | Description                    |
|-------------|--------|--------------------------------|
| `type`      | string | Filter by type (case-insensitive) |
| `available` | bool   | Filter by availability         |
| `min_price` | float  | Minimum price (>= 0)          |
| `max_price` | float  | Maximum price (>= 0)          |
| `year`      | int    | Filter by year                 |

Response:
```json
{
  "total": 6,
  "filtered_count": 3,
  "artworks": [ ... ]
}
```

#### `GET /artworks/{artwork_id}`
Get a single artwork by ID. Returns `404` if not found.

#### `POST /artworks`
Create a new artwork. Body: `ArtworkCreate` JSON. Returns `201` with created artwork.

#### `PUT /artworks/{artwork_id}`
Partial update. Body: `ArtworkUpdate` JSON (only include changed fields). Returns `400` if no fields, `404` if not found.

#### `DELETE /artworks/{artwork_id}`
Delete an artwork. Returns `404` if not found.
```json
{
  "message": "Artwork 'Title' deleted successfully",
  "deleted_id": "abc123"
}
```

#### `GET /types`
List all unique artwork types.
```json
{
  "types": ["featured", "large-canvas", "mixed-media", "watercolor"],
  "count": 4
}
```

---

## 10. Technology Stack

### Frontend

| Technology       | Version  | Purpose                                |
|------------------|----------|----------------------------------------|
| React            | 19.2     | UI library (hooks, functional components) |
| Vite             | 5.4      | Build tool, dev server, HMR            |
| Tailwind CSS     | 4.1      | Utility-first CSS framework            |
| PostCSS          | 8.5      | CSS processing pipeline                |
| ESLint           | 9.39     | Code quality linting                   |

### Backend

| Technology       | Version  | Purpose                                |
|------------------|----------|----------------------------------------|
| Python           | 3.9+     | Runtime (3.13 on Render)               |
| FastAPI          | 0.109+   | Web framework                          |
| Uvicorn          | 0.27+    | ASGI server                            |
| Pydantic         | 2.5+     | Data validation                        |
| PyMongo          | 4.6+     | MongoDB driver                         |
| python-dotenv    | 1.0+     | Environment variable loading           |

### Infrastructure

| Service          | Purpose                                    |
|------------------|--------------------------------------------|
| GitHub           | Source code hosting (2 private repos)       |
| Vercel           | Frontend hosting (CDN, edge deployment)    |
| Render           | Backend hosting (Python web service)       |
| MongoDB Atlas    | Cloud database                             |

### Developer Tools

| Tool             | Purpose                                    |
|------------------|--------------------------------------------|
| gh CLI           | GitHub operations from terminal            |
| Vercel CLI       | Frontend deployment from terminal          |

---

## 11. Configuration & Environment

### 11.1 Environment Variables

**Backend (Render):**

| Variable      | Required | Example                          | Description                  |
|---------------|----------|----------------------------------|------------------------------|
| `MONGODB_URI` | Yes      | `mongodb+srv://...`              | MongoDB connection string    |
| `API_KEY`     | No*      | `kepram-art-2024`                | Shared password for auth     |
| `PORT`        | Auto     | `10000`                          | Set by Render automatically  |

\* If `API_KEY` is not set, all endpoints are publicly accessible (useful for local dev without auth).

**Frontend (Vercel):**

| Variable       | Required | Example                                    | Description              |
|----------------|----------|--------------------------------------------|--------------------------|
| `VITE_API_URL` | Yes      | `https://artworks-api-xjds.onrender.com`   | Backend API base URL     |

**Local Development (`.env` file in `artworks-api/`):**
```
MONGODB_URI=mongodb+srv://...
API_KEY=kepram-art-2024
```

### 11.2 Frontend Configuration Files

| File                | Purpose                                         |
|---------------------|-------------------------------------------------|
| `vite.config.js`    | Enables React plugin for JSX + Fast Refresh     |
| `tailwind.config.js`| Defines content paths for class scanning        |
| `postcss.config.js` | Registers Tailwind PostCSS plugin               |
| `eslint.config.js`  | React hooks and refresh linting rules           |

---

## 12. Known Constraints & Trade-offs

### 12.1 Architectural Decisions

| Decision                           | Rationale                                          | Trade-off                                    |
|------------------------------------|----------------------------------------------------|----------------------------------------------|
| Single-file backend (`main.py`)    | Simplicity for a small API with 7 endpoints        | Would need refactoring if scope grows        |
| Single-component frontend (`App.jsx`) | All state in one place, easy to reason about    | 587 lines — could extract components         |
| Shared password (not per-user auth)| Simple to implement and share with friends          | No audit trail, no role-based access         |
| `sessionStorage` (not cookies)     | Clears on tab close for security                   | Must re-enter password for each new tab      |
| MongoDB (not SQL)                  | Flexible schema matches artwork data well           | No referential integrity enforcement         |
| No pagination                      | Small dataset (< 100 artworks expected)            | Would need pagination if collection grows    |
| Free tier hosting                  | Zero cost for a portfolio/personal project          | Cold starts, limited resources               |
| CORS `allow_origins=["*"]`         | Works with any frontend domain during development  | Should lock to Vercel domain in production   |

### 12.2 What's Not Implemented

| Feature                  | Why                                               |
|--------------------------|---------------------------------------------------|
| Image upload             | Images referenced by URL, hosted externally       |
| Pagination               | Dataset is small enough to return all at once      |
| Search (text)            | Not needed with current filter set                |
| User accounts            | Shared password is sufficient for target audience |
| Rate limiting            | Low traffic expected on free tier                 |
| Caching                  | MongoDB queries are fast for this data size       |
| Tests                    | Rapid prototype — would add for production use    |
| CI/CD pipeline           | Manual deploy is sufficient for current scale     |
| Error boundaries (React) | Simple `try/catch` + alert is sufficient          |
| TypeScript               | Would improve maintainability if scope grows      |

---

*Document generated: February 2026*
*Application version: 1.0.0*

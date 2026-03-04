# 🚛 Carrier Assure

> **Compliance intelligence platform** for freight carrier scoring — upload CCF files, detect changes via hash, and visualize composite safety scores in real-time.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [How to Run](#how-to-run)
- [API Reference](#api-reference)
- [Scoring Algorithm](#scoring-algorithm)
- [Design Decisions & Trade-offs](#design-decisions--trade-offs)
- [CI/CD Pipeline](#cicd-pipeline)
- [AI Assistance Policy](#ai-assistance-policy)

---

## 🧭 Overview

Carrier Assure ingests **CCF (Carrier Compliance File)** JSON files, computes a composite 0–100 safety score for each carrier, and tracks changes over time using SHA-256 hash-based diffing. The dashboard lets users upload a baseline file and a modified file side-by-side, instantly highlighting which carriers were rescored and by how much.

**Core capabilities:**

- 📥 Dual upload zones — baseline vs. modified CCF files
- 🔁 Hash-based change detection — only processes genuinely changed records
- 📊 Composite scoring across 6 safety factors
- 📈 Score history tracking per carrier
- 🔍 Real-time filtering and search
- ⚡ Auto-refresh after every upload

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│   Next.js (App Router) · single Dashboard component         │
│   CarrierService · UploadService · useCarriers · useToast   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP (fetch)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Django REST Framework                     │
│   CarrierViewSet · CCFUploadView · ScoreHistoryView         │
│   CCFProcessingService · RecordProcessor · ScoringService   │
│   DjangoCarrierRepository (ICarrierRepository)              │
└──────────────────────┬──────────────────────────────────────┘
                       │ ORM
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                       SQLite                                │
│   Carrier · ScoreHistory · CCFUpload                        │
└─────────────────────────────────────────────────────────────┘
```

### Backend layers

| Layer | Responsibility |
|---|---|
| **Views** | HTTP in/out, validation, serialization |
| **Services** | Orchestration — `CCFProcessingService` drives the full upload flow |
| **RecordProcessor** | Single-record processing: hash → score → upsert |
| **ScoringService** | Pure scoring logic, no I/O |
| **Repository** | All database access behind `ICarrierRepository` interface |
| **Models** | Django ORM models: `Carrier`, `ScoreHistory`, `CCFUpload` |

### Frontend layers

| Layer | Responsibility |
|---|---|
| **`CarrierService`** | All GET requests to the API |
| **`UploadService`** | File upload to `/api/ccf/upload/` |
| **`useCarriers`** | State management for carrier list + prev scores |
| **`useToast`** | Notification queue |
| **`Dashboard`** | Single root component, composes everything |

---

## 🛠️ Tech Stack

### Backend
- 🐍 **Python 3.12**
- 🎸 **Django 5.2** + **Django REST Framework**
- 🗄️ **SQLite** (via Django ORM)
- 📦 **Poetry** for dependency management
- 🧹 **ruff** + **black** for linting and formatting
- 🧪 **pytest** + **pytest-django** for testing

### Frontend
- ⚛️ **Next.js 15** (App Router)
- ⚡ **React 18** with hooks
- 🧪 **Vitest** + **Testing Library** for testing
- 🔍 **ESLint** for linting
- 🐳 **Docker** + **Nginx** for production

### Infrastructure
- 🐳 **Docker Compose** for local orchestration
- 🔄 **GitHub Actions** for CI/CD

---

## 📁 Project Structure

```
carrierassure/
├── backend/
│   ├── manage.py
│   ├── pyproject.toml
│   ├── ruff.toml
│   ├── pytest.ini
│   ├── Dockerfile
│   └── src/
│       ├── settings.py
│       ├── urls.py
│       └── scoring/
│           ├── models/
│           │   ├── carrier.py        # Carrier + ScoreHistory
│           │   └── ccf.py            # CCFUpload audit log
│           ├── repositories/
│           │   └── carrier.py        # ICarrierRepository + DjangoCarrierRepository
│           ├── services/
│           │   ├── ccf_processing.py # Orchestrator
│           │   └── scoring.py        # Pure scoring logic
│           ├── views/
│           │   ├── carrier_views.py
│           │   └── ccf_upload_view.py
│           └── tests/
│               ├── test_scoring.py
│               ├── test_hashing.py
│               ├── test_repositories.py
│               └── test_ccf_upload.py
│
├── frontend/
│   ├── app/
│   │   ├── layout.jsx
│   │   ├── page.jsx
│   │   └── dashboard.jsx             # Single component — full dashboard
│   ├── tests/
│   │   └── test_dashboard.jsx        # 50 unit tests
│   ├── vitest.config.js
│   ├── next.config.js
│   ├── eslint.config.js
│   └── Dockerfile
│
├── docker-compose.yml
└── .github/
    └── workflows/
        └── ci.yml
```

---

## 🚀 How to Run

### Prerequisites

- Docker + Docker Compose (or Podman)
- Node.js 20+ (for frontend dev)
- Python 3.12+ + Poetry (for backend dev)

---

### 🐳 With Docker Compose (recommended)

```bash
git clone https://github.com/your-org/carrierassure.git
cd carrierassure

docker compose up --build
```

- Frontend → http://localhost:3000
- Backend API → http://localhost:8000

---

### 🖥️ Backend (local dev)

```bash
cd backend

# Install dependencies
poetry install

# Run migrations
poetry run python manage.py migrate

# Start server
poetry run python manage.py runserver

# Run tests
poetry run pytest --tb=short -q

# Lint
poetry run ruff check .
poetry run black --check .

# Auto-fix
poetry run ruff check . --fix
poetry run black .
```

---

### 🌐 Frontend (local dev)

```bash
cd frontend

# Install dependencies
npm install

# Create env file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start dev server
npm run dev        # → http://localhost:3000

# Run tests
npm run test

# Lint
npm run lint

# Build for production
npm run build
```

---

### 🧪 Running All Tests

```bash
# Backend
cd backend && poetry run pytest --tb=short -q

# Frontend
cd frontend && npm run test
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/carriers/` | List all carriers. Supports `?authority_status=Active&min_score=50` |
| `GET` | `/api/carriers/:id/` | Get single carrier with score breakdown |
| `GET` | `/api/carriers/:id/history/` | Get score history for a carrier |
| `POST` | `/api/ccf/upload/` | Upload CCF JSON file. Returns processing summary |

### Upload response example

```json
{
  "total_records": 150,
  "new_count": 12,
  "updated_count": 38,
  "unchanged_count": 98,
  "error_count": 2
}
```

### Carrier object example

```json
{
  "id": "1",
  "carrier_id": "CA001",
  "legal_name": "Alpha Transport LLC",
  "dot_number": "1234567",
  "authority_status": "Active",
  "safety_rating": "Satisfactory",
  "score": 82.5,
  "score_breakdown": {
    "safety_rating_score": 20.0,
    "oos_pct_score": 16.0,
    "crash_total_score": 15.0,
    "driver_oos_pct_score": 12.0,
    "insurance_score": 10.0,
    "authority_status_score": 9.5
  }
}
```

---

## 🧮 Scoring Algorithm

The composite score is computed across **6 factors** with a max of **100 points**:

| Factor | Max Points | Description |
|---|---|---|
| Safety Rating | 25 | Satisfactory = 25, Conditional = 12, Unsatisfactory = 0 |
| OOS % (vehicles) | 20 | Lower out-of-service % = higher score |
| Crash Total | 20 | Penalizes crash history relative to fleet size |
| Driver OOS % | 15 | Lower driver out-of-service % = higher score |
| Insurance | 10 | Active, valid insurance coverage |
| Authority Status | 10 | Active = 10, Inactive = 5, Revoked = 0 |

**Score tiers:**

| Tier | Range | Color |
|---|---|---|
| 🟢 SAFE | > 70 | Green |
| 🟡 CAUTION | 40 – 70 | Yellow |
| 🔴 RISK | < 40 | Red |

---

## ⚖️ Design Decisions & Trade-offs

### 🔑 Hash-based change detection

**Decision:** Each CCF record is hashed (SHA-256 over a canonical JSON of relevant fields) before processing. Records whose hash matches the stored value are skipped entirely.

**Why:** Avoids redundant score recalculations and database writes on re-uploads of unchanged data. Enables efficient diffing without field-by-field comparison.

**Trade-off:** Hash collisions are astronomically unlikely but theoretically possible. Canonical field ordering must stay stable — any change to which fields are included breaks existing hashes and forces a full reprocess.

---

### 🗄️ SQLite over MongoDB

**Decision:** Switched from MongoDB (`django-mongodb-backend`) to SQLite.

**Why:** `django-mongodb-backend` had an active bug where `ContentType` instances with ObjectId PKs failed hashing in Django's `create_permissions` signal, requiring a monkey-patch in `manage.py`. SQLite with Django's standard ORM eliminates this complexity entirely with zero configuration. I didn't have enough time to resolve this issue and proceed with MongoDB, so I decided to get it working and deliver it with the remaining features.


**Trade-off:** SQLite doesn't scale horizontally. For production workloads with concurrent writes at high volume, PostgreSQL would be the right upgrade path — the repository pattern makes this a one-line settings change.

---

### 🏛️ Repository pattern

**Decision:** All database access goes through `ICarrierRepository`, with `DjangoCarrierRepository` as the concrete implementation.

**Why:** Decouples business logic from the ORM. Services and tests depend on the interface, not Django models. Makes swapping the database (e.g., SQLite → PostgreSQL) or mocking in tests trivial.

**Trade-off:** Adds a layer of indirection for a relatively small codebase. Worth it for testability and long-term maintainability.

---

### ⚛️ Single component frontend

**Decision:** The entire dashboard lives in one `dashboard.jsx` file with internal sub-components and hooks.

**Why:** Matches the project scope — one page, one feature. Internal composition (`ScoreRing`, `UploadZone`, `DetailPanel`) keeps related code co-located without the overhead of a full component library structure.

**Trade-off:** As the product grows, this file will need to be split. The service layer (`CarrierService`, `UploadService`) and hooks (`useCarriers`, `useToast`) are already isolated and can be extracted without touching the UI logic.

---

### 🔄 Vite → Next.js migration

**Decision:** Migrated from Vite + React to Next.js (App Router).

**Why:** Project requirements. All components that use hooks are marked `'use client'` — the current app is fully client-side rendered, so Next.js is used as a React framework with routing capabilities rather than for SSR/SSG specifically.

**Trade-off:** `import.meta.env` (Vite) replaced with `process.env.NEXT_PUBLIC_*` (Next.js). Build output changed from `dist/` to `.next/` requiring Dockerfile updates.

---

## 🔄 CI/CD Pipeline

The GitHub Actions pipeline runs on every push and PR to `main` and `develop`:

```
push / PR
    │
    ├── Backend CI
    │   ├── Setup Python 3.12 + Poetry
    │   ├── poetry run ruff check .
    │   ├── poetry run black --check .
    │   ├── python manage.py makemigrations --check --dry-run
    │   └── pytest --tb=short -q
    │
    └── Frontend CI
        ├── Setup Node 20
        ├── npm ci
        ├── npm run lint
        ├── npm run test
        └── npm run build
```

---

## 🤖 AI Assistance Policy

This project uses AI-assisted development with explicit attribution. Every section of code that was written or significantly modified with AI assistance is annotated:

```python
# --- AI-ASSISTED ---
# Tool: Claude Sonnet 4.6
# Prompt: "..."
# Modifications: ...
# --- END AI-ASSISTED ---
```

This applies to both backend (Python) and frontend (JavaScript) code, as well as CI configuration. The annotation includes the tool used, the original prompt, and any modifications made to the generated output.

---

## 📄 License

MIT

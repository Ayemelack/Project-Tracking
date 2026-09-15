# Project Tracking System — Phase 1

## Overview

A professional project cost and resource auditing system. Phase 1 implements **Estimate Document Ingestion** and the **Estimate Register**.

The system allows a user to upload a PDF estimate document, extract its contents (project info, line items, costs), review and correct the extraction, confirm the estimate, and save it to PostgreSQL.

## Architecture

```
┌─────────────────────┐         ┌─────────────────────────┐
│   React Frontend    │  HTTP   │    FastAPI Backend       │
│   (Vite + TS)       │◄──────►│    (Python 3.12)         │
│   Port: 5173        │         │    Port: 8000            │
└─────────────────────┘         └────────────┬────────────┘
                                             │
                                    ┌────────▼────────┐
                                    │    PostgreSQL    │
                                    │    Database      │
                                    └─────────────────┘
```

- **Frontend** and **Backend** are completely separated
- Frontend communicates with backend exclusively through HTTP APIs
- Frontend is deployable to Vercel/Netlify/Cloudflare Pages
- Backend is deployable to Render/Railway/Fly.io/AWS

## Technologies

| Layer       | Technology                            |
|-------------|---------------------------------------|
| Frontend    | React 19, TypeScript, Vite, Tailwind CSS 4 |
| Backend     | Python 3.12, FastAPI, SQLAlchemy 2, Alembic |
| Database    | PostgreSQL 16                         |
| PDF Parsing | pdfplumber                            |

## Project Structure

```
project-root/
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # Layout, shared components
│   │   ├── pages/          # Dashboard, Upload, Register, Detail
│   │   ├── services/       # API client
│   │   ├── types/          # TypeScript types
│   │   ├── App.tsx         # Router setup
│   │   └── main.tsx        # Entry point
│   ├── .env                # VITE_API_BASE_URL
│   └── package.json
├── backend/                # FastAPI backend
│   ├── app/
│   │   ├── api/v1/         # API routes
│   │   ├── core/           # Config, database, logging
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # PDF extraction, storage
│   │   ├── repositories/   # Database operations
│   │   └── main.py         # FastAPI app
│   ├── alembic/            # Database migrations
│   ├── tests/              # Backend tests
│   ├── storage/uploads/    # Uploaded PDF files
│   ├── .env                # DATABASE_URL, etc.
│   └── requirements.txt
└── README.md
```

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 16+

### 1. Install PostgreSQL

Download and install from https://www.postgresql.org/download/windows/

During installation, set a password for the `postgres` user. Default port is `5432`.

### 2. Create Database

```sql
CREATE DATABASE project_tracking;
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your PostgreSQL credentials

# Run database migrations (creates tables)
python -c "from app.core.database import engine, Base; from app.models.models import *; Base.metadata.create_all(bind=engine)"

# Start the backend
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
copy .env.example .env
# Edit .env if needed (default: http://localhost:8000)

# Start the frontend
npm run dev
```

### 5. Access

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Environment Variables

### Backend (.env)

| Variable        | Description                          | Default                                     |
|-----------------|--------------------------------------|---------------------------------------------|
| DATABASE_URL    | PostgreSQL connection string         | postgresql://postgres:postgres@localhost:5432/project_tracking |
| CORS_ORIGINS    | Allowed frontend origins (comma-sep) | http://localhost:5173,http://localhost:3000  |
| UPLOAD_MAX_SIZE | Max upload size in bytes             | 52428800 (50MB)                             |
| STORAGE_PATH    | Directory for uploaded files         | ./storage/uploads                           |
| ENVIRONMENT     | development/production               | development                                 |

### Frontend (.env)

| Variable          | Description              | Default                    |
|-------------------|--------------------------|----------------------------|
| VITE_API_BASE_URL | Backend API base URL     | http://localhost:8000       |

## API Endpoints

| Method   | Endpoint                          | Description                    |
|----------|-----------------------------------|--------------------------------|
| GET      | /api/v1/health                    | Health check                   |
| POST     | /api/v1/estimates/upload          | Upload and process PDF         |
| GET      | /api/v1/estimates                 | List all estimates             |
| GET      | /api/v1/estimates/{id}            | Get estimate with line items   |
| PUT      | /api/v1/estimates/{id}            | Update estimate metadata       |
| POST     | /api/v1/estimates/{id}/confirm    | Confirm an estimate            |
| DELETE   | /api/v1/estimates/{id}            | Delete an estimate             |
| PUT      | /api/v1/estimates/{id}/items/{item_id} | Update a line item      |
| POST     | /api/v1/estimates/{id}/items      | Add a line item                |
| DELETE   | /api/v1/estimates/{id}/items/{item_id} | Delete a line item      |

## PDF Extraction

### How It Works

1. User uploads a PDF via the upload page
2. Backend validates the file (type, size)
3. `pdfplumber` extracts text and tables from each page
4. Section headers are detected via regex pattern matching on character positions
5. Tables are parsed to extract line items (description, quantity, unit cost, total)
6. Currency values with "frs" suffix have dots treated as thousands separators
7. The summary page (grand total) is parsed separately
8. Extracted data is returned for user review

### Extraction Strategy

- Uses `pdfplumber` for text and table extraction (not OCR)
- Character-position-based section detection handles multi-table pages
- Currency parsing handles FCFA format: "72.000frs" → 72000
- Modular design allows adding new parsers for different document formats

### Tested With

- MOLA FAKO GENERAL ESTIMATE (10-page PDF, 13 sections, ~100 line items)
- Successfully extracts all section totals and grand total (16,768,565 FCFA)

## Database Schema

### estimates
| Column                  | Type         | Description                    |
|-------------------------|--------------|--------------------------------|
| id                      | UUID (PK)    | Unique identifier              |
| title                   | VARCHAR(500) | Estimate title                 |
| project_name            | VARCHAR(500) | Project name                   |
| reference_number        | VARCHAR(200) | Reference number               |
| contractor              | VARCHAR(500) | Contractor name                |
| client                  | VARCHAR(500) | Client name                    |
| currency                | VARCHAR(50)  | Currency (default: FCFA)       |
| original_filename       | VARCHAR(500) | Original uploaded filename     |
| stored_filename         | VARCHAR(500) | Safe stored filename           |
| status                  | VARCHAR(50)  | extracted/confirmed/rejected   |
| total_estimated_amount  | NUMERIC(15,2)| Total estimated amount         |
| notes                   | TEXT         | User notes                     |
| created_at              | TIMESTAMPTZ  | Creation timestamp             |
| updated_at              | TIMESTAMPTZ  | Last update timestamp          |

### estimate_line_items
| Column              | Type         | Description                    |
|---------------------|--------------|--------------------------------|
| id                  | UUID (PK)    | Unique identifier              |
| estimate_id         | UUID (FK)    | Reference to estimate          |
| item_number         | VARCHAR(50)  | Item number from document      |
| category            | VARCHAR(300) | Section/category name          |
| description         | TEXT         | Item description               |
| quantity            | NUMERIC(12,2)| Quantity                      |
| unit                | VARCHAR(50)  | Unit of measure                |
| unit_cost           | NUMERIC(15,2)| Unit cost                     |
| total_cost          | NUMERIC(15,2)| Total cost                     |
| source_page         | INTEGER      | Source page number             |
| section_total_type  | VARCHAR(50)  | material/labour/section_total/grand_total |
| created_at          | TIMESTAMPTZ  | Creation timestamp             |
| updated_at          | TIMESTAMPTZ  | Last update timestamp          |

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

## Deployment

### Frontend (Vercel/Netlify)

1. Set `VITE_API_BASE_URL` environment variable to your backend URL
2. Build command: `npm run build`
3. Output directory: `dist/`

### Backend (Render/Railway)

1. Set environment variables (DATABASE_URL, CORS_ORIGINS, etc.)
2. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Ensure PostgreSQL is accessible

## Known Limitations

1. **Foundation and Electrical Work sections** have no detail-page items in the PDF (only summary totals). These sections show as summary totals only.
2. **PDF text encoding**: Some special characters (e.g., "½") may not render correctly from PDF text extraction.
3. **No OCR support**: Only text-based PDFs are supported. Scanned/image PDFs require OCR (not implemented in Phase 1).
4. **Currency parsing ambiguity**: The parser uses heuristics to distinguish thousands separators from decimal points in FCFA values.

## Next Steps (Phase 2)

- Expense tracking and actual expenditure recording
- Budget-vs-actual analysis
- Resource consumption monitoring
- User authentication and authorization
- OCR support for scanned documents
- Export functionality (Excel, CSV)

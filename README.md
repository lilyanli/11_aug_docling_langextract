# Financial Document Extraction System

A full-stack application for extracting structured financial data from PDF documents using AI-powered vision processing.

## Project Structure

```
12-aug/
├── backend/              # Python-based extraction API
│   ├── api/             # Core extraction modules
│   ├── docs/            # Documentation and sample data
│   └── .venv/           # Python virtual environment
├── frontend/            # Next.js web application (coming soon)
└── README.md           # This file
```

## Features

- **AI-Powered Extraction**: Uses Google Gemini 2.5 Pro Vision for PDF processing
- **Multi-Page Analysis**: Extracts fund information and investment details from different pages
- **Structured Output**: Generates JSON, CSV, and PDF reports
- **Web Interface**: Next.js frontend for easy document upload and result viewing

## Quick Start

### Complete Setup

1. **Set up environment variables**:
   ```bash
   export GOOGLE_API_KEY="your_gemini_api_key"
   ```

2. **Start the backend API server**:
   ```bash
   cd backend
   source .venv/bin/activate
   pip install -r requirements.txt
   python start_server.py
   ```
   The API will be available at http://localhost:8000

3. **Start the frontend**:
   ```bash
   cd frontend
   pnpm install
   pnpm dev
   ```
   The frontend will be available at http://localhost:3000

4. **Upload and process documents**:
   - Drag and drop PDF files onto the frontend
   - Watch real-time processing progress
   - View extracted data in the preview section
   - Export results as CSV, JSON, or PDF

### Data Flow

1. **Drag & Drop** → Frontend uploads file to backend
2. **Backend Processing** → Gemini Vision converts PDF to markdown
3. **LangExtract** → Extracts structured data from markdown
4. **Data Preview** → Frontend displays extracted information
5. **Export** → Download CSV, JSON, or PDF reports

## Backend Documentation

See [backend/README.md](backend/README.md) for detailed backend documentation.

## Frontend Documentation

See [frontend/README.md](frontend/README.md) for detailed frontend documentation.

## Supported Document Types

- Private equity fund reports
- Credit fund reports  
- Investment schedules
- Portfolio valuations
- Financial statements

## Technology Stack

### Backend
- **Python 3.13**
- **Google Gemini 2.5 Pro Vision**
- **LangExtract**
- **PyMuPDF**
- **Pydantic**
- **Pandas**

### Frontend
- **Next.js** (coming soon)
- **React**
- **TypeScript**
- **Tailwind CSS**

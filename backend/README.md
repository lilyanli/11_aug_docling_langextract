# Vision-Based PDF Extraction Backend

A Python-based backend API for extracting structured financial data from PDF documents using Gemini Vision and LangExtract.

## Features

- **Vision-Based Extraction**: Uses Gemini 2.5 Pro Vision to convert PDF pages to structured markdown
- **Multi-Page Processing**: Extracts fund information from first page and investment details from schedule pages
- **Structured Data Output**: Converts extracted data to JSON, CSV, and PDF reports
- **No Docling Dependency**: Direct PDF-to-markdown conversion via Vision API

## Architecture

```
backend/
├── api/                    # Core API modules
│   ├── app.py             # Main application entry point
│   ├── pipeline.py        # Vision + LangExtract pipeline
│   ├── schema.py          # Pydantic data models
│   ├── exporter.py        # CSV/PDF export utilities
│   └── vision_extract.py  # Vision-based PDF extraction
├── docs/                  # Documentation and data
│   ├── prompts/           # LangExtract prompts and examples
│   ├── sample_docs/       # Sample PDF documents
│   ├── outputs/           # Generated outputs
│   └── docling_langextract/ # Legacy Docling-based approach
├── .venv/                 # Python virtual environment
└── requirements.txt       # Python dependencies
```

## Setup

1. **Install Dependencies**:
   ```bash
   cd backend
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   ```bash
   export GOOGLE_API_KEY="your_gemini_api_key"
   # or
   export LANGEXTRACT_API_KEY="your_langextract_api_key"
   ```

## Usage

### API Server (Recommended)

Start the FastAPI server for web interface integration:

```bash
# Install dependencies first
pip install -r requirements.txt

# Start the API server
python start_server.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Interactive docs**: http://localhost:8000/redoc

### Command Line Extraction

For direct command-line processing:

```bash
python api/app.py --pdf "docs/sample_docs/your_document.pdf"
```

### Custom Page Ranges

```bash
# Extract fund info from page 1 and investments from pages 7-8
python api/app.py --pdf "docs/sample_docs/your_document.pdf" --page-ranges "0:0" "6:7"
```

### Output Files

Each run generates:
- `outputs/run_YYYYMMDD_HHMMSS/`
  - `vision_markdown.md` - Raw markdown from Vision API
  - `normalized.json` - Structured data in JSON format
  - `extraction.jsonl` - LangExtract raw extractions
  - `review.html` - Interactive review interface
  - `csv/` - Relational CSV files
    - `fund.csv` - Fund information
    - `investments.csv` - Investment details
    - `fees.csv` - Fee structure
    - `contacts.csv` - Contact information
  - `report.pdf` - Human-readable PDF report

## Data Schema

### Fund Information
- `fund_name`: Fund name
- `fund_reporting_period`: Reporting date (YYYY-MM-DD)
- `vintage_year`: Fund vintage year
- `gp_name`: General partner name
- `domicile`: Fund domicile
- `strategy`: Investment strategy

### Investment Details
- `investment_name`: Company/project name
- `investment_type`: Type of investment
- `industry`: Industry/sector
- `country`: Geographic location
- `currency`: Currency (defaults to USD)
- `investment_cost`: Original investment amount
- `fair_value`: Current fair value
- `ownership`: Ownership percentage

## API Endpoints

The FastAPI server provides the following REST endpoints:

- `POST /api/upload` - Upload and process a document
- `GET /api/status/{job_id}` - Get processing status
- `GET /api/result/{file_hash}` - Get processing results
- `GET /api/history` - Get processing history
- `GET /api/download/{file_hash}/{filename}` - Download result files

### API Response Format

```json
{
  "job_id": "uuid",
  "state": "queued|processing|extracting|done|error",
  "progress": 0-100,
  "message": "Status message",
  "entities": {...},
  "downloads": {...},
  "preview": {...}
}
```

## Supported Document Types

- Private equity fund reports
- Credit fund reports
- Investment schedules
- Portfolio valuations
- Financial statements

## Technologies Used

- **Google Gemini 2.5 Pro Vision**: PDF-to-markdown conversion
- **LangExtract**: Structured data extraction
- **PyMuPDF**: PDF page extraction
- **Pydantic**: Data validation and serialization
- **Pandas**: CSV export
- **ReportLab**: PDF report generation

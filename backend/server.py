#!/usr/bin/env python3
"""
FastAPI server for document processing
Integrates with vision-based extraction pipeline
"""
import os
import uuid
import hashlib
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import aiofiles
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from pipeline import (
    setup_gemini,
    extract_pdf_pages_as_images,
    vision_to_markdown,
    load_prompt,
    load_examples,
    run_langextract,
    ensure_run_dir,
    save_outputs,
    normalize_to_schema,
)

# Initialize FastAPI app
app = FastAPI(title="Document Processing API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job storage (in production, use Redis or database)
jobs: Dict[str, Dict[str, Any]] = {}
results: Dict[str, Dict[str, Any]] = {}

def load_existing_results():
    """Load existing processed results from output directories"""
    outputs_dir = Path("outputs")
    if not outputs_dir.exists():
        return
    
    for run_dir in outputs_dir.iterdir():
        if not run_dir.is_dir() or not run_dir.name.startswith("run_"):
            continue
            
        normalized_path = run_dir / "normalized.json"
        if not normalized_path.exists():
            continue
            
        try:
            with open(normalized_path, 'r') as f:
                normalized_data = json.load(f)
            
            # Try to find the original file to get hash
            uploads_dir = Path("uploads")
            if uploads_dir.exists():
                for upload_file in uploads_dir.iterdir():
                    if upload_file.is_file():
                        # Read file content to compute hash
                        with open(upload_file, 'rb') as f:
                            file_content = f.read()
                        file_hash = compute_file_hash(file_content)
                        
                        # Create result entry
                        downloads = {
                            "csv": f"/api/download/{file_hash}/investments.csv",
                            "json": f"/api/download/{file_hash}/normalized.json", 
                            "pdf": f"/api/download/{file_hash}/report.pdf",
                        }
                        
                        investments = normalized_data.get("investments", [])
                        preview = {
                            "fund": {
                                "name": normalized_data.get("fund", {}).get("fund_name", "Unknown"),
                                "reporting_period": normalized_data.get("fund", {}).get("fund_reporting_period", "Not specified"),
                            },
                            "soi": [
                                {
                                    "name": inv.get("investment_name", ""),
                                    "type": inv.get("investment_type", ""),
                                    "industry": inv.get("industry", ""),
                                    "country": inv.get("country", ""),
                                    "cost": inv.get("investment_cost", 0),
                                    "fair_value": inv.get("fair_value", 0),
                                    "ownership": inv.get("ownership", None),
                                }
                                for inv in investments
                            ],
                            "summary": {
                                "total_investments": len(investments),
                                "total_cost": sum(inv.get("investment_cost", 0) or 0 for inv in investments),
                                "total_fair_value": sum(inv.get("fair_value", 0) or 0 for inv in investments),
                            }
                        }
                        
                        results[file_hash] = {
                            "hash": file_hash,
                            "filename": upload_file.name,
                            "doc_type": "fund_financials",
                            "entities": normalized_data,
                            "downloads": downloads,
                            "preview": preview,
                            "completedAt": datetime.now().isoformat(),
                            "run_dir": str(run_dir.absolute()),
                        }
                        print(f"✅ Loaded existing result: {upload_file.name}")
                        break
                        
        except Exception as e:
            print(f"Error loading result from {run_dir}: {e}")

# Pydantic models
class JobStatus(BaseModel):
    job_id: str
    state: str
    progress: int
    message: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    downloads: Optional[Dict[str, str]] = None
    preview: Optional[Dict[str, Any]] = None
    doc_type: Optional[str] = None
    hash: Optional[str] = None

class ProcessingResult(BaseModel):
    hash: str
    filename: str
    doc_type: str
    entities: Optional[Dict[str, Any]] = None
    downloads: Dict[str, str]
    preview: Optional[Dict[str, Any]] = None
    completedAt: str

def compute_file_hash(file_content: bytes) -> str:
    """Compute SHA256 hash of file content"""
    return hashlib.sha256(file_content).hexdigest()

def infer_doc_type(filename: str) -> str:
    """Infer document type from filename"""
    name = filename.lower()
    if any(keyword in name for keyword in ["fund", "soi", "financial"]):
        return "fund_financials"
    elif any(keyword in name for keyword in ["investor", "report"]):
        return "investor_report"
    return "generic"

# Load existing results on startup (after function definitions)
# Disabled for demo - each unique document will be processed fresh
# load_existing_results()

async def process_document_async(job_id: str, file_path: Path, filename: str, file_hash: str):
    """Background task to process document"""
    try:
        # Update job status
        jobs[job_id]["state"] = "processing"
        jobs[job_id]["progress"] = 10
        jobs[job_id]["message"] = "Setting up processing pipeline..."

        # Create output directory
        run_dir = ensure_run_dir()
        jobs[job_id]["run_dir"] = str(run_dir)
        jobs[job_id]["progress"] = 20
        jobs[job_id]["message"] = "Converting PDF pages to markdown..."

        # Step 1: PDF Pages -> Images -> Markdown via Gemini Vision
        model = setup_gemini()
        images = extract_pdf_pages_as_images(str(file_path), page_ranges=[(0, 0), (6, 7)])
        markdown_content = vision_to_markdown(model, images)
        
        if not markdown_content:
            raise Exception("Failed to convert PDF pages to markdown")
        
        # Save vision-generated markdown
        vision_markdown_path = run_dir / "vision_markdown.md"
        async with aiofiles.open(vision_markdown_path, 'w', encoding='utf-8') as f:
            await f.write(markdown_content)
        
        jobs[job_id]["progress"] = 40
        jobs[job_id]["message"] = "Loading extraction prompts and examples..."

        # Step 2: Load prompt & examples
        prompt = load_prompt("docs/prompts/fund_terms.md")
        examples = load_examples("docs/prompts/examples.jsonl")

        jobs[job_id]["progress"] = 60
        jobs[job_id]["message"] = "Running LangExtract on vision-generated markdown..."

        # Step 3: LangExtract on vision-generated markdown
        if not os.getenv("LANGEXTRACT_API_KEY") and os.getenv("GOOGLE_API_KEY"):
            os.environ["LANGEXTRACT_API_KEY"] = os.getenv("GOOGLE_API_KEY")
        
        # Check API keys
        api_key = os.getenv("LANGEXTRACT_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise Exception("No API key found. Please set LANGEXTRACT_API_KEY or GOOGLE_API_KEY")
        
        print(f"Running LangExtract with API key: {api_key[:10]}...")
        result = run_langextract(markdown_content, prompt, examples)
        
        if not result:
            raise Exception("LangExtract returned no result")

        jobs[job_id]["progress"] = 80
        jobs[job_id]["message"] = "Saving extraction artifacts..."

        # Step 4: Save artifacts (JSONL + HTML viz)
        save_outputs(result, run_dir)

        jobs[job_id]["progress"] = 90
        jobs[job_id]["message"] = "Normalizing to schema..."

        # Step 5: Normalize to schema
        model_data = normalize_to_schema(result, run_dir)

        jobs[job_id]["progress"] = 95
        jobs[job_id]["message"] = "Preparing exports..."

        # Step 6: Export to CSV and PDF
        from exporter import to_relational_rows, write_csvs, write_pdf_report
        
        fund_id = run_dir.name
        tables = to_relational_rows(model_data, fund_id=fund_id)
        csv_dir = run_dir / "csv"
        write_csvs(tables, csv_dir)
        write_pdf_report(model_data, run_dir / "report.pdf", fund_id=fund_id)

        # Prepare downloads
        downloads = {
            "csv": f"/api/download/{file_hash}/investments.csv",
            "json": f"/api/download/{file_hash}/normalized.json",
            "pdf": f"/api/download/{file_hash}/report.pdf",
        }

        # Create preview data
        preview = {
            "fund": {
                "name": model_data.fund.fund_name,
                "reporting_period": model_data.fund.fund_reporting_period,
            },
            "soi": [
                {
                    "name": inv.investment_name,
                    "type": inv.investment_type,
                    "industry": inv.industry,
                    "country": inv.country,
                    "cost": inv.investment_cost,
                    "fair_value": inv.fair_value,
                    "ownership": inv.ownership,
                }
                for inv in model_data.investments
            ],
            "summary": {
                "total_investments": len(model_data.investments),
                "total_cost": sum(inv.investment_cost or 0 for inv in model_data.investments),
                "total_fair_value": sum(inv.fair_value or 0 for inv in model_data.investments),
            }
        }

        # Update job status to completed
        jobs[job_id]["state"] = "done"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Processing completed successfully"
        jobs[job_id]["entities"] = model_data.model_dump()
        jobs[job_id]["downloads"] = downloads
        jobs[job_id]["preview"] = preview

        # Store result
        results[file_hash] = {
            "hash": file_hash,
            "filename": filename,
            "doc_type": jobs[job_id]["doc_type"],
            "entities": model_data.model_dump(),
            "downloads": downloads,
            "preview": preview,
            "completedAt": datetime.now().isoformat(),
            "run_dir": str(run_dir),
        }

    except Exception as e:
        import traceback
        jobs[job_id]["state"] = "error"
        jobs[job_id]["message"] = f"Processing failed: {str(e)}"
        print(f"Error processing job {job_id}: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        
        # Save error log to run directory
        if "run_dir" in jobs[job_id]:
            error_log_path = Path(jobs[job_id]["run_dir"]) / "error.log"
            with open(error_log_path, 'w') as f:
                f.write(f"Error: {e}\n")
                f.write(f"Traceback: {traceback.format_exc()}")

@app.post("/api/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload and process a document"""
    try:
        # Read file content
        file_content = await file.read()
        file_hash = compute_file_hash(file_content)
        
        # Check if already processed
        if file_hash in results:
            return JSONResponse({
                "job_id": f"cached-{file_hash}",
                "doc_type": results[file_hash]["doc_type"],
                "message": "File already processed, returning cached result"
            })

        # Create job
        job_id = str(uuid.uuid4())
        doc_type = infer_doc_type(file.filename)
        
        jobs[job_id] = {
            "id": job_id,
            "hash": file_hash,
            "filename": file.filename,
            "startedAt": datetime.now().isoformat(),
            "state": "queued",
            "progress": 0,
            "doc_type": doc_type,
            "message": "Job created, starting processing..."
        }

        # Save uploaded file
        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)
        file_path = uploads_dir / f"{file_hash}_{file.filename}"
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)

        # Start background processing
        background_tasks.add_task(process_document_async, job_id, file_path, file.filename, file_hash)

        return JSONResponse({
            "job_id": job_id,
            "doc_type": doc_type
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get processing status"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return JobStatus(
        job_id=job["id"],
        state=job["state"],
        progress=job["progress"],
        message=job.get("message"),
        entities=job.get("entities"),
        downloads=job.get("downloads"),
        preview=job.get("preview"),
        doc_type=job.get("doc_type"),
        hash=job.get("hash")
    )

@app.get("/api/result/{file_hash}")
async def get_result(file_hash: str):
    """Get processing result by file hash"""
    if file_hash not in results:
        raise HTTPException(status_code=404, detail="Result not found")
    
    result = results[file_hash]
    return ProcessingResult(
        hash=result["hash"],
        filename=result["filename"],
        doc_type=result["doc_type"],
        entities=result["entities"],
        downloads=result["downloads"],
        preview=result["preview"],
        completedAt=result["completedAt"]
    )

@app.get("/api/history")
async def get_history(limit: int = 5):
    """Get processing history"""
    history_items = list(results.values())[:limit]
    return {"items": history_items}

@app.get("/api/download/{file_hash}/{filename}")
async def download_file(file_hash: str, filename: str):
    """Download processed files"""
    if file_hash not in results:
        raise HTTPException(status_code=404, detail="File not found")
    
    result = results[file_hash]
    run_dir = Path(result["run_dir"])
    
    if filename == "normalized.json":
        file_path = run_dir / "normalized.json"
    elif filename == "investments.csv":
        file_path = run_dir / "csv" / "investments.csv"
    elif filename == "report.pdf":
        file_path = run_dir / "report.pdf"
    else:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Document Processing API is running", "version": "1.0.0"}

@app.post("/api/add-result")
async def add_manual_result():
    """Manually add the Peak Credit Fund result"""
    try:
        file_hash = "f85dfb9f8e0edaccaf702ff12e6b5d1eee7c7a985849d0dc51fc56dda425c057"
        filename = "PEAK Credit Fund I_2024Q1_Investor Report.pdf"
        run_dir = Path("outputs/run_20250812_201306")
        
        # Load the normalized data
        normalized_path = run_dir / "normalized.json"
        if not normalized_path.exists():
            raise HTTPException(status_code=404, detail="Normalized data not found")
        
        with open(normalized_path, 'r') as f:
            normalized_data = json.load(f)
        
        # Create downloads URLs
        downloads = {
            "csv": f"/api/download/{file_hash}/investments.csv",
            "json": f"/api/download/{file_hash}/normalized.json", 
            "pdf": f"/api/download/{file_hash}/report.pdf",
        }
        
        # Create preview data
        investments = normalized_data.get("investments", [])
        preview = {
            "fund": {
                "name": normalized_data.get("fund", {}).get("fund_name", "Unknown"),
                "reporting_period": normalized_data.get("fund", {}).get("fund_reporting_period", "Not specified"),
            },
            "soi": [
                {
                    "name": inv.get("investment_name", ""),
                    "type": inv.get("investment_type", ""),
                    "industry": inv.get("industry", ""),
                    "country": inv.get("country", ""),
                    "cost": inv.get("investment_cost", 0),
                    "fair_value": inv.get("fair_value", 0),
                    "ownership": inv.get("ownership", None),
                }
                for inv in investments
            ],
            "summary": {
                "total_investments": len(investments),
                "total_cost": sum(inv.get("investment_cost", 0) or 0 for inv in investments),
                "total_fair_value": sum(inv.get("fair_value", 0) or 0 for inv in investments),
            }
        }
        
        # Add to results
        results[file_hash] = {
            "hash": file_hash,
            "filename": filename,
            "doc_type": "fund_financials",
            "entities": normalized_data,
            "downloads": downloads,
            "preview": preview,
            "completedAt": datetime.now().isoformat(),
            "run_dir": str(run_dir.absolute()),
        }
        
        return {"message": "Result added successfully", "investments_count": len(investments)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add result: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

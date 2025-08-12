#!/usr/bin/env python3
"""
Vision-based pipeline: Gemini Vision + LangExtract
No Docling needed - direct PDF to markdown via Vision, then structured extraction
"""
import argparse
import os
from pathlib import Path
import json
import base64
from dotenv import load_dotenv
import google.generativeai as genai
import fitz  # PyMuPDF for PDF page extraction
import langextract as lx
from schema import FundDocExtraction, FundEntity, FeeTerms, KeyContacts, Investment
import re
import datetime

load_dotenv()

def setup_gemini():
    """Setup Gemini Vision API"""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("LANGEXTRACT_API_KEY")
    if not api_key:
        raise ValueError("Please set GOOGLE_API_KEY or LANGEXTRACT_API_KEY environment variable")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro')
    return model

def extract_pdf_pages_as_images(pdf_path: str, page_ranges: list = None) -> list:
    """
    Extract specific page ranges from PDF as images
    page_ranges: list of tuples [(start_page, end_page), ...] where pages are 0-indexed
    Default: [(0, 0), (6, 7)] - first page for fund info, pages 7-8 for investments
    """
    if page_ranges is None:
        page_ranges = [(0, 0), (6, 7)]  # Default: first page + investment pages
    
    doc = fitz.open(pdf_path)
    images = []
    
    for start_page, end_page in page_ranges:
        for page_num in range(start_page, end_page + 1):
            if page_num < len(doc):
                page = doc.load_page(page_num)
                # Render page as image with higher resolution
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # 2x zoom for better quality
                img_data = pix.tobytes("png")
                images.append({
                    "page": page_num + 1,  # Convert to 1-indexed for display
                    "image_data": img_data,
                    "page_type": "fund_info" if page_num == 0 else "investments"
                })
    
    doc.close()
    return images

def vision_to_markdown(model, images: list) -> str:
    """Use Gemini Vision to convert PDF pages to structured markdown"""
    
    # Separate fund info and investment pages
    fund_info_images = [img for img in images if img.get("page_type") == "fund_info"]
    investment_images = [img for img in images if img.get("page_type") == "investments"]
    
    markdown_content = ""
    
    # Extract fund information from first page
    if fund_info_images:
        fund_prompt = """
You are a financial data extraction expert. I have the first page of a fund report.

Please extract the fund name and reporting period from this page. Look for:
1. Fund name (usually in the title or header)
2. Reporting period/date (quarterly report date, year-end date, etc.)

Convert to markdown format:
### Fund Information
- **Fund Name**: [extract fund name]
- **Reporting Period**: [extract date in YYYY-MM-DD format if possible]

Please extract from the provided PDF page:
"""
        
        try:
            content_parts = [fund_prompt]
            for img in fund_info_images:
                content_parts.append({
                    "mime_type": "image/png",
                    "data": base64.b64encode(img["image_data"]).decode('utf-8')
                })
            
            response = model.generate_content(content_parts)
            markdown_content += response.text + "\n\n"
        except Exception as e:
            print(f"Error extracting fund info: {e}")
    
    # Extract investment details from investment pages
    if investment_images:
        investment_prompt = """
You are a financial data extraction expert. I have PDF pages showing investment details, portfolio valuation, or schedule of investments from a financial statement.

IMPORTANT: Only extract CURRENT investments from sections like "Unaudited Valuation Report", "Schedule of Investments", "Portfolio Holdings", or similar sections that show actual current investments. DO NOT extract from "Future Pipeline", "Investment Pipeline", "Deal Flow", or similar sections that show planned/future investments.

Please convert these pages to clean, structured markdown format that preserves the table structure and all investment information.

Requirements:
1. ONLY extract from current investment sections (e.g., "Unaudited Valuation Report")
2. IGNORE future pipeline sections (e.g., "Future Pipeline", "Investment Pipeline")
3. Preserve the hierarchical structure: Investment Type > Country > Industry > Company
4. Convert tables to proper markdown table format
5. Include all investment details:
   - Company/Project names
   - Investment types (Equities, Corporate Debt, Loans, etc.)
   - Industries/Sectors
   - Countries/Geographies (separate from currency)
   - Currencies (separate from country)
   - Investment costs
   - Fair values
   - Ownership percentages or other relevant metrics
6. Skip summary/total rows
7. Maintain the exact values as shown in the document
8. Use proper markdown table syntax with headers and separators
9. IMPORTANT: If a row has financial data but no company/project name is visible, use "Undisclosed" as the placeholder
10. Include all rows with financial data, even if names are not disclosed
11. CRITICAL: Currency and Country are separate fields - do not assume USD means United States

Example format:
| Investment Name | Investment Type | Industry | Country | Currency | Investment Cost | Fair Value | Interest/Fee Receivable | Total | Currency Exposure | Ownership % |
|----------------|----------------|----------|---------|----------|----------------|------------|------------------------|-------|-------------------|-------------|
| Company Name | Equities | Technology | Singapore | USD | $1,000,000 | $1,200,000 | $50,000 | $1,250,000 | USD | 5.2% |
| Undisclosed | Equities | Health Care | Vietnam | USD | $2,000,000 | $2,500,000 | $100,000 | $2,600,000 | USD | 8.1% |

Please convert the provided PDF pages to markdown, focusing ONLY on current investments:
"""
        
        try:
            content_parts = [investment_prompt]
            for img in investment_images:
                content_parts.append({
                    "mime_type": "image/png",
                    "data": base64.b64encode(img["image_data"]).decode('utf-8')
                })
            
            response = model.generate_content(content_parts)
            markdown_content += response.text
        except Exception as e:
            print(f"Error extracting investment details: {e}")
    
    return markdown_content
    
    try:
        # Prepare the content parts
        content_parts = [prompt]
        
        for img in images:
            content_parts.append({
                "mime_type": "image/png",
                "data": base64.b64encode(img["image_data"]).decode('utf-8')
            })
        
        response = model.generate_content(content_parts)
        return response.text
    except Exception as e:
        print(f"Error calling Gemini Vision API: {e}")
        return None

def load_prompt(path: str) -> str:
    return Path(path).read_text()

def load_examples(path: str):
    """
    Load examples.jsonl and convert to LangExtract example objects.
    """
    examples = []
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        # Build extractions list
        exts = []
        for e in row.get("extractions", []):
            exts.append(
                lx.data.Extraction(
                    extraction_class=e.get("extraction_class", "value"),
                    extraction_text=e.get("extraction_text", ""),
                    attributes=e.get("attributes", {}),
                )
            )
        examples.append(
            lx.data.ExampleData(
                text=row["text"],
                extractions=exts
            )
        )
    return examples

def run_langextract(clean_text: str, prompt_desc: str, examples):
    """
    Core extraction call using LangExtract on the vision-generated markdown
    """
    result = lx.extract(
        text_or_documents=clean_text,
        prompt_description=prompt_desc,
        examples=examples,
        model_id="gemini-2.5-pro",  # Use the same model for consistency
        extraction_passes=3,     # improves recall on long docs
        max_workers=8,           # parallel requests
        max_char_buffer=1000     # controls chunk size
    )
    return result

def ensure_run_dir(base: str = "outputs") -> Path:
    base_path = Path(base).resolve()
    base_path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base_path / f"run_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir

def save_outputs(result, run_dir: Path):
    """
    Save annotated JSONL (entities + spans) then create the HTML visualization.
    """
    run_dir.mkdir(parents=True, exist_ok=True)

    # Normalize result to a list of documents expected by langextract IO
    if isinstance(result, (list, tuple)):
        docs = list(result)
        # Some APIs return (result, meta)
        if len(docs) == 2 and hasattr(docs[0], "extractions") and not hasattr(docs[1], "extractions"):
            docs = [docs[0]]
    else:
        docs = [result]

    try:
        lx.io.save_annotated_documents(docs, output_name=str(run_dir / "extraction.jsonl"))
    except Exception as e:
        (run_dir / "extraction_error.txt").write_text(
            f"save_annotated_documents failed: {e}\n", encoding="utf-8"
        )
        return

    try:
        html = lx.visualize(str(run_dir / "extraction.jsonl"))
        (run_dir / "review.html").write_text(html, encoding="utf-8")
    except Exception as e:
        (run_dir / "visualize_error.txt").write_text(f"visualize failed: {e}\n", encoding="utf-8")

def normalize_to_schema(result, run_dir: Path):
    """
    Convert LangExtract's result into our Pydantic schema.
    """
    # Safely get list of extraction objects
    extractions = getattr(result, "extractions", [])
    
    data = {
        "fund": {},
        "investments": [],
        "fees": {},
        "contacts": [],
        "source_anchors": []
    }

    # Group investment extractions by investment name AND type
    investment_groups = {}
    current_investment_name = None
    current_investment_type = None

    for ext in extractions:
        cls = getattr(ext, "extraction_class", "")
        txt = getattr(ext, "extraction_text", "")
        attrs = getattr(ext, "attributes", {}) or {}

        # Fund-level fields
        if cls == "fund_name":
            data["fund"]["fund_name"] = txt
        elif cls == "fund_reporting_period":
            data["fund"]["fund_reporting_period"] = txt
        elif cls == "vintage_year":
            try:
                data["fund"]["vintage_year"] = int(re.sub(r"\D", "", txt))
            except Exception:
                data["fund"]["vintage_year"] = None
        elif cls == "domicile":
            data["fund"]["domicile"] = txt
        elif cls == "strategy":
            data["fund"]["strategy"] = txt
        elif cls == "gp_name":
            data["fund"]["gp_name"] = txt

        # Fee fields
        elif cls == "management_fee":
            data["fees"]["management_fee"] = txt
        elif cls == "carry":
            data["fees"]["carry"] = txt
        elif cls == "hurdle_rate":
            data["fees"]["hurdle_rate"] = txt
        elif cls == "catch_up":
            data["fees"]["catch_up"] = txt

        # Investment fields - group by investment name AND type
        elif cls == "investment_name":
            current_investment_name = txt
            if current_investment_type:
                unique_key = f"{txt}_{current_investment_type}"
            else:
                unique_key = txt
            if unique_key not in investment_groups:
                investment_groups[unique_key] = {"investment_name": txt}
        elif cls == "investment_type":
            current_investment_type = txt
            if current_investment_name:
                unique_key = f"{current_investment_name}_{txt}"
                if unique_key not in investment_groups:
                    investment_groups[unique_key] = {"investment_name": current_investment_name}
                investment_groups[unique_key]["investment_type"] = txt
        elif cls == "industry":
            if current_investment_name and current_investment_type:
                unique_key = f"{current_investment_name}_{current_investment_type}"
                if unique_key not in investment_groups:
                    investment_groups[unique_key] = {"investment_name": current_investment_name, "investment_type": current_investment_type}
                investment_groups[unique_key]["industry"] = txt
        elif cls == "country":
            if current_investment_name and current_investment_type:
                unique_key = f"{current_investment_name}_{current_investment_type}"
                if unique_key not in investment_groups:
                    investment_groups[unique_key] = {"investment_name": current_investment_name, "investment_type": current_investment_type}
                investment_groups[unique_key]["country"] = txt
        elif cls == "currency":
            if current_investment_name and current_investment_type:
                unique_key = f"{current_investment_name}_{current_investment_type}"
                if unique_key not in investment_groups:
                    investment_groups[unique_key] = {"investment_name": current_investment_name, "investment_type": current_investment_type}
                investment_groups[unique_key]["currency"] = txt
        elif cls == "investment_date":
            if current_investment_name and current_investment_type:
                unique_key = f"{current_investment_name}_{current_investment_type}"
                if unique_key not in investment_groups:
                    investment_groups[unique_key] = {"investment_name": current_investment_name, "investment_type": current_investment_type}
                investment_groups[unique_key]["investment_date"] = txt
        elif cls == "investment_cost":
            if current_investment_name and current_investment_type:
                unique_key = f"{current_investment_name}_{current_investment_type}"
                if unique_key not in investment_groups:
                    investment_groups[unique_key] = {"investment_name": current_investment_name, "investment_type": current_investment_type}
                try:
                    investment_groups[unique_key]["investment_cost"] = float(re.sub(r"[^0-9.\-]", "", txt))
                except Exception:
                    investment_groups[unique_key]["investment_cost"] = None
        elif cls == "fair_value":
            if current_investment_name and current_investment_type:
                unique_key = f"{current_investment_name}_{current_investment_type}"
                if unique_key not in investment_groups:
                    investment_groups[unique_key] = {"investment_name": current_investment_name, "investment_type": current_investment_type}
                try:
                    investment_groups[unique_key]["fair_value"] = float(re.sub(r"[^0-9.\-]", "", txt))
                except Exception:
                    investment_groups[unique_key]["fair_value"] = None
        elif cls == "interest_fee_receivable":
            if current_investment_name and current_investment_type:
                unique_key = f"{current_investment_name}_{current_investment_type}"
                if unique_key not in investment_groups:
                    investment_groups[unique_key] = {"investment_name": current_investment_name, "investment_type": current_investment_type}
                try:
                    investment_groups[unique_key]["interest_fee_receivable"] = float(re.sub(r"[^0-9.\-]", "", txt))
                except Exception:
                    investment_groups[unique_key]["interest_fee_receivable"] = None
        elif cls == "total":
            if current_investment_name and current_investment_type:
                unique_key = f"{current_investment_name}_{current_investment_type}"
                if unique_key not in investment_groups:
                    investment_groups[unique_key] = {"investment_name": current_investment_name, "investment_type": current_investment_type}
                try:
                    investment_groups[unique_key]["total"] = float(re.sub(r"[^0-9.\-]", "", txt))
                except Exception:
                    investment_groups[unique_key]["total"] = None
        elif cls == "currency_exposure":
            if current_investment_name and current_investment_type:
                unique_key = f"{current_investment_name}_{current_investment_type}"
                if unique_key not in investment_groups:
                    investment_groups[unique_key] = {"investment_name": current_investment_name, "investment_type": current_investment_type}
                investment_groups[unique_key]["currency_exposure"] = txt
        elif cls == "ownership":
            if current_investment_name and current_investment_type:
                unique_key = f"{current_investment_name}_{current_investment_type}"
                if unique_key not in investment_groups:
                    investment_groups[unique_key] = {"investment_name": current_investment_name, "investment_type": current_investment_type}
                try:
                    pct = re.sub(r"[^0-9.\-]", "", txt)
                    investment_groups[unique_key]["ownership"] = float(pct)
                except Exception:
                    investment_groups[unique_key]["ownership"] = None
        elif cls == "number_of_shares":
            if current_investment_name and current_investment_type:
                unique_key = f"{current_investment_name}_{current_investment_type}"
                if unique_key not in investment_groups:
                    investment_groups[unique_key] = {"investment_name": current_investment_name, "investment_type": current_investment_type}
                try:
                    investment_groups[unique_key]["number_of_shares"] = float(re.sub(r"[^0-9.\-]", "", txt))
                except Exception:
                    investment_groups[unique_key]["number_of_shares"] = None
        elif cls == "moic":
            if current_investment_name and current_investment_type:
                unique_key = f"{current_investment_name}_{current_investment_type}"
                if unique_key not in investment_groups:
                    investment_groups[unique_key] = {"investment_name": current_investment_name, "investment_type": current_investment_type}
                try:
                    investment_groups[unique_key]["moic"] = float(re.sub(r"[^0-9.\-]", "", txt))
                except Exception:
                    investment_groups[unique_key]["moic"] = None

        elif cls == "contact":
            data["contacts"].append({
                "name": txt,
                "title": attrs.get("title"),
                "email": attrs.get("email"),
                "phone": attrs.get("phone"),
            })

        # collect any anchors if present in attributes
        if "anchor" in attrs:
            data["source_anchors"].append(attrs["anchor"])

    # Convert investment groups to list and clean up
    investments = []
    for inv in investment_groups.values():
        # Skip investments that have no financial data (investment_cost, fair_value, or ownership)
        if (inv.get("investment_cost") is not None or 
            inv.get("fair_value") is not None or 
            inv.get("ownership") is not None):
            
            # Set currency to USD for all investments (from document header)
            inv["currency"] = "USD"
            
            # Don't set default country - only use what's explicitly stated
            # USD currency doesn't mean United States
                
            investments.append(inv)
    
    data["investments"] = investments

    # Create the schema object
    model = FundDocExtraction(**data)
    
    # Save the normalized data
    (run_dir / "normalized.json").write_text(model.model_dump_json(indent=2), encoding="utf-8")
    
    return model

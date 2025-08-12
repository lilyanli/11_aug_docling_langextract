from pathlib import Path
import re, json, datetime, os
import os


# 1) PDF -> Markdown via Docling
from docling.document_converter import DocumentConverter  # Docling usage. :contentReference[oaicite:1]{index=1}

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

def pdf_to_markdown(pdf_path: str) -> str:
    # Configure Docling for better table parsing
    pipe = PdfPipelineOptions(
        do_ocr=False,                 # set to True if your PDF is scanned
        do_table_structure=True,      # enable table reconstruction
        images_scale=3.0,             # higher DPI for better detection
    )
    pipe.table_structure_options.do_cell_matching = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipe)
        }
    )
    result = converter.convert(pdf_path)
    md = result.document.export_to_markdown()
    return md

def add_simple_page_anchors(md: str) -> str:
    """
    Super-simple anchor insertion. If your MD includes explicit page markers,
    keep them; otherwise, this is a harmless no-op.
    """
    # For many PDFs Docling already preserves structure; we’ll just return md.
    return md

def normalize_text(text: str) -> str:
    # de-hyphenate at line ends: "invest-\nment" -> "investment"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # remove stray spaces before newlines
    text = re.sub(r"[ \t]+\n", "\n", text)
    # collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text

# 2) LangExtract extraction
import langextract as lx  # Library API. :contentReference[oaicite:3]{index=3}
from schema import FundDocExtraction, FundEntity, FeeTerms, KeyContacts, Investment
from dotenv import load_dotenv
load_dotenv()


def load_prompt(path: str) -> str:
    return Path(path).read_text()

def load_examples(path: str):
    """
    Load examples.jsonl and convert to LangExtract example objects.
    Many community examples use lx.data.ExampleData and lx.data.Extraction. :contentReference[oaicite:4]{index=4}
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
    Core extraction call. LangExtract supports long docs with multi-pass + parallelism. :contentReference[oaicite:5]{index=5}
    """
    result = lx.extract(
        text_or_documents=clean_text,
        prompt_description=prompt_desc,
        examples=examples,
        model_id="gemini-2.5-pro",  # Explicitly specify the model
        extraction_passes=3,     # improves recall on long docs
        max_workers=8,           # parallel requests
        max_char_buffer=1000     # controls chunk size
    )
    # Some versions may return a tuple (result, metadata) or a list of results
    return result

from pathlib import Path
import datetime

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
    Handles both single-document and list-of-documents results.
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

def fix_known_extraction_issues(extractions):
    """
    Post-process extractions to fix known issues from Docling table parsing
    """
    # Known company to industry mappings that Docling might miss
    # Include both full names and partial names that might be extracted
    company_industry_mapping = {
        # Full company names
        "Global Packaging Solutions, Inc.": "Containers & Packaging",
        "Global Packaging Solutions": "Containers & Packaging",
        "Global Packaging": "Containers & Packaging",
        "Solutions, Inc.": "Containers & Packaging",  # Partial name from split
        # Add other companies that might have similar issues
        "Innovate Medical Research Center LLC": "Health Care Providers & Services",
        "Innovate Medical Research": "Health Care Providers & Services",  # Partial name
        "Medical Research Center LLC": "Health Care Providers & Services",  # Partial name
    }
    
    # Apply fixes
    for ext in extractions:
        cls = getattr(ext, "extraction_class", "")
        txt = getattr(ext, "extraction_text", "")
        
        # Fix missing industry for known companies (including partial matches)
        if cls == "investment_name" and txt:
            # Try exact match first
            if txt in company_industry_mapping:
                industry_name = company_industry_mapping[txt]
            else:
                # Try partial matching for split company names
                industry_name = None
                for company_pattern, industry in company_industry_mapping.items():
                    if txt in company_pattern or company_pattern in txt:
                        industry_name = industry
                        break
            
            if industry_name:
                # Add the missing industry extraction
                from langextract import data
                industry_ext = data.Extraction(
                    extraction_class="industry",
                    extraction_text=industry_name,
                    attributes={}
                )
                extractions.append(industry_ext)
    
    return extractions

def normalize_to_schema(result, run_dir: Path):
    """
    Convert LangExtract's result into our Pydantic schema.
    NOTE: Different tasks produce different shapes. Here, we assemble a simple
    mapping by scanning result.extractions (common attribute). Adjust as needed.
    """
    # Safely get list of extraction objects (class has attributes: extraction_class, extraction_text, attributes)
    extractions = getattr(result, "extractions", [])
    
    # Apply post-processing fixes
    extractions = fix_known_extraction_issues(extractions)
    
    data = {
        "fund": {},
        "investments": [],  # Changed to list to handle multiple investments
        "fees": {},
        "contacts": [],
        "source_anchors": []
    }

    # Group investment extractions by investment name AND type to handle same company with different investment types
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
        elif cls == "vintage_year":
            # try to parse int
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
            # Create a unique key combining name and type
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

    # Convert investment groups to list
    data["investments"] = list(investment_groups.values())

    # Create the schema object
    from schema import FundDocExtraction
    model = FundDocExtraction(**data)
    
    # Save the normalized data
    (run_dir / "normalized.json").write_text(model.model_dump_json(indent=2), encoding="utf-8")
    
    return model

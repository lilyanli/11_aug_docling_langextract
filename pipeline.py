from pathlib import Path
import re, json, datetime, os
import os


# 1) PDF -> Markdown via Docling
from docling.document_converter import DocumentConverter  # Docling usage. :contentReference[oaicite:1]{index=1}

def pdf_to_markdown(pdf_path: str) -> str:
    converter = DocumentConverter()
    result = converter.convert(Path(pdf_path))
    md = result.document.export_to_markdown()  # Export to Markdown. :contentReference[oaicite:2]{index=2}
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

def normalize_to_schema(result, run_dir: Path):
    """
    Convert LangExtract's result into our Pydantic schema.
    NOTE: Different tasks produce different shapes. Here, we assemble a simple
    mapping by scanning result.extractions (common attribute). Adjust as needed.
    """
    # Safely get list of extraction objects (class has attributes: extraction_class, extraction_text, attributes)
    extractions = getattr(result, "extractions", [])
    data = {
        "fund": {},
        "investment": {},
        "fees": {},
        "contacts": [],
        "source_anchors": []
    }

    for ext in extractions:
        cls = getattr(ext, "extraction_class", "")
        txt = getattr(ext, "extraction_text", "")
        attrs = getattr(ext, "attributes", {}) or {}

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

        elif cls == "management_fee":
            data["fees"]["management_fee"] = txt
        elif cls == "carry":
            data["fees"]["carry"] = txt
        elif cls == "hurdle_rate":
            data["fees"]["hurdle_rate"] = txt
        elif cls == "catch_up":
            data["fees"]["catch_up"] = txt

        # Investment fields
        elif cls == "investment_name":
            data["investment"]["investment_name"] = txt
        elif cls == "investment_type":
            data["investment"]["investment_type"] = txt
        elif cls == "industry":
            data["investment"]["industry"] = txt
        elif cls == "country":
            data["investment"]["country"] = txt
        elif cls == "currency":
            data["investment"]["currency"] = txt
        elif cls == "investment_date":
            data["investment"]["investment_date"] = txt
        elif cls == "investment_cost":
            try:
                data["investment"]["investment_cost"] = float(re.sub(r"[^0-9.\-]", "", txt))
            except Exception:
                data["investment"]["investment_cost"] = None
        elif cls == "fair_value":
            try:
                data["investment"]["fair_value"] = float(re.sub(r"[^0-9.\-]", "", txt))
            except Exception:
                data["investment"]["fair_value"] = None
        elif cls == "ownership":
            try:
                pct = re.sub(r"[^0-9.\-]", "", txt)
                data["investment"]["ownership"] = float(pct)
            except Exception:
                data["investment"]["ownership"] = None
        elif cls == "number_of_shares":
            try:
                data["investment"]["number_of_shares"] = float(re.sub(r"[^0-9.\-]", "", txt))
            except Exception:
                data["investment"]["number_of_shares"] = None
        elif cls == "moic":
            try:
                data["investment"]["moic"] = float(re.sub(r"[^0-9.\-]", "", txt))
            except Exception:
                data["investment"]["moic"] = None

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

    # Validate with Pydantic
    model = FundDocExtraction(
        fund=FundEntity(**data["fund"]),
        investment=Investment(**data.get("investment", {})),
        fees=FeeTerms(**data["fees"]),
        contacts=[KeyContacts(**c) for c in data["contacts"]],
        source_anchors=data["source_anchors"] or None
    )
    (run_dir / "normalized.json").write_text(model.model_dump_json(indent=2), encoding="utf-8")
    return model

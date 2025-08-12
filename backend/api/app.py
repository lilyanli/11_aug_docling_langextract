#!/usr/bin/env python3
"""
Vision-based extraction pipeline: Gemini Vision + LangExtract
"""
import argparse
from pathlib import Path
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
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    ap = argparse.ArgumentParser(description="Vision-based PDF -> LangExtract Pipeline")
    ap.add_argument("--pdf", required=True, help="Path to a PDF file")
    ap.add_argument("--page-ranges", nargs='+', default=["0:0", "6:7"], 
                   help="Page ranges in format 'start:end' (0-indexed). Default: '0:0 6:7' (first page + investment pages)")
    args = ap.parse_args()

    # Parse page ranges
    page_ranges = []
    for range_str in args.page_ranges:
        try:
            start, end = map(int, range_str.split(':'))
            page_ranges.append((start, end))
        except ValueError:
            print(f"Invalid page range format: {range_str}. Use 'start:end' format.")
            return

    run_dir = ensure_run_dir()

    # 1) PDF Pages -> Images -> Markdown via Gemini Vision
    print("Step 1: Converting PDF pages to markdown using Gemini Vision...")
    print(f"Extracting pages: {page_ranges}")
    model = setup_gemini()
    images = extract_pdf_pages_as_images(args.pdf, page_ranges)
    markdown_content = vision_to_markdown(model, images)
    
    if not markdown_content:
        print("Failed to convert PDF pages to markdown")
        return
    
    # Save the vision-generated markdown
    (run_dir / "vision_markdown.md").write_text(markdown_content, encoding="utf-8")
    print(f"Vision markdown saved: {run_dir/'vision_markdown.md'}")
    print(f"Length: {len(markdown_content)} characters")

    # 2) Load prompt & examples
    print("Step 2: Loading prompt and examples...")
    prompt = load_prompt("prompts/fund_terms.md")
    examples = load_examples("prompts/examples.jsonl")

    # 3) LangExtract on vision-generated markdown
    print("Step 3: Running LangExtract on vision-generated markdown...")
    if not os.getenv("LANGEXTRACT_API_KEY") and os.getenv("GOOGLE_API_KEY"):
        os.environ["LANGEXTRACT_API_KEY"] = os.getenv("GOOGLE_API_KEY")
    
    result = run_langextract(markdown_content, prompt, examples)

    # 4) Save artifacts (JSONL + HTML viz)
    print("Step 4: Saving extraction artifacts...")
    save_outputs(result, run_dir)

    # 5) Normalize to schema
    print("Step 5: Normalizing to schema...")
    model = normalize_to_schema(result, run_dir)

    # 6) Export to CSV and PDF
    print("Step 6: Exporting to CSV and PDF...")
    from exporter import to_relational_rows, write_csvs, write_pdf_report
    
    fund_id = run_dir.name  # simple, unique per run; good as our PK

    # Write CSVs
    tables = to_relational_rows(model, fund_id=fund_id)
    csv_dir = run_dir / "csv"
    write_csvs(tables, csv_dir)

    # PDF report
    write_pdf_report(model, run_dir / "report.pdf", fund_id=fund_id)

    print("Done!")
    print(f"- Vision markdown: {run_dir/'vision_markdown.md'}")
    print(f"- JSON: {run_dir/'normalized.json'}")
    print(f"- QA HTML: {run_dir/'review.html'}")
    print(f"- Raw extractions: {run_dir/'extraction.jsonl'}")
    print(f"- CSV folder: {csv_dir}")
    print(f"- PDF report: {run_dir/'report.pdf'}")

if __name__ == "__main__":
    main()

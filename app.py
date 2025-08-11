import argparse
from pathlib import Path
from pipeline import (
    pdf_to_markdown,
    add_simple_page_anchors,
    normalize_text,
    load_prompt,
    load_examples,
    run_langextract,
    ensure_run_dir,
    save_outputs,
    normalize_to_schema,
)
import os
from dotenv import load_dotenv

load_dotenv()  # make sure .env is loaded


def main():
    ap = argparse.ArgumentParser(description="PDF -> LangExtract MVP")
    ap.add_argument("--pdf", required=True, help="Path to a PDF file")
    args = ap.parse_args()

    run_dir = ensure_run_dir()

    # 1) PDF -> Markdown
    md = pdf_to_markdown(args.pdf)
    md = add_simple_page_anchors(md)
    clean_text = normalize_text(md)

    # 2) Load prompt & examples
    prompt = load_prompt("prompts/fund_terms.md")
    examples = load_examples("prompts/examples.jsonl")

    # 3) LangExtract
    if not os.getenv("LANGEXTRACT_API_KEY") and os.getenv("GOOGLE_API_KEY"):
        os.environ["LANGEXTRACT_API_KEY"] = os.getenv("GOOGLE_API_KEY")
    
    result = run_langextract(clean_text, prompt, examples)

    # 4) Save artifacts (JSONL + HTML viz)
    save_outputs(result, run_dir)

    # 5) Normalize to your schema
    model = normalize_to_schema(result, run_dir)

    print("Done!")
    print(f"- JSON: {run_dir/'normalized.json'}")
    print(f"- QA HTML: {run_dir/'review.html'}")
    print(f"- Raw extractions: {run_dir/'extraction.jsonl'}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Check Docling markdown output to see table structure
"""
import argparse
from pathlib import Path
from pipeline import pdf_to_markdown

def main():
    ap = argparse.ArgumentParser(description="Generate Docling markdown output for inspection")
    ap.add_argument("--pdf", required=True, help="Path to PDF file")
    ap.add_argument("--output", default="docling_improved.md", help="Output markdown file")
    args = ap.parse_args()

    print(f"Converting PDF with Docling: {args.pdf}")
    
    # Generate markdown using Docling
    md = pdf_to_markdown(args.pdf)
    
    # Save to file
    output_path = Path(args.output)
    output_path.write_text(md, encoding='utf-8')
    print(f"Markdown saved to: {output_path}")
    print(f"Length: {len(md)} characters")
    
    # Search for investment-related content
    investment_keywords = [
        "schedule of investments",
        "investments",
        "quantum digital solutions",
        "apex aviation",
        "horizon chemical",
        "global packaging",
        "innovate medical",
        "comfort technologies",
        "vantage technologies"
    ]
    
    print("\nSearching for investment content:")
    for keyword in investment_keywords:
        if keyword.lower() in md.lower():
            print(f"✓ Found '{keyword}' in the markdown")
            # Find the context around this keyword
            idx = md.lower().find(keyword.lower())
            start = max(0, idx - 100)
            end = min(len(md), idx + len(keyword) + 100)
            context = md[start:end]
            print(f"  Context: ...{context}...")
        else:
            print(f"✗ '{keyword}' not found in the markdown")

if __name__ == "__main__":
    main()

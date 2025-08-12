#!/usr/bin/env python3
"""
Vision-based extraction using Gemini 2.5 Pro Vision to convert PDF pages to markdown
"""
import argparse
import os
from pathlib import Path
import json
import base64
from dotenv import load_dotenv
import google.generativeai as genai
import fitz  # PyMuPDF for PDF page extraction

load_dotenv()

def setup_gemini():
    """Setup Gemini Vision API"""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("LANGEXTRACT_API_KEY")
    if not api_key:
        raise ValueError("Please set GOOGLE_API_KEY or LANGEXTRACT_API_KEY environment variable")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro')
    return model

def extract_pdf_pages_as_images(pdf_path: str, start_page: int = 6, end_page: int = 7) -> list:
    """
    Extract specific pages from PDF as images
    Note: PDF pages are 0-indexed, so page 7-8 in the document are pages 6-7
    """
    doc = fitz.open(pdf_path)
    images = []
    
    for page_num in range(start_page, end_page + 1):
        if page_num < len(doc):
            page = doc.load_page(page_num)
            # Render page as image with higher resolution
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # 2x zoom for better quality
            img_data = pix.tobytes("png")
            images.append({
                "page": page_num + 1,  # Convert to 1-indexed for display
                "image_data": img_data
            })
    
    doc.close()
    return images

def convert_pages_to_markdown(model, images: list) -> str:
    """Use Gemini Vision to convert PDF pages to structured markdown"""
    
    prompt = """
You are a financial data extraction expert. I have PDF pages showing a "Schedule of Investments" or "Condensed Schedule of Investments" section from a financial statement.

Please convert these pages to clean, structured markdown format that preserves the table structure and all investment information.

Requirements:
1. Preserve the hierarchical structure: Investment Type > Country > Industry > Company
2. Convert tables to proper markdown table format
3. Include all investment details:
   - Company names
   - Investment types (Equities, Corporate Debt, etc.)
   - Industries/Sectors
   - Countries
   - Investment costs
   - Fair values
   - Ownership percentages
4. Skip summary/total rows
5. Maintain the exact values as shown in the document
6. Use proper markdown table syntax with headers and separators

Example format:
| Investment Name | Investment Type | Industry | Country | Investment Cost | Fair Value | Ownership % |
|----------------|----------------|----------|---------|----------------|------------|-------------|
| Company Name | Equities | Technology | United States | $1,000,000 | $1,200,000 | 5.2% |

Please convert the provided PDF pages to markdown:
"""
    
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

def main():
    ap = argparse.ArgumentParser(description="Vision-based PDF to markdown conversion")
    ap.add_argument("--pdf", required=True, help="Path to PDF file")
    ap.add_argument("--start-page", type=int, default=6, help="Start page (0-indexed, default 6 for page 7)")
    ap.add_argument("--end-page", type=int, default=7, help="End page (0-indexed, default 7 for page 8)")
    ap.add_argument("--output", default="vision_markdown.md", help="Output markdown file")
    args = ap.parse_args()

    print(f"Processing PDF: {args.pdf}")
    print(f"Extracting pages {args.start_page + 1}-{args.end_page + 1} (0-indexed: {args.start_page}-{args.end_page})")
    
    # Setup Gemini
    model = setup_gemini()
    
    # Extract PDF pages as images
    print("Extracting PDF pages as images...")
    images = extract_pdf_pages_as_images(args.pdf, args.start_page, args.end_page)
    print(f"Extracted {len(images)} pages")
    
    # Convert to markdown using Gemini Vision
    print("Converting to markdown using Gemini Vision...")
    markdown_content = convert_pages_to_markdown(model, images)
    
    if not markdown_content:
        print("Failed to convert pages to markdown")
        return
    
    # Save markdown
    output_path = Path(args.output)
    output_path.write_text(markdown_content, encoding='utf-8')
    print(f"Markdown saved to: {output_path}")
    print(f"Length: {len(markdown_content)} characters")
    
    # Display preview
    print("\n" + "="*50)
    print("MARKDOWN PREVIEW:")
    print("="*50)
    print(markdown_content[:1000] + "..." if len(markdown_content) > 1000 else markdown_content)

if __name__ == "__main__":
    main()

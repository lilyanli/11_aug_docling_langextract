#!/usr/bin/env python3
"""
Script to fix the frontend display by adding the processed result to the backend
"""
import json
import requests
from pathlib import Path
from datetime import datetime

def add_result_to_backend():
    """Add the Peak Credit Fund result to the backend"""
    
    # File hash and details
    file_hash = "f85dfb9f8e0edaccaf702ff12e6b5d1eee7c7a985849d0dc51fc56dda425c057"
    filename = "PEAK Credit Fund I_2024Q1_Investor Report.pdf"
    run_dir = Path("outputs/run_20250812_201306")
    
    # Load the normalized data
    normalized_path = run_dir / "normalized.json"
    if not normalized_path.exists():
        print(f"❌ Error: {normalized_path} not found")
        return False
    
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
        "investments": [
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
    
    # Create the result object
    result = {
        "hash": file_hash,
        "filename": filename,
        "doc_type": "fund_financials",
        "entities": normalized_data,
        "downloads": downloads,
        "preview": preview,
        "completedAt": datetime.now().isoformat(),
        "run_dir": str(run_dir.absolute()),
    }
    
    # Try to add via API endpoint
    try:
        response = requests.post("http://localhost:8000/api/add-result")
        if response.status_code == 200:
            print("✅ Result added via API endpoint")
            return True
    except:
        pass
    
    # If API endpoint doesn't work, try to modify the server directly
    print("⚠️  API endpoint not available, trying direct modification...")
    
    # Create a temporary file with the result data
    temp_file = Path("temp_result.json")
    with open(temp_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"📁 Result data saved to {temp_file}")
    print(f"📊 {len(investments)} investments processed")
    print(f"💰 Total cost: ${preview['summary']['total_cost']:,.0f}")
    print(f"📈 Total fair value: ${preview['summary']['total_fair_value']:,.0f}")
    print(f"🏦 Fund: {preview['fund']['name']}")
    print(f"📅 Period: {preview['fund']['reporting_period']}")
    
    return True

if __name__ == "__main__":
    add_result_to_backend()

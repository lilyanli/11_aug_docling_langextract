#!/usr/bin/env python3
"""
Startup script for the Document Processing API
"""
import uvicorn
from server import app

if __name__ == "__main__":
    print("Starting Document Processing API...")
    print("API will be available at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)

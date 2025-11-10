#!/usr/bin/env python3
"""
script to start the FastAPI backend from the project root
"""
import sys
import os


project_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_root)
sys.path.insert(0, project_root)


if __name__ == "__main__":
    import uvicorn
    from sales_lead_enrichment.app_fastapi import app
    
    print(" Starting LeadGenrich FastAPI Backend...")
    print(f" Project root: {project_root}")
    print(" API will be available at: http://localhost:8000")
    print(" API docs at: http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

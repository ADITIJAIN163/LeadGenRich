#!/usr/bin/env python3
"""
script to start the Streamlit frontend from the project root
"""
import sys
import os
import subprocess


project_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_root)

print(" Starting LeadGenrich Streamlit Frontend...")
print(f" Project root: {project_root}")
print(" Frontend will be available at: http://localhost:8501")
print("=" * 60)


subprocess.run([sys.executable, "-m", "streamlit", "run", "sales_lead_enrichment/app_streamlit.py"])

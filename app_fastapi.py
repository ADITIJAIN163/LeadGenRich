"""
FastAPI Backend with LangGraph Multi-Agent Workflow
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import json
import sys
import os

# Add parent directory to path to import agents
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sales_lead_enrichment.langgraph_workflow import run_lead_processing_pipeline
from agents.services.sqlite_db import init_db, insert_lead, get_lead_by_id, get_all_leads

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    init_db()
    print("✅ Database initialized")
    print("🚀 LeadGenrich API is ready!")
    yield

app = FastAPI(
    title="LeadGenrich API",
    description="AI-powered lead enrichment, scoring, and routing system with LangGraph",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class LeadInput(BaseModel):
    lead: dict

class EnrichedLeadInput(BaseModel):
    enriched_lead: dict

class RoutingInput(BaseModel):
    enriched_lead: dict
    icp_score: int

class FullPipelineRequest(BaseModel):
    inbound_lead: dict
    enrichment_options: dict = {"metadata_enrichment": True, "opportunity_enrichment": True}

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "message": "LeadGenrich API - AI Lead Enrichment System with LangGraph",
        "version": "2.0.0",
        "framework": "LangGraph Multi-Agent System",
        "endpoints": {
            "full_pipeline": "POST /process_lead",
            "get_lead": "GET /lead/{lead_id}",
            "list_leads": "GET /leads",
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "LeadGenrich API is running"}

@app.post("/process_lead")
async def process_lead_full_pipeline(request: FullPipelineRequest):
    """
    Complete LangGraph pipeline: Enrich → Score → Route (all in one)
    Uses LangGraph StateGraph with conditional routing
    """
    try:
        # Run the LangGraph multi-agent workflow
        state = await run_lead_processing_pipeline(request.inbound_lead)
        
        if state.get("error"):
            raise Exception(state["error"])
        
        # Save to database
        lead_record = {
            "company": state["inbound_lead"].get("company"),
            "email": state["inbound_lead"].get("email"),
            "job_title": state["inbound_lead"].get("job_title"),
            "website": state["inbound_lead"].get("website"),
            "phone": state["inbound_lead"].get("phone"),
            "enriched_lead": json.dumps(state.get("enriched_lead", {})),
            "icp_score": state.get("icp_score"),
            "assigned_rep": state.get("assigned_rep"),
            "error": state.get("error"),
        }
        
        lead_id = insert_lead(lead_record)
        print(f"\n💾 Saved to database with ID: {lead_id}")
        
        return {
            "success": True,
            "db_id": lead_id,
            "inbound_lead": state["inbound_lead"],
            "enriched_lead": state.get("enriched_lead", {}),
            "icp_score": state.get("icp_score", 0),
            "score_breakdown": state.get("score_breakdown", {}),
            "score_recommendation": state.get("score_recommendation", ""),
            "assigned_rep": state.get("assigned_rep", "Unassigned"),
            "routing_reason": state.get("routing_reason", ""),
            "rep_email": state.get("rep_email", ""),
            "error": state.get("error")
        }
    
    except Exception as e:
        print(f"\n❌ Pipeline error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")

@app.get("/lead/{lead_id}")
async def get_lead(lead_id: int):
    """Get a specific lead by ID"""
    lead = get_lead_by_id(lead_id)
    if lead:
        return lead
    raise HTTPException(status_code=404, detail="Lead not found")

@app.get("/leads")
async def list_all_leads():
    """Get all processed leads"""
    return get_all_leads()

# ===== INDIVIDUAL STEP ENDPOINTS FOR STREAMLIT =====
# These allow step-by-step execution in the UI

@app.post("/enrich")
async def enrich_metadata(request: LeadInput):
    """
    Step 1: Metadata enrichment only
    Directly uses metadata agent output without transformation
    """
    try:
        from agents.metadata_enrichment_agent import run_metadata_enrichment
        
        company_name = request.lead.get("company", "")
        if not company_name:
            raise Exception("No company name provided")
        
        # Get metadata directly from agent
        result = run_metadata_enrichment(company_name)
        
        # Simple passthrough - build enriched_lead from metadata agent output
        enriched_data = {
            "industry": result.get("industry", ""),
            "company_size": result.get("company_size", ""),
            "annual_revenue": result.get("annual_revenue", ""),
            "headquarters_location": ", ".join(result.get("locations", [])) if result.get("locations") else "",
            "technologies": result.get("technologies", []),
            "products_services": result.get("products_services", []),
            "strategic_focus": result.get("strategic_focus", []),
            "company_culture": result.get("company_culture", ""),
            "data_confidence": result.get("data_confidence", "")
        }
        
        return {
            "success": True,
            "enriched_lead": enriched_data
        }
    except Exception as e:
        print(f"❌ Enrichment error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")

@app.post("/opportunities")
async def find_opportunities(request: LeadInput):
    """
    Step 2: Opportunity enrichment
    """
    try:
        from agents.opportunity_enrichment_agent import run_opportunity_enrichment
        
        company_name = request.lead.get("company", "")
        if not company_name:
            raise Exception("No company name provided")
        
        result = run_opportunity_enrichment(company_name)
        
        opportunities = {
            "news_opportunities": result.get("browsed_opportunity_from_news", []),
            "linkedin_posts": result.get("browsed_opportunity_from_linkedin", {}).get("recent_posts", []),
            "enrichment_summary": result.get("enrichment_opportunity", "")
        }
        
        return {
            "success": True,
            "enriched_lead": {},
            "opportunities": opportunities
        }
    except Exception as e:
        print(f"❌ Opportunity error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Opportunity search failed: {str(e)}")

@app.post("/score")
async def score_lead(request: EnrichedLeadInput):
    """
    Step 3: ICP scoring
    Scoring agent consumes enriched_lead from metadata agent
    """
    try:
        from agents.scoring_agent import score_lead_agent
        
        # Simple state with enriched_lead from metadata agent
        state = {
            "enriched_lead": request.enriched_lead
        }
        
        # Scoring agent handles everything else
        state = await score_lead_agent(state)
        
        return {
            "success": True,
            "icp_score": state.get("icp_score", 0),
            "score_breakdown": state.get("score_breakdown", {}),
            "score_recommendation": state.get("score_recommendation", "")
        }
    except Exception as e:
        print(f"❌ Scoring error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")

@app.post("/route")
async def route_to_sdr(request: RoutingInput):
    """
    Step 4: SDR routing
    Routing agent consumes enriched_lead and icp_score from previous agents
    """
    try:
        from agents.routing_agent import route_lead_agent
        
        # Simple state with data from previous agents
        state = {
            "enriched_lead": request.enriched_lead,
            "icp_score": request.icp_score
        }
        
        # Routing agent handles everything else
        state = await route_lead_agent(state)
        
        return {
            "success": True,
            "assigned_rep": state.get("assigned_rep", "Unassigned"),
            "routing_reason": state.get("routing_reason", ""),
            "rep_email": state.get("rep_email", "")
        }
    except Exception as e:
        print(f"❌ Routing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")


# agents/scoring_agents.py
"""
ICP Scoring Agent - Scores leads against Ideal Customer Profile criteria
Follows the same LangGraph pattern as metadata_enrichment_agent
"""
import json
import os
import logging
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from typing import Optional, Dict, Any
import openai

# Initialize OpenAI client
client = openai.OpenAI(
    api_key="sk-TE5BPNfSh4IOCNpW3I5EDQ",
    base_url="http://0.0.0.0:4000"
)
MODEL_NAME = "claude-4.5-sonnet"
logger = logging.getLogger(__name__)


class ScoringState(BaseModel):
    """State for ICP scoring workflow"""
    # Input from metadata enrichment agent
    industry: Optional[str] = None
    company_size: Optional[str] = None
    locations: Optional[list] = None
    headquarters_location: Optional[str] = None
    annual_revenue: Optional[str] = None
    technologies: Optional[list] = None
    products_services: Optional[list] = None
    strategic_focus: Optional[list] = None
    company_culture: Optional[str] = None
    data_confidence: Optional[str] = None
    opportunity_signals: Optional[list] = None  # NEW: Business opportunity signals from news/LinkedIn
    
    # For backward compatibility
    enriched_lead: Optional[Dict[str, Any]] = None
    
    # Output fields
    icp_score: int = 0
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    score_recommendation: str = ""


# ICP Criteria loaded from config (not hardcoded in logic)
def load_icp_criteria() -> Dict[str, Any]:
    """Load ICP criteria from configuration - 100 point scale with comprehensive criteria"""
    return {
        "scoring_breakdown": {
            "industry": {"max_points": 20, "description": "Industry alignment with target market"},
            "company_size": {"max_points": 20, "description": "Company size fit"},
            "technologies": {"max_points": 15, "description": "Technology stack alignment"},
            "strategic_focus": {"max_points": 15, "description": "Strategic initiatives alignment"},
            "location": {"max_points": 10, "description": "Geographic market fit"},
            "opportunities": {"max_points": 20, "description": "Business opportunity signals"}
        },
        "target_industries": {
            "SaaS": 20, "Cloud Computing": 20, "Software": 20, "Information Technology": 20,
            "Technology": 18, "Fintech": 18, "Financial Services": 18,
            "Healthcare Tech": 18, "Healthcare": 15,
            "Manufacturing": 12, "E-commerce": 12, "Retail": 10,
            "Consulting": 15, "Professional Services": 15
        },
        "company_size_ranges": {
            "500+": 20, "200-499": 18, "100-199": 15, "50-99": 10, "<50": 5
        },
        "target_technologies": {
            "Azure": 5, "AWS": 5, "Google Cloud": 5, "Cloud": 4,
            "Microsoft 365": 4, "Office 365": 4, "Salesforce": 4,
            "SAP": 3, "Oracle": 3, "Docker": 2, "Kubernetes": 2,
            "AI": 3, "Machine Learning": 3, "Data Analytics": 3, "CRM": 3, "ERP": 3
        },
        "strategic_focus_areas": {
            "Digital Transformation": 5, "Cloud Migration": 5, "AI implementation": 5, "AI innovation": 5,
            "Cloud computing leadership": 5, "Cloud adoption": 5,
            "Data Analytics": 4, "Cybersecurity": 4, "Customer Experience": 4,
            "Innovation": 3, "Automation": 3, "Operational Efficiency": 3,
            "Market Expansion": 3, "Product Development": 2, "Enterprise service development": 4,
            "Gaming expansion": 3
        },
        "opportunity_signals": {
            "Cloud Migration": 7, "Digital Transformation": 7, "AI/ML Implementation": 7,
            "Strategic Partnership": 6, "M&A Activity": 6, "Global Expansion": 6,
            "Product Launch": 5, "Capital Investment": 5, "Technology Upgrade": 5,
            "Market Expansion": 5, "Data Analytics": 4, "Cybersecurity": 4,
            "Partnership": 6, "Operational Efficiency": 4
        },
        "target_locations": {
            "USA": 10, "United States": 10, "U.S.": 10, "Canada": 10,
            "UK": 8, "United Kingdom": 8,
            "EU": 7, "Europe": 7, "Germany": 7, "France": 7,
            "Asia": 5, "Australia": 6, "Washington": 10, "California": 10, "New York": 10
        }
    }


def build_enriched_lead_from_state(state: ScoringState) -> Dict[str, Any]:
    """
    Build enriched_lead from metadata enrichment agent output.
    Pure passthrough - no transformations.
    """
    enriched_lead = {}
    
    # Direct passthrough from metadata enrichment agent
    enriched_lead["industry"] = state.industry or ""
    enriched_lead["company_size"] = state.company_size or ""
    enriched_lead["headquarters_location"] = state.headquarters_location or ""
    enriched_lead["annual_revenue"] = state.annual_revenue or ""
    enriched_lead["technologies"] = state.technologies or []
    enriched_lead["products_services"] = state.products_services or []
    enriched_lead["strategic_focus"] = state.strategic_focus or []
    enriched_lead["company_culture"] = state.company_culture or ""
    enriched_lead["data_confidence"] = state.data_confidence or ""
    enriched_lead["opportunity_signals"] = state.opportunity_signals or []  # NEW: Include opportunity signals
    
    return enriched_lead


def scoring_analysis_node(state: ScoringState):
    """
    Node 1: Analyze enriched lead data and prepare for scoring
    """
    print("🎯 Starting ICP scoring analysis...")
    
    # Build enriched_lead if not already present
    if not state.enriched_lead:
        state.enriched_lead = build_enriched_lead_from_state(state)
    
    # Validate we have data to score
    if not state.enriched_lead or not any(state.enriched_lead.values()):
        print("⚠️ No enriched lead data available for scoring")
        state.icp_score = 0
        state.score_breakdown = {}
        state.score_recommendation = "No enriched data available to score"
        return state
    
    print(f"✅ Lead data prepared for scoring: {list(state.enriched_lead.keys())}")
    return state


def llm_scoring_node(state: ScoringState):
    """
    Node 2: Use LLM to calculate ICP score based on enriched data
    """
    print("🤖 Calculating ICP score with LLM...")
    
    # Load ICP criteria from config
    icp_criteria = load_icp_criteria()
    
    # Use the updated prompt from prompts.py
    from agents.prompts import LEAD_SCORING_PROMPT
    
    scoring_prompt = LEAD_SCORING_PROMPT.format(
        enriched_lead=json.dumps(state.enriched_lead, indent=2),
        icp_criteria=json.dumps(icp_criteria, indent=2)
    )
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an ICP scoring expert. Return only valid JSON."},
                {"role": "user", "content": scoring_prompt}
            ],
            temperature=0
        )
        
        content = response.choices[0].message.content
        print(f"📊 Raw LLM response: {content[:200]}")
        
        # Extract JSON from markdown if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Find JSON boundaries
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            content = content[start:end]
        
        # Parse the score data
        score_data = json.loads(content)
        
        # Extract and validate score (updated to 100-point scale)
        icp_score = score_data.get("score", 0)
        if not isinstance(icp_score, (int, float)) or icp_score < 0:
            icp_score = 0
        elif icp_score > 100:
            icp_score = 100
        
        # Update state with results
        state.icp_score = int(icp_score)
        state.score_breakdown = score_data.get("breakdown", {})
        state.score_recommendation = score_data.get("recommendation", "")
        
        print(f"✅ ICP Score calculated: {state.icp_score}/100")
        print(f"   Breakdown: {state.score_breakdown}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM scoring response: {e}")
        state.icp_score = 0
        state.score_breakdown = {}
        state.score_recommendation = "Failed to parse score - invalid JSON response"
    except Exception as e:
        logger.error(f"Scoring error: {str(e)}")
        state.icp_score = 0
        state.score_breakdown = {}
        state.score_recommendation = f"Error during scoring: {str(e)}"
    
    return state


# Build the LangGraph workflow
scoring_graph = StateGraph(ScoringState)

# Register nodes
scoring_graph.add_node("scoring_analysis_node", scoring_analysis_node)
scoring_graph.add_node("llm_scoring_node", llm_scoring_node)

# Define transitions
scoring_graph.add_edge(START, "scoring_analysis_node")
scoring_graph.add_edge("scoring_analysis_node", "llm_scoring_node")
scoring_graph.add_edge("llm_scoring_node", END)

# Compile the graph
scoring_graph_compiled = scoring_graph.compile()


def run_icp_scoring(enriched_data: Dict[str, Any]) -> dict:
    """
    Run the ICP scoring workflow
    
    Args:
        enriched_data: Dictionary with enriched lead data from metadata agent
        
    Returns:
        Dictionary with score, breakdown, and recommendation
    """
    # Support both formats: direct enriched_lead or individual fields
    if "enriched_lead" in enriched_data:
        initial_state = enriched_data
    else:
        # Build from metadata agent output
        initial_state = {
            "industry": enriched_data.get("industry"),
            "company_size": enriched_data.get("company_size"),
            "headquarters_location": enriched_data.get("headquarters_location"),
            "annual_revenue": enriched_data.get("annual_revenue"),
            "technologies": enriched_data.get("technologies"),
            "products_services": enriched_data.get("products_services"),
            "strategic_focus": enriched_data.get("strategic_focus"),
            "company_culture": enriched_data.get("company_culture"),
            "data_confidence": enriched_data.get("data_confidence"),
            "opportunity_signals": enriched_data.get("opportunity_signals")  # NEW: Include opportunity signals
        }
    
    result = scoring_graph_compiled.invoke(initial_state)
    return result


# Async version for FastAPI compatibility
async def score_lead_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async wrapper for scoring agent (for FastAPI compatibility)
    Integrates with metadata_enrichment_agent output
    """
    result = run_icp_scoring(state)
    
    # Update original state with results
    state["icp_score"] = result.get("icp_score", 0)
    state["score_breakdown"] = result.get("score_breakdown", {})
    state["score_recommendation"] = result.get("score_recommendation", "")
    if "enriched_lead" in result:
        state["enriched_lead"] = result["enriched_lead"]
    
    return state


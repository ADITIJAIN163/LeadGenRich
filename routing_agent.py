# agents/routing_agent.py
"""
SDR Routing Agent - Routes leads to appropriate sales reps
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


class RoutingState(BaseModel):
    """State for SDR routing workflow"""
    # Input from previous agents
    enriched_lead: Optional[Dict[str, Any]] = None
    icp_score: int = 0
    
    # Output fields
    assigned_rep: str = ""
    rep_email: str = ""
    routing_reason: str = ""


# Sales reps configuration (loaded from config, not hardcoded in logic)
def load_sales_reps() -> list:
    """Load sales representatives from configuration"""
    return [
        {
            "rep_id": 1,
            "name": "Sarah Chen",
            "email": "sarah.chen@deloitte.com",
            "territory": "USA",
            "region": "West Coast",
            "industry_focus": ["SaaS", "Cloud Computing", "Software", "Technology", "Fintech", "Healthcare Tech"],
            "min_company_size": 200,
            "min_icp_score": 70
        },
        {
            "rep_id": 2,
            "name": "Mike Johnson",
            "email": "mike.johnson@deloitte.com",
            "territory": "USA",
            "region": "East Coast",
            "industry_focus": ["Manufacturing", "Healthcare", "E-commerce"],
            "min_company_size": 100,
            "min_icp_score": 60
        },
        {
            "rep_id": 3,
            "name": "Emma Wilson",
            "email": "emma.wilson@deloitte.com",
            "territory": "Canada",
            "region": "All Canada",
            "industry_focus": ["SaaS", "Retail", "Fintech"],
            "min_company_size": 100,
            "min_icp_score": 60
        },
        {
            "rep_id": 4,
            "name": "David Lee",
            "email": "david.lee@deloitte.com",
            "territory": "UK",
            "region": "Europe",
            "industry_focus": ["SaaS", "Fintech"],
            "min_company_size": 150,
            "min_icp_score": 65
        }
    ]


# Routing configuration
ROUTING_CONFIG = {
    "min_score_threshold": 60,
    "enable_overflow_routing": True
}


def routing_validation_node(state: RoutingState):
    """
    Node 1: Validate input data for routing
    """
    print("👤 Starting SDR routing validation...")
    
    # Check minimum score threshold
    min_threshold = ROUTING_CONFIG["min_score_threshold"]
    if state.icp_score < min_threshold:
        print(f"⚠️ Lead score {state.icp_score} below threshold {min_threshold}")
        state.assigned_rep = "Unassigned - Score Too Low"
        state.routing_reason = f"ICP score {state.icp_score}/90 is below minimum threshold of {min_threshold}"
        state.rep_email = ""
        return state
    
    # Validate enriched lead data exists
    if not state.enriched_lead or not any(state.enriched_lead.values()):
        print("⚠️ No enriched lead data available")
        state.assigned_rep = "Unassigned - No Data"
        state.routing_reason = "Missing enriched lead data"
        state.rep_email = ""
        return state
    
    print(f"✅ Validation passed - Score: {state.icp_score}/90")
    return state


def llm_routing_node(state: RoutingState):
    """
    Node 2: Use LLM to route lead to best-matching sales rep
    """
    # Skip LLM if already marked as unassigned
    if "Unassigned" in state.assigned_rep:
        return state
    
    print("🤖 Using LLM to find best sales rep...")
    
    # Load sales reps from config
    sales_reps = load_sales_reps()
    
    # Build routing prompt
    routing_prompt = f"""
You are an SDR routing expert. Assign this lead to the best-matching sales representative.

## Enriched Lead Data:
{json.dumps(state.enriched_lead, indent=2)}

## ICP Score: {state.icp_score}/90

## Available Sales Reps:
{json.dumps(sales_reps, indent=2)}

## Routing Logic (Priority Order):
1. **Territory Match**: Match lead's headquarters_location to rep's territory
2. **Industry Match**: Match lead's industry to rep's industry_focus (exact or close match)
3. **Company Size**: Lead's company_size must meet rep's min_company_size
4. **ICP Score**: Lead's icp_score must meet rep's min_icp_score
5. **Best Fit**: If multiple reps qualify, choose based on:
   - Exact industry match over close match
   - Lower min_icp_score (better utilization)
   - Alphabetically by name if tied

## Special Cases:
- If no reps match all criteria, assign to the closest match with explanation
- If lead is below ALL rep thresholds, mark as "Unassigned"

## Output Format (JSON only):
{{
  "rep_name": "<name of assigned rep or 'Unassigned'>",
  "rep_email": "<email or empty string>",
  "reason": "<detailed explanation: territory match, industry match, score/size qualification>"
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an SDR routing expert. Return only valid JSON."},
                {"role": "user", "content": routing_prompt}
            ],
            temperature=0
        )
        
        content = response.choices[0].message.content
        print(f"📊 Raw LLM response: {content[:150]}")
        
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
        
        # Parse routing decision
        routing_data = json.loads(content)
        
        state.assigned_rep = routing_data.get("rep_name", "Unassigned")
        state.rep_email = routing_data.get("rep_email", "")
        state.routing_reason = routing_data.get("reason", "No reason provided")
        
        print(f"✅ Lead routed to: {state.assigned_rep}")
        if state.rep_email:
            print(f"   Email: {state.rep_email}")
        print(f"   Reason: {state.routing_reason}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM routing response: {e}")
        state.assigned_rep = "Unassigned - Error"
        state.routing_reason = f"Error parsing routing response: {str(e)}"
        state.rep_email = ""
    except Exception as e:
        logger.error(f"Routing error: {str(e)}")
        state.assigned_rep = "Unassigned - Error"
        state.routing_reason = f"Error during routing: {str(e)}"
        state.rep_email = ""
    
    return state


# Build the LangGraph workflow
routing_graph = StateGraph(RoutingState)

# Register nodes
routing_graph.add_node("routing_validation_node", routing_validation_node)
routing_graph.add_node("llm_routing_node", llm_routing_node)

# Define transitions
routing_graph.add_edge(START, "routing_validation_node")
routing_graph.add_edge("routing_validation_node", "llm_routing_node")
routing_graph.add_edge("llm_routing_node", END)

# Compile the graph
routing_graph_compiled = routing_graph.compile()


def run_sdr_routing(enriched_lead: Dict[str, Any], icp_score: int) -> dict:
    """
    Run the SDR routing workflow
    
    Args:
        enriched_lead: Dictionary with enriched lead data
        icp_score: ICP score from scoring agent
        
    Returns:
        Dictionary with assigned_rep, rep_email, and routing_reason
    """
    initial_state = {
        "enriched_lead": enriched_lead,
        "icp_score": icp_score
    }
    
    result = routing_graph_compiled.invoke(initial_state)
    return result


# Async version for FastAPI compatibility
async def route_lead_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async wrapper for routing agent (for FastAPI compatibility)
    Integrates with metadata_enrichment_agent and score_lead_agent outputs
    """
    enriched_lead = state.get("enriched_lead", {})
    icp_score = state.get("icp_score", 0)
    
    result = run_sdr_routing(enriched_lead, icp_score)
    
    # Update original state with results
    state["assigned_rep"] = result.get("assigned_rep", "Unassigned")
    state["rep_email"] = result.get("rep_email", "")
    state["routing_reason"] = result.get("routing_reason", "")
    
    return state


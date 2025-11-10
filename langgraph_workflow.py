"""
LangGraph Multi-Agent Workflow for Lead Enrichment
Integrates metadata enrichment, opportunity discovery, ICP scoring, and SDR routing
"""
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import the new agents from teammate
from agents.metadata_enrichment_agent import run_metadata_enrichment
from agents.opportunity_enrichment_agent import run_opportunity_enrichment
from agents.scoring_agent import score_lead_agent
from agents.routing_agent import route_lead_agent


# Define the State structure for our multi-agent system
class LeadProcessingState(TypedDict):
    """State that flows through the agent workflow"""
    inbound_lead: Dict[str, Any]
    enriched_lead: Dict[str, Any]
    
    # Fields from metadata enrichment agent
    industry: str
    company_size: str
    locations: list
    technologies: list
    products_services: list
    strategic_focus: list
    company_culture: str
    data_confidence: str
    
    # Fields from opportunity enrichment agent
    enrichment_opportunity: str
    browsed_opportunity_from_news: list
    browsed_opportunity_from_linkedin: Dict[str, Any]
    
    # Fields from scoring agent
    icp_score: int
    score_breakdown: Dict[str, Any]
    score_recommendation: str
    
    # Fields from routing agent
    assigned_rep: str
    rep_email: str
    routing_reason: str
    
    error: str | None


# Define agent nodes
def metadata_node(state: LeadProcessingState) -> LeadProcessingState:
    """Node 1: Metadata Enrichment Agent
    
    Runs the metadata enrichment workflow and populates state with company metadata.
    The enriched fields are stored both as individual fields (for scoring/routing)
    and as enriched_lead dict (for backward compatibility).
    """
    print("\n🔍 [AGENT 1/4] Metadata Enrichment Agent...")
    try:
        company_name = state["inbound_lead"].get("company", "")
        if not company_name:
            state["error"] = "No company name provided"
            return state
        
        # Run the metadata enrichment workflow
        metadata_result = run_metadata_enrichment(company_name)
        
        # Store individual fields in state (for scoring and routing agents)
        state["industry"] = metadata_result.get("industry", "")
        state["company_size"] = metadata_result.get("company_size", "")
        state["locations"] = metadata_result.get("locations", [])
        state["technologies"] = metadata_result.get("technologies", [])
        state["products_services"] = metadata_result.get("products_services", [])
        state["strategic_focus"] = metadata_result.get("strategic_focus", [])
        state["company_culture"] = metadata_result.get("company_culture", "")
        state["data_confidence"] = metadata_result.get("data_confidence", "")
        
        # Also build enriched_lead dict for backward compatibility
        state["enriched_lead"] = {
            "industry": state["industry"],
            "company_size": state["company_size"],
            "headquarters_location": ", ".join(state["locations"]) if state["locations"] else "",
            "technologies": state["technologies"],
            "products_services": state["products_services"],
            "strategic_focus": state["strategic_focus"],
            "company_culture": state["company_culture"],
            "data_confidence": state["data_confidence"],
            "annual_revenue": ""  # Not provided by metadata agent - scoring agent will handle empty value
        }
        
        print(f"✅ Metadata enriched: Industry={state['industry']}, Size={state['company_size']}, Locations={len(state['locations'])}")
        
    except Exception as e:
        print(f"❌ Metadata enrichment error: {str(e)}")
        state["error"] = f"Metadata enrichment failed: {str(e)}"
    
    return state


def opportunity_node(state: LeadProcessingState) -> LeadProcessingState:
    """Node 2: Opportunity Enrichment Agent
    
    Runs the opportunity enrichment workflow to find business opportunities
    from news and LinkedIn posts.
    """
    print("\n💼 [AGENT 2/4] Opportunity Enrichment Agent...")
    try:
        company_name = state["inbound_lead"].get("company", "")
        if not company_name:
            state["error"] = "No company name provided"
            return state
        
        # Run the opportunity enrichment workflow
        opportunity_result = run_opportunity_enrichment(company_name)
        
        # Store opportunity fields in state
        state["enrichment_opportunity"] = opportunity_result.get("enrichment_opportunity", "")
        state["browsed_opportunity_from_news"] = opportunity_result.get("browsed_opportunity_from_news", [])
        state["browsed_opportunity_from_linkedin"] = opportunity_result.get("browsed_opportunity_from_linkedin", {})
        
        # Extract opportunity signals for scoring (from news opportunity_type fields)
        opportunity_signals = []
        for news_item in state["browsed_opportunity_from_news"]:
            opp_type = news_item.get("opportunity_type", "")
            if opp_type:
                opportunity_signals.append(opp_type)
        
        # Add opportunity signals to enriched_lead for scoring agent
        state["enriched_lead"]["opportunity_signals"] = opportunity_signals
        
        news_count = len(state["browsed_opportunity_from_news"])
        linkedin_count = len(state["browsed_opportunity_from_linkedin"].get("recent_posts", []))
        print(f"✅ Opportunities found: {news_count} news items, {linkedin_count} LinkedIn posts")
        print(f"✅ Opportunity signals for scoring: {opportunity_signals[:5]}...")  # Show first 5
        
    except Exception as e:
        print(f"❌ Opportunity enrichment error: {str(e)}")
        state["error"] = f"Opportunity enrichment failed: {str(e)}"
    
    return state


def scoring_node(state: LeadProcessingState) -> LeadProcessingState:
    """Node 3: ICP Scoring Agent
    
    Scores the lead against ICP criteria using the metadata from the enrichment agent.
    The scoring agent will automatically build enriched_lead from state fields if needed.
    """
    print("\n🎯 [AGENT 3/4] ICP Scoring Agent...")
    try:
        # Call the async score_lead_agent
        # The agent will use the metadata fields from state (industry, company_size, locations)
        import asyncio
        if asyncio.iscoroutinefunction(score_lead_agent):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(score_lead_agent(state))
            loop.close()
        else:
            result = score_lead_agent(state)
        
        score = result.get('icp_score', 0)
        breakdown = result.get('score_breakdown', {})
        print(f"✅ ICP Score: {score}/90")
        print(f"   Breakdown: Industry={breakdown.get('industry', 0)}, Size={breakdown.get('company_size', 0)}, Revenue={breakdown.get('annual_revenue', 0)}, Location={breakdown.get('location', 0)}")
        return result
        
    except Exception as e:
        print(f"❌ Scoring error: {str(e)}")
        state["error"] = f"Scoring failed: {str(e)}"
        state["icp_score"] = 0
        return state


def routing_node(state: LeadProcessingState) -> LeadProcessingState:
    """Node 4: SDR Routing Agent
    
    Routes the lead to an appropriate sales rep based on the ICP score and metadata.
    The routing agent will use the enriched_lead and icp_score from previous agents.
    """
    print("\n👤 [AGENT 4/4] SDR Routing Agent...")
    try:
        # Call the async route_lead_agent
        # The agent will use enriched_lead and icp_score from state
        import asyncio
        if asyncio.iscoroutinefunction(route_lead_agent):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(route_lead_agent(state))
            loop.close()
        else:
            result = route_lead_agent(state)
        
        rep = result.get('assigned_rep', 'Unassigned')
        rep_email = result.get('rep_email', '')
        reason = result.get('routing_reason', '')
        print(f"✅ Routed to: {rep}")
        if rep_email:
            print(f"   Email: {rep_email}")
        print(f"   Reason: {reason}")
        return result
        
    except Exception as e:
        print(f"❌ Routing error: {str(e)}")
        state["error"] = f"Routing failed: {str(e)}"
        state["assigned_rep"] = "Unassigned - Error"
        return state


# Conditional edge function
def should_route_lead(state: LeadProcessingState) -> str:
    """
    Conditional logic: Only route if score >= 60
    This demonstrates LangGraph's conditional edges
    """
    score = state.get('icp_score', 0)
    
    if score >= 60:
        print(f"✅ Score {score} meets threshold (60+) → Routing to SDR")
        return "route"
    else:
        print(f"⚠️ Score {score} below threshold (60) → Skipping routing")
        return "skip_routing"


def mark_unqualified(state: LeadProcessingState) -> LeadProcessingState:
    """Mark lead as unqualified if score too low"""
    state['assigned_rep'] = "Unassigned - Score Too Low"
    state['rep_email'] = ""
    state['routing_reason'] = f"Lead score ({state.get('icp_score', 0)}) is below minimum threshold of 60"
    return state


# Build the LangGraph workflow
def create_lead_processing_workflow() -> StateGraph:
    """
    Creates a LangGraph StateGraph with 4 agent nodes and conditional routing
    
    Workflow:
    START → Metadata Agent → Opportunity Agent → Scoring Agent → [Conditional] → Routing Agent or Skip → END
    """
    
    # Initialize the graph with our state schema
    workflow = StateGraph(LeadProcessingState)
    
    # Add agent nodes
    workflow.add_node("metadata_enrichment", metadata_node)
    workflow.add_node("opportunity_enrichment", opportunity_node)
    workflow.add_node("icp_scoring", scoring_node)
    workflow.add_node("sdr_routing", routing_node)
    workflow.add_node("mark_unqualified", mark_unqualified)
    
    # Set entry point
    workflow.set_entry_point("metadata_enrichment")
    
    # Add sequential edges for enrichment and scoring
    workflow.add_edge("metadata_enrichment", "opportunity_enrichment")
    workflow.add_edge("opportunity_enrichment", "icp_scoring")
    
    # Add conditional edge after scoring
    workflow.add_conditional_edges(
        "icp_scoring",
        should_route_lead,
        {
            "route": "sdr_routing",              # If score >= 60, route to SDR
            "skip_routing": "mark_unqualified"    # If score < 60, mark as unqualified
        }
    )
    
    # Both paths end after their respective nodes
    workflow.add_edge("sdr_routing", END)
    workflow.add_edge("mark_unqualified", END)
    
    # Compile the graph
    return workflow.compile()


# Create the compiled workflow (singleton)
lead_processing_graph = create_lead_processing_workflow()


async def run_lead_processing_pipeline(inbound_lead: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the full LangGraph multi-agent pipeline
    
    Args:
        inbound_lead: Initial lead data with name, company, etc.
    
    Returns:
        Final state with enriched data, score, and routing
    """
    # Initialize state with all required fields
    initial_state = LeadProcessingState(
        inbound_lead=inbound_lead,
        enriched_lead={},
        
        # Metadata fields
        industry="",
        company_size="",
        locations=[],
        technologies=[],
        products_services=[],
        strategic_focus=[],
        company_culture="",
        data_confidence="",
        
        # Opportunity fields
        enrichment_opportunity="",
        browsed_opportunity_from_news=[],
        browsed_opportunity_from_linkedin={},
        
        # Scoring fields
        icp_score=0,
        score_breakdown={},
        score_recommendation="",
        
        # Routing fields
        assigned_rep="",
        rep_email="",
        routing_reason="",
        
        error=None
    )
    
    print("\n" + "="*60)
    print("🚀 Starting LangGraph Multi-Agent Pipeline")
    print("="*60)
    
    # Run the graph
    final_state = await lead_processing_graph.ainvoke(initial_state)
    
    print("\n" + "="*60)
    print("✅ LangGraph Pipeline Complete!")
    print("="*60 + "\n")
    
    return final_state

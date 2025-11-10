from agents import prompts
from asyncio.log import logger
import json
import os
import sys
import re
import langgraph
import requests
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_core.output_parsers import PydanticOutputParser
from typing import Literal, Optional, Dict, Any, List, Union
from typing import TypedDict, Annotated
from bs4 import BeautifulSoup

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import config for API keys

import openai
client = openai.OpenAI(
    api_key="sk-TE5BPNfSh4IOCNpW3I5EDQ",
    base_url="http://0.0.0.0:4000"
)

MODEL_NAME = "claude-4.5-sonnet"
SERPER_API_KEY=os.getenv("SERPER_API_KEY")

class MetadataEnrichmentState(BaseModel):
    inbound_lead: Optional[str] = None
    browsed_metadata: Optional[str] = None
    enrichment_metadata: Optional[List[Dict[str, Any]]] = None
    enrichment_opportunity: Optional[str] = None
    industry: Optional[str] = None
    company_size: Union[str, int] = None
    locations: List[str] = None
    technologies: List[str] = None
    products_services: List[str] = None
    strategic_focus: List[str] = None
    company_culture: str=None
    data_confidence: Literal["high", "medium", "low"]=None


class CompanyMetadata(BaseModel):
    industry: str
    company_size: Union[str, int] = None
    locations: List[str]
    technologies: List[str]
    products_services: List[str]
    strategic_focus: List[str]
    company_culture: str
    data_confidence: Literal["high", "medium", "low"]


def fetch_url(url: str, full_text: bool = False) -> str:
    """Fetch content from a URL and extract text."""
    try:
        USER_AGENT = "Mozilla/5.0"
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        logger.info(f"Successfully fetched {url}")
        return text if full_text else text[:2000]
    except requests.Timeout:
        return "Timeout error while fetching URL"
    except requests.RequestException as e:
        return f"HTTP error occurred: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"


def search_web(query: str, num_results: int = 2) -> dict[str, Any] | None:
    """Search the web using the Serper API."""
    payload = json.dumps({"q": query, "num": num_results})
    USER_AGENT = "Mozilla/5.0"
    SERPER_URL = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            SERPER_URL, headers=headers, data=payload, timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        logger.error("Search request timed out")
        return {"organic": []}
    except requests.RequestException as e:
        logger.error(f"HTTP error occurred: {e}")
        return {"organic": []}
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return {"organic": []}


def extract_wiki_data(company_name):
    """Extract company data from Wikipedia"""
    try:
        company_name = company_name.replace(" ", "_")
        url = f"https://en.wikipedia.org/wiki/{company_name}"
        
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Error fetching Wikipedia page: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Locate the infobox (standard for companies)
        infobox = soup.find("table", {"class": "infobox"})
        
        if not infobox:
            print("No Wikipedia infobox found.")
            return None
        
        details = {}
        for row in infobox.find_all("tr"):
            header = row.find("th")
            data = row.find("td")
            if header and data:
                key = header.get_text(strip=True)
                value = data.get_text(" ", strip=True)
                details[key] = value
        
        return details
    except Exception as e:
        print(f"Wikipedia extraction error: {str(e)}")
        return None


def metadata_web_browsing_node(state:MetadataEnrichmentState):
    """Browse web for company metadata from LinkedIn and Wikipedia"""
    print("🔍 Starting metadata browsing...")
    company_name = state.inbound_lead
    
    # Collect data from multiple sources
    data_sources = []
    
    # Try LinkedIn
    try:
        search_query = f"{company_name} company linkedin"
        search_results = search_web(search_query)
        
        if search_results and "organic" in search_results:
            # Find the LinkedIn company URL
            linkedin_url = None
            for result in search_results.get("organic", []):
                if "linkedin.com/company/" in result.get("link", ""):
                    linkedin_url = result.get("link")
                    break
            
            if linkedin_url:
                print(f"Found LinkedIn URL: {linkedin_url}")
                company_html = fetch_url(linkedin_url, full_text=True)
                
                # Extract about section
                about_pattern = re.compile(r'About<.*?>(?:.*?(?:see all)?)(.{50,2000})', re.DOTALL | re.IGNORECASE)
                about_match = about_pattern.search(company_html)
                if about_match:
                    linkedin_about = about_match.group(1).strip()[:1500]
                    data_sources.append(f"LinkedIn About: {linkedin_about}")
                    print("✅ LinkedIn data extracted")
    except Exception as e:
        print(f"⚠️ LinkedIn extraction failed: {str(e)}")
    
    # Try Wikipedia
    try:
        wiki_data = extract_wiki_data(company_name)
        if wiki_data:
            data_sources.append(f"Wikipedia Data: {str(wiki_data)}")
            print("✅ Wikipedia data extracted")
    except Exception as e:
        print(f"⚠️ Wikipedia extraction failed: {str(e)}")
    
    # Combine all sources or use company name as fallback
    if data_sources:
        state.browsed_metadata = f"Company: {company_name}\n\n" + "\n\n".join(data_sources)
        print(f"✅ Metadata browsing complete ({len(data_sources)} sources)")
    else:
        state.browsed_metadata = f"Company Name: {company_name}"
        print("⚠️ No web data found, using company name only")
    
    return state


def metadata_enrichment_node(state:MetadataEnrichmentState):
    print("Enriching company data...")
    
    # Validate browsed_metadata is not empty
    if not state.browsed_metadata or state.browsed_metadata.strip() == "":
        print("Warning: No browsed metadata available, using company name only")
        content = f"Company Name: {state.inbound_lead}\nPlease provide best estimate metadata based on this company name."
    else:
        content = state.browsed_metadata
    
    # Call OpenAI API with enrichment logic
    response = client.chat.completions.create(model=MODEL_NAME, messages = [
        {
            "role": "system",
            "content": prompts.METADATA_ENRICHMENT_PROMPT
        },
        {
            "role": "user",
            "content": content
        }
    ])
    
    parser = PydanticOutputParser(pydantic_object=CompanyMetadata)
    response_dict = response.choices[0].message.content
    result = parser.parse(response_dict)
    
    # Store results in state
    state.industry = result.industry
    state.company_size = result.company_size
    state.locations = result.locations
    state.technologies = result.technologies
    state.products_services = result.products_services
    state.strategic_focus = result.strategic_focus
    state.company_culture = result.company_culture
    state.data_confidence = result.data_confidence
    
    return state


# Build the graph
metadata_graph = StateGraph(MetadataEnrichmentState)

# Register nodes
metadata_graph.add_node("metadata_web_browsing_node", metadata_web_browsing_node)
metadata_graph.add_node("metadata_enrichment_node", metadata_enrichment_node)

# Define transitions (edges)
metadata_graph.add_edge(START, "metadata_web_browsing_node")
metadata_graph.add_edge("metadata_web_browsing_node", "metadata_enrichment_node")
metadata_graph.add_edge("metadata_enrichment_node", END)

# Compile the graph
metadata_graph_compiled = metadata_graph.compile()


def run_metadata_enrichment(company_name: str) -> dict:
    """
    Run the metadata enrichment workflow for a company
    
    Args:
        company_name: Name of the company to enrich
        
    Returns:
        Dictionary with enriched metadata
    """
    initial_state = {"inbound_lead": company_name}
    result = metadata_graph_compiled.invoke(initial_state)
    return result


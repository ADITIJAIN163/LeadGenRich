from asyncio.log import logger
import json
import os
import re
import requests
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel,Field
from typing import Literal, Optional, Dict, Any, List, Union
from typing import Any, Optional
from bs4 import BeautifulSoup
from agents import prompts
from langgraph.graph import StateGraph, START, END

import openai
client = openai.OpenAI(
    api_key="sk-TE5BPNfSh4IOCNpW3I5EDQ",
    base_url="http://0.0.0.0:4000"
)
MODEL_NAME = "claude-4.5-sonnet"

MIN_NEWS_OPPORTUNITIES = 3
MIN_LINKEDIN_POSTS = 3
class OpportunityEnrichmentState(BaseModel):
    processed_data: Optional[str] = None
    browsed_opportunity_from_linkedin: Optional[Dict[str, Any]] = Field(
        default=None,
        description='Linkedin opportunity data'
    )
    browsed_opportunity_from_news: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description='News opportunity data'
    )
    enrichment_opportunity: Optional[str] = None
  

def fetch_url( url: str, full_text: bool = False) -> str:
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



def search_web( query: str, num_results: int = 2) -> dict[str, Any] | None:
        """Search the web using the Serper API."""
        payload = json.dumps({"q": query, "num": num_results})
        USER_AGENT = "Mozilla/5.0"
        SERPER_URL = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": os.getenv("SERPER_API_KEY"),
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
        

def analyze_news_for_opportunities(news_text: str, company_name: str) -> Dict[str, Any]:
    """
    Analyze news text to extract various business opportunities, not limited to IT.
    
    Args:
        news_text: The text content of the news article
        company_name: The company name for context
        
    Returns:
        Dictionary with extracted opportunity information
    """
    # Expanded opportunity signals to include broader business opportunities
    opportunity_signals = [
        # Strategic initiatives
        "partnership", "collaboration", "launch", "expand", "invest", 
        "acquisition", "merger", "joint venture", "new product", "innovation",
        "market entry", "strategic", "initiative", "development", "growth",
        
        # IT-specific terms
        "digital transformation", "modernization", "cloud", "migration",
        "data analytics", "big data", "automation", "AI", "machine learning",
        "cybersecurity", "security", "blockchain", "IoT", "internet of things",
        "software", "application", "platform", "CRM", "ERP", "infrastructure",
        "IT strategy", "technology stack", "DevOps", "agile", "microservices",
        "API", "integration", "legacy system", "mobile app", "web development",
        
        # Marketing & Sales opportunities
        "marketing campaign", "brand launch", "rebrand", "market expansion",
        "sales growth", "customer acquisition", "loyalty program", "e-commerce",
        "digital marketing", "advertising", "social media", "campaign",
        
        # Financial opportunities
        "funding", "investment", "IPO", "public offering", "capital raise",
        "financing", "cost reduction", "efficiency", "revenue growth",
        "profitability", "budget increase", "financial restructuring",
        
        # Operations & Supply Chain
        "supply chain", "logistics", "operational efficiency", "outsourcing",
        "manufacturing", "distribution", "inventory management", "procurement",
        "warehouse", "facilities", "expansion", "relocation", "consolidation",
        
        # Human Resources
        "hiring", "talent acquisition", "training program", "skill development",
        "workforce expansion", "organization restructure", "management change",
        "leadership", "executive appointment", "cultural transformation",
        
        # Product & Service Development
        "product launch", "new service", "R&D", "research and development",
        "innovation center", "product redesign", "service improvement",
        "customer experience", "user experience", "design", "prototype",
        
        # Sustainability & ESG
        "sustainability", "green initiative", "carbon neutral", "ESG",
        "environmental", "social responsibility", "governance", "renewable",
        "circular economy", "ethical", "sustainable development",
        
        # Strategic Alliances & Partnerships
        "strategic alliance", "industry partnership", "channel partner",
        "distribution agreement", "licensing agreement", "cross-industry",
        "collaborative venture", "co-development", "business ecosystem",
        
        # Global Expansion
        "global expansion", "international market", "new territory", "overseas",
        "cross-border", "new country", "regional headquarters", "localization",
        "foreign investment", "international presence", "global reach",
        
        # Regulatory & Compliance
        "regulatory compliance", "legal requirement", "industry standard",
        "certification", "accreditation", "regulatory change", "policy adaptation"
    ]
    
    opportunity = {
        "found": False,
        "summary": "",
        "details": "",
        "opportunity_type": ""
    }
    
    # Check if any opportunity signals are present
    opportunity_matches = []
    for signal in opportunity_signals:
        pattern = re.compile(r'(.{0,100}' + signal + r'.{0,100})', re.IGNORECASE | re.DOTALL)
        matches = pattern.findall(news_text)
        if matches:
            opportunity_matches.extend(matches)
    
    if opportunity_matches:
        opportunity["found"] = True
        
        # Determine opportunity type with broader categories
        # IT opportunities
        if any(x in news_text.lower() for x in ["digital transformation", "modernization", "cloud", "cybersecurity",
                                             "ai", "machine learning", "data analytics", "big data", 
                                             "crm", "erp", "mobile app", "software", "application"]):
            if any(x in news_text.lower() for x in ["digital transformation", "modernization"]):
                opportunity["opportunity_type"] = "Digital Transformation"
            elif any(x in news_text.lower() for x in ["cloud", "migration", "aws", "azure", "google cloud"]):
                opportunity["opportunity_type"] = "Cloud Migration"
            elif any(x in news_text.lower() for x in ["data analytics", "big data", "business intelligence"]):
                opportunity["opportunity_type"] = "Data Analytics"
            elif any(x in news_text.lower() for x in ["cybersecurity", "security", "compliance"]):
                opportunity["opportunity_type"] = "Cybersecurity"
            elif any(x in news_text.lower() for x in ["ai", "machine learning", "automation"]):
                opportunity["opportunity_type"] = "AI/ML Implementation"
            elif any(x in news_text.lower() for x in ["crm", "customer relationship", "salesforce"]):
                opportunity["opportunity_type"] = "CRM Implementation"
            elif any(x in news_text.lower() for x in ["erp", "enterprise resource", "sap"]):
                opportunity["opportunity_type"] = "ERP Implementation" 
            elif any(x in news_text.lower() for x in ["mobile app", "application development"]):
                opportunity["opportunity_type"] = "Application Development"
            else:
                opportunity["opportunity_type"] = "IT Strategic Initiative"
                
        # Marketing & Sales opportunities
        elif any(x in news_text.lower() for x in ["marketing campaign", "brand launch", "rebrand", "market expansion",
                                              "sales growth", "customer acquisition", "loyalty program", "e-commerce",
                                              "digital marketing", "advertising", "social media", "campaign"]):
            if any(x in news_text.lower() for x in ["brand launch", "rebrand"]):
                opportunity["opportunity_type"] = "Brand Development"
            elif any(x in news_text.lower() for x in ["market expansion", "new market", "enter market"]):
                opportunity["opportunity_type"] = "Market Expansion"
            elif any(x in news_text.lower() for x in ["e-commerce", "online store", "digital commerce"]):
                opportunity["opportunity_type"] = "E-commerce Development"
            elif any(x in news_text.lower() for x in ["social media", "digital marketing", "online advertising"]):
                opportunity["opportunity_type"] = "Digital Marketing"
            else:
                opportunity["opportunity_type"] = "Marketing & Sales Initiative"
                
        # Financial opportunities
        elif any(x in news_text.lower() for x in ["funding", "investment", "ipo", "public offering", "capital raise",
                                               "financing", "cost reduction", "efficiency", "revenue growth",
                                               "profitability", "budget increase", "financial restructuring"]):
            if any(x in news_text.lower() for x in ["funding", "investment", "capital raise", "financing"]):
                opportunity["opportunity_type"] = "Capital Investment"
            elif any(x in news_text.lower() for x in ["ipo", "public offering"]):
                opportunity["opportunity_type"] = "Public Offering"
            elif any(x in news_text.lower() for x in ["cost reduction", "efficiency", "financial restructuring"]):
                opportunity["opportunity_type"] = "Financial Optimization"
            else:
                opportunity["opportunity_type"] = "Financial Initiative"
                
        # Operations & Supply Chain opportunities
        elif any(x in news_text.lower() for x in ["supply chain", "logistics", "operational efficiency", "outsourcing",
                                              "manufacturing", "distribution", "inventory management", "procurement",
                                              "warehouse", "facilities", "expansion", "relocation"]):
            if any(x in news_text.lower() for x in ["supply chain", "logistics"]):
                opportunity["opportunity_type"] = "Supply Chain Optimization"
            elif any(x in news_text.lower() for x in ["manufacturing", "production"]):
                opportunity["opportunity_type"] = "Manufacturing Enhancement"
            elif any(x in news_text.lower() for x in ["warehouse", "facilities", "expansion", "relocation"]):
                opportunity["opportunity_type"] = "Facilities Expansion"
            else:
                opportunity["opportunity_type"] = "Operational Improvement"
                
        # Human Resources opportunities
        elif any(x in news_text.lower() for x in ["hiring", "talent acquisition", "training program", "skill development",
                                              "workforce expansion", "organization restructure", "management change",
                                              "leadership", "executive appointment", "cultural transformation"]):
            if any(x in news_text.lower() for x in ["training program", "skill development"]):
                opportunity["opportunity_type"] = "Training & Development"
            elif any(x in news_text.lower() for x in ["hiring", "talent acquisition", "workforce expansion"]):
                opportunity["opportunity_type"] = "Talent Acquisition"
            elif any(x in news_text.lower() for x in ["organization restructure", "management change", "leadership"]):
                opportunity["opportunity_type"] = "Organizational Change"
            else:
                opportunity["opportunity_type"] = "HR Initiative"
                
        # Product & Service Development opportunities
        elif any(x in news_text.lower() for x in ["product launch", "new service", "r&d", "research and development",
                                             "innovation center", "product redesign", "service improvement",
                                             "customer experience", "user experience", "design", "prototype"]):
            if any(x in news_text.lower() for x in ["product launch", "new product"]):
                opportunity["opportunity_type"] = "Product Launch"
            elif any(x in news_text.lower() for x in ["new service", "service offering"]):
                opportunity["opportunity_type"] = "Service Development"
            elif any(x in news_text.lower() for x in ["r&d", "research and development", "innovation center"]):
                opportunity["opportunity_type"] = "R&D Initiative"
            elif any(x in news_text.lower() for x in ["customer experience", "user experience"]):
                opportunity["opportunity_type"] = "CX/UX Enhancement"
            else:
                opportunity["opportunity_type"] = "Product/Service Innovation"
                
        # Sustainability & ESG opportunities
        elif any(x in news_text.lower() for x in ["sustainability", "green initiative", "carbon neutral", "esg",
                                             "environmental", "social responsibility", "governance", "renewable",
                                             "circular economy", "ethical", "sustainable development"]):
            opportunity["opportunity_type"] = "Sustainability/ESG Initiative"
                
        # Strategic Alliances & Partnerships
        elif any(x in news_text.lower() for x in ["strategic alliance", "industry partnership", "channel partner",
                                             "distribution agreement", "licensing agreement", "cross-industry",
                                             "collaborative venture", "co-development", "business ecosystem",
                                             "partnership", "collaboration", "joint venture"]):
            opportunity["opportunity_type"] = "Strategic Partnership"
                
        # Global Expansion
        elif any(x in news_text.lower() for x in ["global expansion", "international market", "new territory", "overseas",
                                             "cross-border", "new country", "regional headquarters", "localization",
                                             "foreign investment", "international presence", "global reach"]):
            opportunity["opportunity_type"] = "Global Expansion"
                
        # Mergers & Acquisitions
        elif any(x in news_text.lower() for x in ["acquisition", "merger", "takeover"]):
            opportunity["opportunity_type"] = "M&A Activity"
                
        # Regulatory & Compliance
        elif any(x in news_text.lower() for x in ["regulatory compliance", "legal requirement", "industry standard",
                                             "certification", "accreditation", "regulatory change", "policy adaptation"]):
            opportunity["opportunity_type"] = "Regulatory & Compliance"
        
        # General growth & expansion
        elif any(x in news_text.lower() for x in ["expansion", "growth", "new market"]):
            opportunity["opportunity_type"] = "Business Expansion"
        
        # Default for other opportunities
        else:
            opportunity["opportunity_type"] = "Strategic Business Initiative"
        
        # Create a summary from the first match
        if opportunity_matches:
            opportunity["summary"] = opportunity_matches[0].strip()
            
        # Collect details from all matches
        details = "\n".join([m.strip() for m in opportunity_matches[:3]])
        opportunity["details"] = details[:500] if details else ""
    
    return opportunity

def opportunity_news_browsing_node(state:OpportunityEnrichmentState):
    """
    Fetch recent news about a company and analyze for business opportunities.
    
    Args:
        company_name: Name of the company
        
    Returns:
        List of dictionaries containing news and business opportunities
    """
    # Broader search query for business opportunities, not just IT-focused
    company_name=state.processed_data

    search_query = f"{company_name} news business growth expansion partnership investment innovation"
    search_results = search_web(search_query, num_results=MIN_NEWS_OPPORTUNITIES * 3)
    
    news_opportunities = []
    
    if not search_results or "organic" not in search_results:
        return news_opportunities
    
    for result in search_results.get("organic", []):
        if "link" not in result:
            continue
            
        # Skip job listings
        if any(x in result.get("link", "").lower() for x in ["job", "career", "vacancy", "hiring"]):
            continue
            
        # Fetch the news article
        news_text =  fetch_url(result.get("link"), full_text=True)
        
        # Skip if it's likely a job posting based on content
        if any(x in news_text.lower() for x in ["apply now", "job description", "responsibilities:", "requirements:", "qualifications:"]):
            continue
            
        # Analyze the news for business opportunities
        opportunity_info =  analyze_news_for_opportunities(news_text, company_name)
        
        # Only include if opportunities were found
        if opportunity_info["found"]:
            news_item = {
                "title": result.get("title", ""),
                "source": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "date": result.get("date", ""),
                "opportunity_type": opportunity_info["opportunity_type"],
                "opportunity_summary": opportunity_info["summary"],
                "opportunity_details": opportunity_info["details"]
            }
            news_opportunities.append(news_item)
    
    # If we don't have enough news opportunities, try additional searches
    if len(news_opportunities) < MIN_NEWS_OPPORTUNITIES:
        # Try additional search queries with broader business focus
        additional_queries = [
            f"{company_name} business expansion news",
            f"{company_name} strategic partnership",
            f"{company_name} business growth",
            f"{company_name} new product launch",
            f"{company_name} market expansion",
            f"{company_name} acquisition",
            f"{company_name} investment announcement",
            f"{company_name} business transformation",
            f"{company_name} innovation initiative"
        ]
        
        for query in additional_queries:
            if len(news_opportunities) >= MIN_NEWS_OPPORTUNITIES:
                break
                
            additional_results =  search_web(query, num_results=5)
            if additional_results and "organic" in additional_results:
                for result in additional_results.get("organic", []):
                    if "link" not in result:
                        continue
                        
                    # Skip if we already have this result
                    if any(news["source"] == result.get("link", "") for news in news_opportunities):
                        continue
                        
                    # Skip job listings
                    if any(x in result.get("link", "").lower() for x in ["job", "career", "vacancy", "hiring"]):
                        continue
                        
                    # Fetch the news article
                    news_text =  fetch_url(result.get("link"), full_text=True)
                    
                    # Skip if it's likely a job posting based on content
                    if any(x in news_text.lower() for x in ["apply now", "job description", "responsibilities:", "requirements:", "qualifications:"]):
                        continue
                        
                    # Analyze the news for business opportunities
                    opportunity_info =  analyze_news_for_opportunities(news_text, company_name)
                    
                    # Only include if opportunities were found
                    if opportunity_info["found"]:
                        news_item = {
                            "title": result.get("title", ""),
                            "source": result.get("link", ""),
                            "snippet": result.get("snippet", ""),
                            "date": result.get("date", ""),
                            "opportunity_type": opportunity_info["opportunity_type"],
                            "opportunity_summary": opportunity_info["summary"],
                            "opportunity_details": opportunity_info["details"]
                        }
                        news_opportunities.append(news_item)
    
    # If we still don't have enough opportunities, add placeholders
    if len(news_opportunities) < MIN_NEWS_OPPORTUNITIES:
        missing_count = MIN_NEWS_OPPORTUNITIES - len(news_opportunities)
        for i in range(missing_count):
            placeholder_news = {
                "title": f"Business Opportunity (Not Found) #{i+1}",
                "source": "",
                "snippet": f"Could not retrieve sufficient business opportunity news for {company_name}. This is a placeholder to meet the minimum required news items.",
                "date": "",
                "opportunity_type": "Unknown Opportunity",
                "opportunity_summary": f"No specific business opportunity information available for placeholder #{i+1}",
                "opportunity_details": "No details available"
            }
            news_opportunities.append(placeholder_news)
    state.browsed_opportunity_from_news=news_opportunities  
    
    return state


def opportunity_linkedin_browsing_node(state:OpportunityEnrichmentState):
    """
    Extract LinkedIn company information.
    
    Args:
        company_name: Name of the company
        
    Returns:
        Dictionary with about and recent posts
    """
    # Search for the company's LinkedIn page
    company_name=state.processed_data


    search_query = f"{company_name} company linkedin"
    search_results = search_web(search_query)
    
    linkedin_data = {
        "company_name": company_name,
        "recent_posts": []
    }
    
 
    # Try to get posts by searching for them - increase search results to get at least MIN_LINKEDIN_POSTS
    posts_search_query = f"site:linkedin.com/posts {company_name}"
    
    # First attempt with more results
    posts_results =  search_web(posts_search_query, num_results=MIN_LINKEDIN_POSTS * 2)
    
    if posts_results and "organic" in posts_results:
        for result in posts_results.get("organic", []):
            if "linkedin.com/posts/" in result.get("link", ""):
                post = {
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "url": result.get("link", "")
                }
                linkedin_data["recent_posts"].append(post)
    
    # If we still don't have enough posts, try with different queries
    if len(linkedin_data["recent_posts"]) < MIN_LINKEDIN_POSTS:
        # Try additional search queries with different terms
        additional_queries = [
            f"{company_name} linkedin posts update",
            f"{company_name} linkedin announcement",
            f"{company_name} linkedin news",
            f"linkedin.com/posts {company_name} recent"
        ]
        
        for query in additional_queries:
            if len(linkedin_data["recent_posts"]) >= MIN_LINKEDIN_POSTS:
                break
                
            additional_results =  search_web(query, num_results=MIN_LINKEDIN_POSTS)
            if additional_results and "organic" in additional_results:
                for result in additional_results.get("organic", []):
                    if "linkedin.com/posts/" in result.get("link", ""):
                        # Check if we already have this post
                        if any(post["url"] == result.get("link", "") for post in linkedin_data["recent_posts"]):
                            continue
                            
                        post = {
                            "title": result.get("title", ""),
                            "snippet": result.get("snippet", ""),
                            "url": result.get("link", "")
                        }
                        linkedin_data["recent_posts"].append(post)
    
    # If we still don't have enough, add placeholders with explanation
    if len(linkedin_data["recent_posts"]) < MIN_LINKEDIN_POSTS:
        missing_count = MIN_LINKEDIN_POSTS - len(linkedin_data["recent_posts"])
        for i in range(missing_count):
            placeholder_post = {
                "title": f"LinkedIn Post (Not Found) #{i+1}",
                "snippet": f"Could not retrieve sufficient LinkedIn posts for {company_name}. This is a placeholder to meet the minimum required posts.",
                "url": ""
            }
            linkedin_data["recent_posts"].append(placeholder_post)
    state.browsed_opportunity_from_linkedin=linkedin_data

    return state


def opportunity_enrichment_node(state:OpportunityEnrichmentState):
    print("Enriching opportunity data...")
    # Enrichment logic here
    print("Enriching company data...")
    # Insert enrichment logic here
    merged_opportunity = state.browsed_opportunity_from_linkedin.copy()
    merged_opportunity["news_opportunities"] = state.browsed_opportunity_from_news

# Step 2: Convert to a string (JSON format is most LLM-friendly)
    result_string = json.dumps(merged_opportunity)
    response = client.chat.completions.create(model="claude-4.5-sonnet", messages = [
            {
            "role": "system",
            "content": prompts.OPPORTUNITY_ENRICHMENT_PROMPT
        },
        {
            "role": "user",
            "content": "Company: " + state.processed_data + "\n" + result_string
        }
    ])
    response_dict=response.choices[0].message.content
    state.enrichment_opportunity=response_dict
    return state


# Build the graph
graph = StateGraph(OpportunityEnrichmentState)

# Register nodes


graph.add_node("opportunity_news_browsing_node", opportunity_news_browsing_node)
graph.add_node("opportunity_linkedin_browsing_node", opportunity_linkedin_browsing_node)
graph.add_node("opportunity_enrichment_node", opportunity_enrichment_node)

# Define transitions (edges)
graph.add_edge(START, "opportunity_news_browsing_node")
graph.add_edge("opportunity_news_browsing_node", "opportunity_linkedin_browsing_node")
graph.add_edge("opportunity_linkedin_browsing_node", "opportunity_enrichment_node")
graph.add_edge("opportunity_enrichment_node", END)


opportunity_enrichment_graph = graph.compile()



def run_opportunity_enrichment(company_name: str) -> dict:
    """
    Run the opportunity enrichment workflow for a company
    
    Args:
        company_name: Name of the company to find opportunities for
        
    Returns:
        Dictionary with opportunity data
    """
    initial_state = {"processed_data": company_name}
    result = opportunity_enrichment_graph.invoke(initial_state)
    return result

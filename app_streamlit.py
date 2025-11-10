import streamlit as st
import requests
import json

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="LeadGenrich - AI Lead Enrichment",
    page_icon="🎯",
    layout="wide"
)

# Custom CSS for professional dashboard styling
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    /* Step section headers - dark professional look */
    .step-card {
        background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
        padding: 1.2rem;
        border-radius: 10px;
        margin: 1.5rem 0 1rem 0;
        color: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .step-card h2 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 600;
    }
    .step-card p {
        margin: 0.3rem 0 0 0;
        opacity: 0.9;
        font-size: 0.95rem;
    }
    
    /* Result cards - clean white with subtle borders */
    .result-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .success-card {
        background: linear-gradient(135deg, #f0fff4 0%, #e6ffed 100%);
        border-left: 5px solid #28a745;
    }
    .warning-card {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border-left: 5px solid #f59e0b;
    }
    .info-card {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border-left: 5px solid #3b82f6;
    }
    
    /* Metric boxes - professional cards */
    .metric-box {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        border: 1px solid #f0f0f0;
        transition: transform 0.2s;
    }
    .metric-box:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.15);
    }
    
    /* Progress indicators */
    .step-indicator {
        display: inline-block;
        width: 45px;
        height: 45px;
        border-radius: 50%;
        background: #e0e0e0;
        color: white;
        text-align: center;
        line-height: 45px;
        font-weight: bold;
        font-size: 1.1rem;
        margin-right: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    .step-complete {
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
    }
    .step-pending {
        background: #9ca3af;
    }
    
    /* Divider line */
    .divider {
        height: 2px;
        background: linear-gradient(to right, rgba(102, 126, 234, 0.3), rgba(118, 75, 162, 0.3));
        margin: 1.5rem 0;
        border: none;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Button styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'lead_data' not in st.session_state:
    st.session_state.lead_data = {}
if 'metadata' not in st.session_state:
    st.session_state.metadata = {}
if 'opportunities' not in st.session_state:
    st.session_state.opportunities = {}
if 'score_data' not in st.session_state:
    st.session_state.score_data = {}
if 'routing_data' not in st.session_state:
    st.session_state.routing_data = {}
if 'steps_completed' not in st.session_state:
    st.session_state.steps_completed = {
        'input': False,
        'metadata': False,
        'opportunities': False,
        'score': False,
        'route': False
    }

# Header
st.markdown('<div class="main-header">LeadGenrich - AgentX Lead Enrichment</div>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666; font-size: 1.1rem;">Deloitte AgentX Hackathon 2025 🚀</p>', unsafe_allow_html=True)

# Progress Indicators
col1, col2, col3, col4 = st.columns(4)
with col1:
    status = "step-complete" if st.session_state.steps_completed['metadata'] else "step-pending"
    st.markdown(f'<div style="text-align: center;"><span class="step-indicator {status}">1</span><br>Metadata</div>', unsafe_allow_html=True)
with col2:
    status = "step-complete" if st.session_state.steps_completed['opportunities'] else "step-pending"
    st.markdown(f'<div style="text-align: center;"><span class="step-indicator {status}">2</span><br>Opportunities</div>', unsafe_allow_html=True)
with col3:
    status = "step-complete" if st.session_state.steps_completed['score'] else "step-pending"
    st.markdown(f'<div style="text-align: center;"><span class="step-indicator {status}">3</span><br>ICP Score</div>', unsafe_allow_html=True)
with col4:
    status = "step-complete" if st.session_state.steps_completed['route'] else "step-pending"
    st.markdown(f'<div style="text-align: center;"><span class="step-indicator {status}">4</span><br>SDR Routing</div>', unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ===== INPUT FORM =====
st.markdown('<div class="step-card"><h2>📝 Step 1: Enter Lead Information</h2></div>', unsafe_allow_html=True)

with st.form("lead_input"):
    col1, col2 = st.columns(2)
    
    with col1:
        lead_name = st.text_input("Lead Name *", placeholder="Sarah Johnson")
        company = st.text_input("Company Name *", placeholder="Salesforce")
        email = st.text_input("Email", placeholder="sarah@salesforce.com")
    
    with col2:
        phone = st.text_input("Phone", placeholder="+1-555-0123")
        website = st.text_input("Website", placeholder="www.salesforce.com")
        job_title = st.text_input("Job Title", placeholder="VP of Sales")
    
    submitted = st.form_submit_button("💾 Save Lead Information", use_container_width=True)
    
    if submitted:
        if not lead_name or not company:
            st.error("❌ Please provide at least Lead Name and Company Name!")
        else:
            st.session_state.lead_data = {
                "name": lead_name,
                "company": company,
                "email": email if email else None,
                "phone": phone if phone else None,
                "website": website if website else None,
                "job_title": job_title if job_title else None
            }
            st.session_state.steps_completed['input'] = True
            st.success("✅ Lead information saved!")
            st.rerun()

# Show saved lead info
if st.session_state.steps_completed['input']:
    st.markdown('<div class="result-card success-card">', unsafe_allow_html=True)
    st.markdown(f"**✅ Lead Saved:** {st.session_state.lead_data.get('name')} from {st.session_state.lead_data.get('company')}")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ===== STEP 2: METADATA ENRICHMENT =====
st.markdown('<div class="step-card"><h2>🔍 Step 2: Get Metadata (ICP Fields)</h2><p>Extract industry, company size, and location from web data</p></div>', unsafe_allow_html=True)

if st.button("🔍 Run Metadata Enrichment", use_container_width=True, disabled=not st.session_state.steps_completed['input']):
    with st.spinner("🔄 Enriching metadata..."):
        try:
            response = requests.post(
                f"{API_BASE_URL}/enrich",
                json={"lead": st.session_state.lead_data},
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            st.session_state.metadata = result.get('enriched_lead', {})
            st.session_state.steps_completed['metadata'] = True
            st.success("✅ Metadata enrichment complete!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Display metadata results
if st.session_state.steps_completed['metadata']:
    st.markdown('<div class="result-card info-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Enriched Metadata")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**🏢 Industry**")
        industry = st.session_state.metadata.get('industry', '') or 'Not Available'
        st.markdown(f"<h5>{industry}</h5>", unsafe_allow_html=True)
    with col2:       
        st.markdown(f"**👥 Company Size**")
        company_size = st.session_state.metadata.get('company_size', '') or 'Not Available'
        st.markdown(f"<h5>{company_size}</h5>", unsafe_allow_html=True)      

    with col3:
        st.markdown(f"**📍 Location**")
        location = st.session_state.metadata.get('headquarters_location', '') or 'Not Available'
        st.markdown(f"<h5>{location}</h5>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    
    # Display additional enriched metadata fields
    st.markdown("---")
    st.markdown("#### 🔍 Detailed Enrichment Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Technologies
        technologies = st.session_state.metadata.get('technologies', [])
        if technologies and len(technologies) > 0:
            st.markdown("**🔧 Technologies:**")
            for tech in technologies[:10]:  # Show first 10
                st.markdown(f"• {tech}")
        else:
            st.markdown("**🔧 Technologies:** Not Available")
        
        st.markdown("")  # Spacer
        
        # Products & Services
        products = st.session_state.metadata.get('products_services', [])
        if products and len(products) > 0:
            st.markdown("**📦 Products & Services:**")
            for product in products[:10]:  # Show first 10
                st.markdown(f"• {product}")
        else:
            st.markdown("**📦 Products & Services:** Not Available")
    
    with col2:
        # Strategic Focus
        strategic = st.session_state.metadata.get('strategic_focus', [])
        if strategic and len(strategic) > 0:
            st.markdown("**🎯 Strategic Focus:**")
            for focus in strategic[:10]:  # Show first 10
                st.markdown(f"• {focus}")
        else:
            st.markdown("**🎯 Strategic Focus:** Not Available")
        
        st.markdown("")  # Spacer
        
        # Company Culture
        culture = st.session_state.metadata.get('company_culture', '')
        if culture:
            st.markdown("**🏢 Company Culture:**")
            st.markdown(f"{culture}")
        else:
            st.markdown("**🏢 Company Culture:** Not Available")
        
        st.markdown("")  # Spacer
        
        # Data Confidence
        confidence = st.session_state.metadata.get('data_confidence', '')
        if confidence:
            confidence_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(confidence.lower(), "⚪")
            st.markdown(f"**✅ Data Confidence:** {confidence_emoji} {confidence.capitalize()}")
        else:
            st.markdown("**✅ Data Confidence:** Not Available")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ===== STEP 3: OPPORTUNITY ENRICHMENT =====
st.markdown('<div class="step-card"><h2>💼 Step 3: Get Business Opportunities</h2><p>Identify potential sales opportunities from news and social media</p></div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col1:
    st.info("💡 Discover sales opportunities based on recent news, partnerships, and business initiatives.")
with col2:
    if st.button("⏭️ Skip This Step", disabled=not st.session_state.steps_completed['metadata']):
        st.session_state.steps_completed['opportunities'] = True
        st.session_state.opportunities = {"status": "skipped"}
        st.rerun()

if st.button("💼 Find Business Opportunities", use_container_width=True, disabled=not st.session_state.steps_completed['metadata']):
    with st.spinner("🔄 Analyzing recent news and activities..."):
        try:

            response = requests.post(
                f"{API_BASE_URL}/opportunities",
                json={"lead": st.session_state.lead_data},
                timeout=90
            )
            response.raise_for_status()
            result = response.json()

            # Extract opportunities from the response
            st.session_state.opportunities = result.get('opportunities', {})
            st.session_state.steps_completed['opportunities'] = True
            st.success("✅ Business opportunities identified!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Display opportunity results
if st.session_state.steps_completed['opportunities'] and st.session_state.opportunities.get('status') != 'skipped':
    opportunities_data = st.session_state.opportunities
    
    st.markdown('<div class="result-card info-card">', unsafe_allow_html=True)
    st.markdown("### 💼 Business Opportunities Identified")
    
    # Display AI-generated opportunity summary
    enrichment_summary = opportunities_data.get('enrichment_summary', '')
    if enrichment_summary:
        st.markdown("#### 🤖 AI Analysis Summary")
        st.markdown(enrichment_summary)
        st.markdown("---")
    
    # Display News Opportunities
    news_opportunities = opportunities_data.get('news_opportunities', [])
    if news_opportunities and len(news_opportunities) > 0:
        st.markdown("#### 📰 Recent News & Business Opportunities")
        for idx, news_item in enumerate(news_opportunities[:5], 1):  # Show first 5
            title = news_item.get('title', 'News Item')
            snippet = news_item.get('snippet', '')
            source = news_item.get('source', '')
            opp_type = news_item.get('opportunity_type', 'General')
            opp_summary = news_item.get('opportunity_summary', '')
            date = news_item.get('date', '')
            
            # Emoji based on opportunity type
            emoji_map = {
                'Digital Transformation': '💻',
                'Cloud Migration': '☁️',
                'Data Analytics': '📊',
                'Cybersecurity': '🔒',
                'AI/ML Implementation': '🤖',
                'Brand Development': '📢',
                'Market Expansion': '🌍',
                'E-commerce Development': '🛒',
                'Capital Investment': '💰',
                'Supply Chain Optimization': '⚙️',
                'M&A Activity': '🤝',
                'Strategic Partnership': '🤝',
                'Global Expansion': '🌎',
                'Product Launch': '📦',
                'Sustainability/ESG Initiative': '🌱'
            }
            emoji = emoji_map.get(opp_type, '🎯')
            
            with st.expander(f"{emoji} {title}", expanded=(idx==1)):
                if date:
                    st.caption(f"📅 {date}")
                st.markdown(f"**Opportunity Type:** {opp_type}")
                st.markdown(f"**Summary:** {snippet}")
                if opp_summary:
                    st.markdown(f"**Key Signal:** {opp_summary}")
                if source:
                    st.markdown(f"[🔗 View Source]({source})")
        st.markdown("---")
    
    # Display LinkedIn Posts
    linkedin_posts = opportunities_data.get('linkedin_posts', [])
    if linkedin_posts and len(linkedin_posts) > 0:
        st.markdown("#### 💼 Recent LinkedIn Activity")
        for idx, post in enumerate(linkedin_posts[:3], 1):  # Show first 3
            title = post.get('title', 'LinkedIn Post')
            snippet = post.get('snippet', '')
            url = post.get('url', '')
            
            with st.expander(f"💼 {title}"):
                st.markdown(snippet)
                if url:
                    st.markdown(f"[🔗 View Post]({url})")
    else:
        if not news_opportunities:
            st.info("No specific opportunities found at this time.")
    
    st.markdown('</div>', unsafe_allow_html=True)
elif st.session_state.steps_completed['opportunities']:
    st.markdown('<div class="result-card warning-card">', unsafe_allow_html=True)
    st.markdown("### ⏩ Opportunities Step Skipped")
    st.markdown("Proceeding directly to ICP scoring.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ===== STEP 4: ICP SCORING =====
st.markdown('<div class="step-card"><h2>🎯 Step 4: Calculate Ideal Customer Profile (ICP) Score</h2><p>Score lead against Ideal Customer Profile (0-100 points)</p></div>', unsafe_allow_html=True)

if st.button("🎯 Calculate ICP Score", use_container_width=True, disabled=not st.session_state.steps_completed['opportunities']):
    with st.spinner("🔄 Calculating ICP score..."):
        try:
            # Merge metadata and opportunity data for comprehensive scoring
            enriched_lead = st.session_state.metadata.copy()
            
            # Extract opportunity signals from opportunities data
            opportunity_signals = []
            if st.session_state.opportunities and st.session_state.opportunities.get('status') != 'skipped':
                news_opps = st.session_state.opportunities.get('news_opportunities', [])
                for news_item in news_opps:
                    opp_type = news_item.get('opportunity_type', '')
                    if opp_type:
                        opportunity_signals.append(opp_type)
            
            # Add opportunity signals to enriched_lead
            enriched_lead['opportunity_signals'] = opportunity_signals
            
            response = requests.post(
                f"{API_BASE_URL}/score",
                json={"enriched_lead": enriched_lead},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            st.session_state.score_data = result
            st.session_state.steps_completed['score'] = True
            st.success("✅ ICP score calculated!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Display score results
if st.session_state.steps_completed['score']:
    score = st.session_state.score_data.get('icp_score', 0)
    breakdown = st.session_state.score_data.get('score_breakdown', {})
    recommendation = st.session_state.score_data.get('score_recommendation', '')
    
    # Determine grade and color (updated for 100-point scale)
    if score >= 90:
        grade = "A+"
        badge = "🔥 Hot Lead"
        card_class = "success-card"
    elif score >= 80:
        grade = "A"
        badge = "⭐ High Priority"
        card_class = "success-card"
    elif score >= 70:
        grade = "B+"
        badge = "✅ Qualified"
        card_class = "success-card"
    elif score >= 60:
        grade = "B"
        badge = "💡 Potential"
        card_class = "warning-card"
    else:
        grade = "C"
        badge = "❌ Below Threshold"
        card_class = "result-card"
    
    st.markdown(f'<div class="result-card {card_class}">', unsafe_allow_html=True)
    st.markdown("### 🎯 ICP Score Results")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"<h1 style='color: #1f77b4; margin: 0;'>{score}/100</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size: 1.2rem; margin: 0;'><strong>Grade: {grade}</strong></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin: 0;'>{badge}</p>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("**📊 Score Breakdown:**")
        # Display 6 categories in 2 rows of 3
        row1_col1, row1_col2, row1_col3 = st.columns(3)
        with row1_col1:
            st.metric("Industry", f"{breakdown.get('industry', 0)}/20")
        with row1_col2:
            st.metric("Company Size", f"{breakdown.get('company_size', 0)}/20")
        with row1_col3:
            st.metric("Technologies", f"{breakdown.get('technologies', 0)}/15")
        
        row2_col1, row2_col2, row2_col3 = st.columns(3)
        with row2_col1:
            st.metric("Strategic Focus", f"{breakdown.get('strategic_focus', 0)}/15")
        with row2_col2:
            st.metric("Location", f"{breakdown.get('location', 0)}/10")
        with row2_col3:
            st.metric("Opportunities", f"{breakdown.get('opportunities', 0)}/20")
    
    if recommendation:
        st.info(f"💡 **Recommendation:** {recommendation}")
    
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ===== STEP 5: SDR ROUTING =====
st.markdown('<div class="step-card"><h2>👤 Step 5: Route to Sales Representative</h2><p>Assign lead to the best-matching SDR based on territory and expertise</p></div>', unsafe_allow_html=True)

if st.button("👤 Route to SDR", use_container_width=True, disabled=not st.session_state.steps_completed['score']):
    with st.spinner("🔄 Finding best sales rep..."):
        try:
            score = st.session_state.score_data.get('icp_score', 0)
            response = requests.post(
                f"{API_BASE_URL}/route",
                json={
                    "enriched_lead": st.session_state.metadata,
                    "icp_score": score
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            st.session_state.routing_data = result
            st.session_state.steps_completed['route'] = True
            st.success("✅ Lead routed successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Display routing results
if st.session_state.steps_completed['route']:
    assigned_rep = st.session_state.routing_data.get('assigned_rep', 'Unassigned')
    rep_email = st.session_state.routing_data.get('rep_email', '')
    routing_reason = st.session_state.routing_data.get('routing_reason', '')
    
    if "Unassigned" not in assigned_rep:
        st.markdown('<div class="result-card success-card">', unsafe_allow_html=True)
        st.markdown("### ✅ Lead Successfully Routed")
        
        col1, col2 = st.columns([1, 2])
        with col1:
           
            st.markdown(f"<h2 style='color: #28a745; margin: 0;'>👤 {assigned_rep}</h2>", unsafe_allow_html=True)
            if rep_email:
                st.markdown(f"<p style='margin: 0.5rem 0;'>📧 {rep_email}</p>", unsafe_allow_html=True)
          
        
        with col2:
            st.markdown("**📝 AI Routing Decision:**")
            st.write(routing_reason)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Show available sales team for reference
        with st.expander("👥 View All Available Sales Reps"):
            st.markdown("**Available Sales Representatives:**")
            
            sales_team = [
                {"name": "Sarah Chen", "email": "sarah.chen@deloitte.com", "territory": "USA - West Coast", 
                 "focus": "SaaS, Cloud, Technology, Fintech", "min_score": "70+", "min_size": "200+"},
                {"name": "Mike Johnson", "email": "mike.johnson@deloitte.com", "territory": "USA - East Coast",
                 "focus": "Manufacturing, Healthcare, E-commerce", "min_score": "60+", "min_size": "100+"},
                {"name": "Emma Wilson", "email": "emma.wilson@deloitte.com", "territory": "Canada",
                 "focus": "SaaS, Retail, Fintech", "min_score": "60+", "min_size": "100+"},
                {"name": "David Lee", "email": "david.lee@deloitte.com", "territory": "UK / Europe",
                 "focus": "SaaS, Fintech", "min_score": "65+", "min_size": "150+"}
            ]
            
            for rep in sales_team:
                is_assigned = (rep["name"] == assigned_rep)
                if is_assigned:
                    st.markdown(f"""
                    <div style="background: #d4edda; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #28a745;">
                        <h4 style="margin: 0; color: #155724;">✅ {rep['name']} (ASSIGNED)</h4>
                        <p style="margin: 0.25rem 0;"><strong>📧 Email:</strong> {rep['email']}</p>
                        <p style="margin: 0.25rem 0;"><strong>🌍 Territory:</strong> {rep['territory']}</p>
                        <p style="margin: 0.25rem 0;"><strong>🎯 Industry Focus:</strong> {rep['focus']}</p>
                        <p style="margin: 0.25rem 0;"><strong>📊 Requirements:</strong> Score {rep['min_score']}, Size {rep['min_size']} employees</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #ccc;">
                        <h4 style="margin: 0; color: #666;">👤 {rep['name']}</h4>
                        <p style="margin: 0.25rem 0; color: #666;"><strong>📧 Email:</strong> {rep['email']}</p>
                        <p style="margin: 0.25rem 0; color: #666;"><strong>🌍 Territory:</strong> {rep['territory']}</p>
                        <p style="margin: 0.25rem 0; color: #666;"><strong>🎯 Industry Focus:</strong> {rep['focus']}</p>
                        <p style="margin: 0.25rem 0; color: #666;"><strong>📊 Requirements:</strong> Score {rep['min_score']}, Size {rep['min_size']} employees</p>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="result-card warning-card">', unsafe_allow_html=True)
        st.markdown(f"### ⚠️ {assigned_rep}")
        st.write(f"**Reason:** {routing_reason}")
        
        # Show why lead didn't qualify
        st.markdown("---")
        st.markdown("**💡 Tip:** Lead may not meet minimum requirements for any sales rep:")
        st.markdown("- Minimum ICP Score: 60/90")
        st.markdown("- Check territory and industry match")
        st.markdown("- Ensure company size meets requirements")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Reset button
if st.session_state.steps_completed['input']:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    if st.button("🔄 Process New Lead", type="secondary", use_container_width=True):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

# Sidebar
with st.sidebar:
    st.markdown("### ℹ️ About LeadGenrich")
    st.markdown("""
    **AI-Powered Lead Processing**
    
    - 🔍 Metadata Enrichment
    - 💼 Opportunity Discovery
    - 🎯 ICP Scoring (0-100)
    - 👤 Smart SDR Routing
    
    **Built with:**
    - LangGraph
    - claude-4.5-sonnet
    - FastAPI
    - Streamlit
    """)
    
    st.markdown("---")
    st.markdown("**Deloitte AgentX Hackathon 2025** 🚀")

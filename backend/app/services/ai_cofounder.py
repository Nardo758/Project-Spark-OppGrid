"""
AI Co-Founder Service
Stage-aware conversational AI assistant that guides users through their opportunity journey.
Uses Replit's AI Integrations for Anthropic-compatible API access.
Supports BYOK (Bring Your Own Key) for users with their own Claude API keys.
"""

import os
import re
from anthropic import Anthropic
from app.services.serpapi_service import SerpAPIService

AI_INTEGRATIONS_ANTHROPIC_API_KEY = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
AI_INTEGRATIONS_ANTHROPIC_BASE_URL = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

serpapi_service = SerpAPIService()

def get_anthropic_client(user_api_key: str = None) -> tuple[Anthropic, str]:
    """
    Get an Anthropic client, preferring user's BYOK key if provided.
    Falls back to direct ANTHROPIC_API_KEY, then Replit AI Integrations.
    
    Returns:
        tuple: (Anthropic client, key_source: "byok" | "direct" | "platform")
    """
    if user_api_key:
        return Anthropic(api_key=user_api_key), "byok"
    
    if ANTHROPIC_API_KEY:
        return Anthropic(api_key=ANTHROPIC_API_KEY), "direct"
    
    return Anthropic(
        api_key=AI_INTEGRATIONS_ANTHROPIC_API_KEY,
        base_url=AI_INTEGRATIONS_ANTHROPIC_BASE_URL
    ), "platform"

if ANTHROPIC_API_KEY:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    client = Anthropic(
        api_key=AI_INTEGRATIONS_ANTHROPIC_API_KEY,
        base_url=AI_INTEGRATIONS_ANTHROPIC_BASE_URL
    )

STAGE_PROMPTS = {
    "researching": """You are an AI Co-Founder helping a user in the RESEARCH stage of their business opportunity.

Your role is to help them:
- Analyze market data and identify trends
- Map out competitors and their strengths/weaknesses
- Find gaps in the market they can exploit
- Understand the target customer profile
- Estimate market size and growth potential

Be encouraging but realistic. Ask probing questions to help them think deeper about the opportunity.
Provide specific, actionable insights based on the opportunity details provided.""",

    "validating": """You are an AI Co-Founder helping a user in the VALIDATION stage of their business opportunity.

Your role is to help them:
- Design customer interviews and surveys
- Interpret feedback and identify patterns
- Distinguish between nice-to-have and must-have features
- Identify early adopter segments
- Build a minimum viable test strategy
- Assess demand signals and willingness to pay

Help them avoid confirmation bias. Challenge their assumptions constructively.
Guide them to find real evidence of customer demand.""",

    "planning": """You are an AI Co-Founder helping a user in the PLANNING stage of their business opportunity.

Your role is to help them:
- Choose the right business model (subscription, marketplace, SaaS, services, etc.)
- Create revenue projections and financial models
- Define their go-to-market strategy
- Identify key metrics and milestones
- Plan resource requirements (team, budget, timeline)
- Prepare investor-ready materials

Help them create a comprehensive business plan they can share with experts, investors, and lenders.
Be thorough and professional - this plan needs to convince stakeholders.""",

    "building": """You are an AI Co-Founder helping a user in the BUILD stage of their business opportunity.

Your role is to help them:
- Create an execution roadmap with clear milestones
- Recommend the right tools for their needs:
  * Design: Figma, Canva, Framer
  * Development: Replit, Vercel, Supabase, Firebase
  * Talent: Upwork, Toptal, Contra, Fiverr
  * No-Code: Bubble, Webflow, Zapier, Airtable
  * Marketing: Mailchimp, Buffer, Hootsuite
  * Project Management: Notion, Trello, Linear
- Help them prioritize what to build first (MVP scope)
- Connect them with the right experts for execution
- Manage budget and timeline expectations

Focus on practical execution. Help them move from plan to reality efficiently.
Recommend specific tools based on their budget, technical ability, and timeline.""",

    "launched": """You are an AI Co-Founder helping a user who has LAUNCHED their business opportunity.

Your role is to help them:

**Business Formation:**
- Guide LLC vs S-Corp vs Sole Proprietorship decision
- Explain state-specific registration steps
- Walk through EIN registration process
- Recommend business bank accounts
- Explain operating agreement basics

**Legal & Compliance:**
- Identify required business licenses
- Recommend appropriate insurance
- Guide Terms of Service / Privacy Policy creation
- Explain trademark and IP basics

**Financial Setup:**
- Recommend accounting software (QuickBooks, Wave, Xero)
- Guide payment processing setup (Stripe, Square, PayPal)
- Explain tax obligations and quarterly estimates
- Set up basic bookkeeping practices

**Growth & Scaling:**
- Identify key metrics to track
- Plan for first hires
- Explore funding options for growth
- Optimize operations

Help them transition from a project to a real, legally established business.
Be practical and specific to their situation."""
}

TOOL_RECOMMENDATIONS = {
    "design": [
        {"name": "Figma", "url": "https://figma.com", "description": "Collaborative design tool for UI/UX", "price": "Free - $15/mo", "best_for": "Professional design, team collaboration"},
        {"name": "Canva", "url": "https://canva.com", "description": "Easy graphic design for non-designers", "price": "Free - $13/mo", "best_for": "Marketing materials, social media"},
        {"name": "Framer", "url": "https://framer.com", "description": "Design to production websites", "price": "Free - $20/mo", "best_for": "Landing pages, marketing sites"},
    ],
    "development": [
        {"name": "Replit", "url": "https://replit.com", "description": "AI-powered development platform", "price": "Free - $25/mo", "best_for": "Full-stack apps, rapid prototyping"},
        {"name": "Vercel", "url": "https://vercel.com", "description": "Frontend deployment platform", "price": "Free - $20/mo", "best_for": "Next.js, React apps"},
        {"name": "Supabase", "url": "https://supabase.com", "description": "Open source Firebase alternative", "price": "Free - $25/mo", "best_for": "Database, auth, real-time"},
        {"name": "Firebase", "url": "https://firebase.google.com", "description": "Google's app development platform", "price": "Pay as you go", "best_for": "Mobile apps, real-time features"},
    ],
    "talent": [
        {"name": "Upwork", "url": "https://upwork.com", "description": "Large freelancer marketplace", "price": "Commission-based", "best_for": "Budget-friendly, variety of skills"},
        {"name": "Toptal", "url": "https://toptal.com", "description": "Top 3% of freelancers", "price": "Premium rates", "best_for": "High-quality, vetted talent"},
        {"name": "Contra", "url": "https://contra.com", "description": "Commission-free freelancing", "price": "No fees", "best_for": "Direct relationships, portfolios"},
        {"name": "Fiverr", "url": "https://fiverr.com", "description": "Quick, affordable gigs", "price": "Starting at $5", "best_for": "Small tasks, quick turnaround"},
    ],
    "nocode": [
        {"name": "Bubble", "url": "https://bubble.io", "description": "Full-featured no-code web apps", "price": "Free - $32/mo", "best_for": "Complex web applications"},
        {"name": "Webflow", "url": "https://webflow.com", "description": "Visual website builder", "price": "Free - $24/mo", "best_for": "Marketing sites, CMS"},
        {"name": "Zapier", "url": "https://zapier.com", "description": "Automate workflows between apps", "price": "Free - $20/mo", "best_for": "Integrations, automation"},
        {"name": "Airtable", "url": "https://airtable.com", "description": "Spreadsheet-database hybrid", "price": "Free - $20/mo", "best_for": "Data management, simple apps"},
    ],
    "marketing": [
        {"name": "Mailchimp", "url": "https://mailchimp.com", "description": "Email marketing platform", "price": "Free - $13/mo", "best_for": "Email campaigns, newsletters"},
        {"name": "Buffer", "url": "https://buffer.com", "description": "Social media scheduling", "price": "Free - $6/mo", "best_for": "Social media management"},
        {"name": "SEMrush", "url": "https://semrush.com", "description": "SEO and marketing toolkit", "price": "$120/mo+", "best_for": "SEO, competitor analysis"},
    ],
    "project": [
        {"name": "Notion", "url": "https://notion.so", "description": "All-in-one workspace", "price": "Free - $10/mo", "best_for": "Docs, wikis, project management"},
        {"name": "Linear", "url": "https://linear.app", "description": "Modern issue tracking", "price": "Free - $8/mo", "best_for": "Software development teams"},
        {"name": "Trello", "url": "https://trello.com", "description": "Visual kanban boards", "price": "Free - $10/mo", "best_for": "Simple task management"},
    ],
    "financial": [
        {"name": "QuickBooks", "url": "https://quickbooks.intuit.com", "description": "Small business accounting", "price": "$30/mo+", "best_for": "Full accounting, invoicing"},
        {"name": "Wave", "url": "https://waveapps.com", "description": "Free accounting software", "price": "Free", "best_for": "Freelancers, small businesses"},
        {"name": "Stripe", "url": "https://stripe.com", "description": "Payment processing", "price": "2.9% + 30¢/txn", "best_for": "Online payments, subscriptions"},
        {"name": "Mercury", "url": "https://mercury.com", "description": "Startup banking", "price": "Free", "best_for": "Business bank account, startups"},
    ],
}

BUSINESS_FORMATION_GUIDE = {
    "llc": {
        "name": "Limited Liability Company (LLC)",
        "best_for": "Most small businesses, flexibility",
        "pros": ["Personal asset protection", "Pass-through taxation", "Flexible management", "Less paperwork than corp"],
        "cons": ["Self-employment taxes", "Varies by state", "Can't issue stock"],
        "cost": "$50-500 state filing fee",
        "steps": [
            "Choose your state (usually where you operate)",
            "Pick a unique business name",
            "File Articles of Organization with state",
            "Create an Operating Agreement",
            "Get an EIN from IRS (free, online)",
            "Open a business bank account",
            "Register for state/local licenses"
        ]
    },
    "scorp": {
        "name": "S Corporation",
        "best_for": "Profitable businesses, tax savings",
        "pros": ["Tax savings on self-employment", "Personal asset protection", "Credibility", "Can issue stock"],
        "cons": ["More paperwork", "Stricter requirements", "Salary requirements", "State fees"],
        "cost": "$100-800 state filing fee + ongoing fees",
        "steps": [
            "Form an LLC or C-Corp first",
            "File Form 2553 with IRS for S-Corp election",
            "Set up payroll for owner-employees",
            "Maintain corporate formalities",
            "File separate business tax return"
        ]
    },
    "sole_prop": {
        "name": "Sole Proprietorship",
        "best_for": "Testing ideas, very small operations",
        "pros": ["Simplest to start", "No filing required", "All profits are yours", "Easy taxes"],
        "cons": ["No liability protection", "Harder to get funding", "Less credible", "Personal assets at risk"],
        "cost": "Free (just DBA if using different name)",
        "steps": [
            "Start operating (that's it for federal)",
            "File DBA if using a business name",
            "Get required local licenses",
            "Keep business records separate"
        ]
    }
}


def get_stage_prompt(stage: str) -> str:
    """Get the system prompt for a given stage."""
    return STAGE_PROMPTS.get(stage, STAGE_PROMPTS["researching"])


def build_context(opportunity: dict, workspace: dict) -> str:
    """Build context string from opportunity and workspace data."""
    context_parts = []
    
    context_parts.append(f"**Opportunity:** {opportunity.get('title', 'Untitled')}")
    context_parts.append(f"**Category:** {opportunity.get('category', 'Unknown')}")
    
    if opportunity.get('description'):
        context_parts.append(f"**Description:** {opportunity['description'][:500]}")
    
    if opportunity.get('ai_problem_statement'):
        context_parts.append(f"**Problem Statement:** {opportunity['ai_problem_statement']}")
    
    if opportunity.get('ai_market_size_estimate'):
        context_parts.append(f"**Market Size:** {opportunity['ai_market_size_estimate']}")
    
    if opportunity.get('ai_competition_level'):
        context_parts.append(f"**Competition:** {opportunity['ai_competition_level']}")
    
    if opportunity.get('ai_target_audience'):
        context_parts.append(f"**Target Audience:** {opportunity['ai_target_audience']}")
    
    context_parts.append(f"\n**Current Stage:** {workspace.get('status', 'researching').upper()}")
    context_parts.append(f"**Progress:** {workspace.get('progress_percent', 0)}%")
    
    return "\n".join(context_parts)


async def chat_with_cofounder(
    message: str,
    stage: str,
    opportunity: dict,
    workspace: dict,
    chat_history: list[dict] = None
) -> str:
    """
    Chat with the AI Co-Founder.
    
    Args:
        message: User's message
        stage: Current workspace stage (researching, validating, planning, building, launched)
        opportunity: Opportunity data dict
        workspace: Workspace data dict
        chat_history: List of previous messages [{"role": "user"|"assistant", "content": "..."}]
    
    Returns:
        AI Co-Founder's response
    """
    system_prompt = get_stage_prompt(stage)
    context = build_context(opportunity, workspace)
    
    full_system = f"""{system_prompt}

---
CURRENT CONTEXT:
{context}
---

Remember: Be helpful, specific, and actionable. Guide them step by step toward success."""

    messages = []
    if chat_history:
        messages.extend(chat_history[-20:])
    
    messages.append({"role": "user", "content": message})
    
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        system=full_system,
        messages=messages
    )
    
    return response.content[0].text


def get_tool_recommendations(category: str = None) -> dict:
    """Get tool recommendations, optionally filtered by category."""
    if category and category in TOOL_RECOMMENDATIONS:
        return {category: TOOL_RECOMMENDATIONS[category]}
    return TOOL_RECOMMENDATIONS


def get_business_formation_guide(entity_type: str = None) -> dict:
    """Get business formation guide, optionally for a specific entity type."""
    if entity_type and entity_type in BUSINESS_FORMATION_GUIDE:
        return {entity_type: BUSINESS_FORMATION_GUIDE[entity_type]}
    return BUSINESS_FORMATION_GUIDE


def detect_tool_intent(message: str) -> tuple[bool, list[str]]:
    """
    Detect if user is asking about tools and which categories.
    
    Returns:
        tuple: (should_show_tools, list of relevant categories)
    """
    lower_msg = message.lower()
    
    tool_triggers = [
        "tool", "software", "app", "platform", "build", "create", "design",
        "develop", "code", "website", "marketing", "accounting", "freelancer",
        "hire", "automation", "no-code", "nocode", "payment", "invoice",
        "project management", "manage", "what should i use", "recommend"
    ]
    
    if not any(trigger in lower_msg for trigger in tool_triggers):
        return False, []
    
    category_mapping = {
        "design": ["design", "logo", "graphics", "ui", "ux", "branding", "visual", "figma", "canva"],
        "development": ["develop", "code", "programming", "app", "website", "backend", "frontend", "deploy", "host"],
        "talent": ["hire", "freelancer", "developer", "designer", "contractor", "talent", "outsource", "team"],
        "nocode": ["no-code", "nocode", "no code", "bubble", "webflow", "zapier", "automate", "without coding"],
        "marketing": ["market", "email", "social media", "seo", "ads", "advertis", "promote", "growth"],
        "project": ["project", "manage", "task", "organize", "track", "collaborate", "team", "notion", "trello"],
        "financial": ["finance", "account", "invoice", "payment", "bank", "money", "tax", "bookkeep", "stripe"]
    }
    
    matched_categories = []
    for category, keywords in category_mapping.items():
        if any(kw in lower_msg for kw in keywords):
            matched_categories.append(category)
    
    if not matched_categories:
        matched_categories = ["development", "nocode"]
    
    return True, matched_categories


def detect_funding_intent(message: str) -> bool:
    """Detect if user is asking about funding or financing."""
    lower_msg = message.lower()
    
    funding_triggers = [
        "fund", "loan", "invest", "capital", "money", "financing", "grant",
        "sba", "venture", "angel", "bootstrap", "crowdfund", "raise"
    ]
    
    return any(trigger in lower_msg for trigger in funding_triggers)


def detect_expert_intent(message: str) -> bool:
    """Detect if user is asking about finding experts."""
    lower_msg = message.lower()
    
    expert_triggers = [
        "expert", "consultant", "advisor", "mentor", "coach", "specialist",
        "professional", "help from", "talk to", "hire someone", "get advice"
    ]
    
    return any(trigger in lower_msg for trigger in expert_triggers)


def detect_search_intent(message: str) -> tuple[bool, str]:
    """Detect if user wants to search the web and extract query."""
    search_patterns = [
        r"search (?:the web|online|internet|google) for (.+)",
        r"look up (.+) online",
        r"find (?:information|info|news|articles) (?:about|on) (.+)",
        r"what's the latest (?:on|about) (.+)",
        r"recent news (?:on|about) (.+)",
        r"search for (.+)",
    ]
    
    lower_msg = message.lower()
    for pattern in search_patterns:
        match = re.search(pattern, lower_msg)
        if match:
            return True, match.group(1).strip()
    
    if any(kw in lower_msg for kw in ["search the web", "search online", "look it up", "google it"]):
        return True, message
    
    return False, ""


def web_search(query: str, num_results: int = 5) -> dict:
    """Perform a web search and return formatted results."""
    if not serpapi_service.is_configured:
        return {"error": "Web search is not configured", "results": []}
    
    try:
        results = serpapi_service.google_search(query, num=num_results)
        organic_results = results.get("organic_results", [])
        
        formatted = []
        for r in organic_results[:num_results]:
            formatted.append({
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "link": r.get("link", ""),
                "source": r.get("source", "")
            })
        
        return {
            "query": query,
            "results": formatted,
            "search_info": results.get("search_information", {})
        }
    except Exception as e:
        return {"error": str(e), "results": []}


async def chat_with_cofounder_enhanced(
    message: str,
    stage: str,
    opportunity: dict,
    workspace: dict,
    chat_history: list[dict] = None,
    enable_web_search: bool = True,
    user_api_key: str = None,
    db_tools: list[dict] = None
) -> dict:
    """
    Enhanced chat with web search capability, BYOK support, and inline card detection.
    
    Args:
        user_api_key: User's own Claude API key (BYOK). If provided, uses this instead of platform key.
        db_tools: Tools from database to use for recommendations (optional, falls back to hardcoded).
    
    Returns:
        Dict with 'response', 'key_source', inline_cards, and optionally 'web_search_results'
    """
    web_results = None
    inline_cards = {}
    
    should_show_tools, tool_categories = detect_tool_intent(message)
    should_show_funding = detect_funding_intent(message)
    should_show_experts = detect_expert_intent(message)
    
    if should_show_tools:
        tool_recs = {}
        for cat in tool_categories[:3]:
            if db_tools:
                cat_tools = [t for t in db_tools if t.get("category") == cat][:3]
                if cat_tools:
                    tool_recs[cat] = cat_tools
            elif cat in TOOL_RECOMMENDATIONS:
                tool_recs[cat] = TOOL_RECOMMENDATIONS[cat][:3]
        if tool_recs:
            inline_cards["tools"] = {
                "type": "tools",
                "title": "Recommended Tools",
                "categories": tool_recs
            }
    
    if should_show_funding:
        inline_cards["funding"] = {
            "type": "funding",
            "title": "Funding Options",
            "cta_url": "/build/funding",
            "description": "Explore SBA loans, grants, and financing options"
        }
    
    if should_show_experts:
        inline_cards["experts"] = {
            "type": "experts",
            "title": "Find an Expert",
            "cta_url": "/network/experts",
            "description": "Connect with vetted consultants and advisors"
        }
    
    if enable_web_search:
        should_search, query = detect_search_intent(message)
        if should_search:
            category = opportunity.get('category', '')
            title = opportunity.get('title', '')
            enhanced_query = f"{query} {category} business opportunity" if len(query) < 30 else query
            web_results = web_search(enhanced_query)
    
    system_prompt = get_stage_prompt(stage)
    context = build_context(opportunity, workspace)
    
    web_context = ""
    if web_results and web_results.get("results"):
        web_context = "\n\n---\nWEB SEARCH RESULTS:\n"
        for i, r in enumerate(web_results["results"], 1):
            web_context += f"{i}. **{r['title']}**\n   {r['snippet']}\n   Source: {r['source']}\n\n"
        web_context += "---\nUse these search results to inform your response. Cite sources when relevant."
    
    inline_hint = ""
    if inline_cards:
        inline_hint = "\n\nNote: The UI will display relevant tool/funding/expert cards alongside your response. Reference them naturally but don't list all details - the cards will show specifics."
    
    full_system = f"""{system_prompt}

---
CURRENT CONTEXT:
{context}
{web_context}
---
{inline_hint}
Remember: Be helpful, specific, and actionable. Guide them step by step toward success."""

    messages = []
    if chat_history:
        messages.extend(chat_history[-20:])
    
    messages.append({"role": "user", "content": message})
    
    ai_client, key_source = get_anthropic_client(user_api_key)
    
    response = ai_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        system=full_system,
        messages=messages
    )
    
    return {
        "response": response.content[0].text,
        "key_source": key_source,
        "web_search_performed": web_results is not None,
        "web_search_query": web_results.get("query") if web_results else None,
        "inline_cards": inline_cards if inline_cards else None
    }

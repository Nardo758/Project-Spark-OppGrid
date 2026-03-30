"""
Seed Marketplace Leads

Creates sample leads for the leads marketplace.
Run with: python -m scripts.seed_marketplace_leads
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import random

from app.db.database import SessionLocal
from app.models.lead import Lead, LeadStatus, LeadSource


SAMPLE_LEADS = [
    {
        "name": "TechVenture Capital",
        "email": "deals@techventure.example.com",
        "company": "TechVenture Partners",
        "interest_category": "saas",
        "notes": "Series A investor looking for B2B SaaS opportunities. $2-10M check size. Focus: productivity, developer tools, enterprise software.",
        "source": LeadSource.REFERRAL,
        "status": LeadStatus.QUALIFIED,
    },
    {
        "name": "Healthcare Innovations Group",
        "email": "partnerships@hig.example.com",
        "company": "Healthcare Innovations Group",
        "interest_category": "healthcare",
        "notes": "Strategic acquirer in digital health space. Interest in patient engagement, telehealth, and health data platforms. Revenue: $10M+",
        "source": LeadSource.ORGANIC,
        "status": LeadStatus.QUALIFIED,
    },
    {
        "name": "E-Commerce Accelerator",
        "email": "invest@ecacc.example.com",
        "company": "ECA Ventures",
        "interest_category": "ecommerce",
        "notes": "Pre-seed to Series A investor. Focus: DTC brands, marketplace enablers, logistics tech. Active in 15+ portfolio companies.",
        "source": LeadSource.PARTNER,
        "status": LeadStatus.QUALIFIED,
    },
    {
        "name": "FinTech Growth Fund",
        "email": "opportunities@ftgf.example.com",
        "company": "FinTech Growth Partners",
        "interest_category": "fintech",
        "notes": "Growth equity investor. Looking for payment processing, lending platforms, wealth management tech. $20-50M investments.",
        "source": LeadSource.ORGANIC,
        "status": LeadStatus.QUALIFIED,
    },
    {
        "name": "Manufacturing Tech Consortium",
        "email": "ventures@mtc.example.com",
        "company": "MTC Industrial",
        "interest_category": "manufacturing",
        "notes": "Corporate venture arm of Fortune 500 manufacturer. Interest: IoT, automation, supply chain optimization, predictive maintenance.",
        "source": LeadSource.DIRECT,
        "status": LeadStatus.QUALIFIED,
    },
    {
        "name": "Professional Services Network",
        "email": "acquisitions@psn.example.com",
        "company": "PSN Holdings",
        "interest_category": "services",
        "notes": "Roll-up strategy in professional services. Seeking: accounting firms, marketing agencies, consulting practices. Revenue: $2-15M",
        "source": LeadSource.REFERRAL,
        "status": LeadStatus.NEW,
    },
    {
        "name": "Cloud Infrastructure Ventures",
        "email": "deals@cloudiv.example.com",
        "company": "CloudIV",
        "interest_category": "saas",
        "notes": "Early stage investor. Focus: infrastructure software, security, DevOps tools. Strong technical due diligence team.",
        "source": LeadSource.ORGANIC,
        "status": LeadStatus.CONTACTED,
    },
    {
        "name": "Digital Health Partners",
        "email": "invest@dhp.example.com",
        "company": "DHP Capital",
        "interest_category": "healthcare",
        "notes": "Seed to Series B investor. Portfolio: 30+ digital health companies. Interest: remote monitoring, mental health, clinical trials.",
        "source": LeadSource.SOCIAL,
        "status": LeadStatus.QUALIFIED,
    },
    {
        "name": "Retail Innovation Fund",
        "email": "opportunities@rif.example.com",
        "company": "RIF Capital",
        "interest_category": "ecommerce",
        "notes": "Corporate VC backed by major retailer. Looking for: retail tech, omnichannel, inventory management, customer analytics.",
        "source": LeadSource.PARTNER,
        "status": LeadStatus.QUALIFIED,
    },
    {
        "name": "Embedded Finance Group",
        "email": "ventures@efg.example.com",
        "company": "EFG Investments",
        "interest_category": "fintech",
        "notes": "Specialist investor in embedded finance, BaaS, and API-first financial services. Strong bank partnerships for portfolio companies.",
        "source": LeadSource.ORGANIC,
        "status": LeadStatus.NEW,
    },
    {
        "name": "Smart Factory Alliance",
        "email": "partnerships@sfa.example.com",
        "company": "SFA Industrial Tech",
        "interest_category": "manufacturing",
        "notes": "Consortium of manufacturers seeking technology partners. Interest: robotics, computer vision, digital twin technology.",
        "source": LeadSource.DIRECT,
        "status": LeadStatus.NURTURING,
    },
    {
        "name": "Legal Tech Ventures",
        "email": "invest@ltv.example.com",
        "company": "LTV Capital",
        "interest_category": "services",
        "notes": "Specialized in legal technology investments. Looking for: contract automation, legal research AI, compliance tools.",
        "source": LeadSource.REFERRAL,
        "status": LeadStatus.QUALIFIED,
    },
]


def seed_leads():
    db = SessionLocal()
    try:
        # Check existing leads
        existing_count = db.query(Lead).count()
        print(f"Existing leads: {existing_count}")
        
        created = 0
        for lead_data in SAMPLE_LEADS:
            # Check if lead with this email already exists
            existing = db.query(Lead).filter(Lead.email == lead_data["email"]).first()
            if existing:
                print(f"  Skipping {lead_data['email']} (already exists)")
                continue
            
            lead = Lead(
                name=lead_data["name"],
                email=lead_data["email"],
                company=lead_data["company"],
                interest_category=lead_data["interest_category"],
                notes=lead_data["notes"],
                source=lead_data["source"],
                status=lead_data["status"],
                email_opt_in=True,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            )
            db.add(lead)
            created += 1
            print(f"  Created: {lead_data['company']}")
        
        db.commit()
        print(f"\nSeeded {created} new marketplace leads")
        print(f"Total leads: {db.query(Lead).count()}")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding leads: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_leads()

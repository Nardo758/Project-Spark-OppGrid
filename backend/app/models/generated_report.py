import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class ReportType(str, enum.Enum):
    FEASIBILITY_STUDY = "feasibility_study"
    FEASIBILITY = "feasibility"
    MARKET_ANALYSIS = "market_analysis"
    STRATEGIC_ASSESSMENT = "strategic_assessment"
    STRATEGIC = "strategic"
    PESTLE = "pestle"
    PESTLE_ANALYSIS = "pestle_analysis"
    BUSINESS_PLAN = "business_plan"
    FINANCIAL = "financial"
    FINANCIAL_MODEL = "financial_model"
    PITCH_DECK = "pitch_deck"
    PROGRESS_REPORT = "progress_report"
    LAYER_1_OVERVIEW = "layer_1_overview"
    LAYER_2_DEEP_DIVE = "layer_2_deep_dive"
    LAYER_3_EXECUTION = "layer_3_execution"
    AD_CREATIVES = "ad_creatives"
    BRAND_PACKAGE = "brand_package"
    LANDING_PAGE = "landing_page"
    CONTENT_CALENDAR = "content_calendar"
    EMAIL_FUNNEL = "email_funnel"
    EMAIL_SEQUENCE = "email_sequence"
    LEAD_MAGNET = "lead_magnet"
    SALES_FUNNEL = "sales_funnel"
    SEO_CONTENT = "seo_content"
    TWEET_LANDING = "tweet_landing"
    USER_PERSONAS = "user_personas"
    FEATURE_SPECS = "feature_specs"
    MVP_ROADMAP = "mvp_roadmap"
    PRD = "prd"
    GTM_CALENDAR = "gtm_calendar"
    GTM_STRATEGY = "gtm_strategy"
    KPI_DASHBOARD = "kpi_dashboard"
    PRICING_STRATEGY = "pricing_strategy"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    CUSTOMER_INTERVIEW = "customer_interview"
    LOCATION_ANALYSIS = "location_analysis"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("user_workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    template_id = Column(Integer, ForeignKey("report_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    
    report_type = Column(Enum(ReportType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    status = Column(Enum(ReportStatus, values_callable=lambda x: [e.value for e in x]), default=ReportStatus.PENDING, nullable=False)
    
    title = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    economic_snapshot = Column(Text, nullable=True)
    
    confidence_score = Column(Integer, nullable=True)
    
    generation_time_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    
    error_type = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="generated_reports")
    opportunity = relationship("Opportunity", back_populates="generated_reports")

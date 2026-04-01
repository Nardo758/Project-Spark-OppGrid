from sqlalchemy import Column, Integer, String, Float, Text, Date, DateTime, Boolean, BigInteger
from sqlalchemy.dialects.postgresql import JSON
from app.db.database import Base


class HubOpportunityEnriched(Base):
    __tablename__ = 'hub_opportunities_enriched'

    opportunity_id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100))
    source_platform = Column(String(100))

    city = Column(String(100), index=True)
    state = Column(String(50), index=True)
    region = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)

    ai_opportunity_score = Column(Float)
    market_tier = Column(String(50))
    trend_momentum = Column(Float)
    competition_density = Column(String(50))
    difficulty_score = Column(Integer)
    market_readiness_score = Column(Integer)

    estimated_market_size_usd = Column(BigInteger)
    target_market_size_usd = Column(BigInteger)
    tam_saw_som = Column(JSON)
    growth_rate_percent = Column(Float)
    time_to_profitability_months = Column(Integer)

    direct_competitors_count = Column(Integer)
    indirect_competitors_count = Column(Integer)
    key_competitors = Column(JSON)
    competitive_advantages = Column(JSON)
    barriers_to_entry = Column(JSON)

    estimated_startup_cost_usd = Column(BigInteger)
    estimated_monthly_costs_usd = Column(BigInteger)
    estimated_monthly_revenue_usd = Column(BigInteger)
    roi_estimate_percent = Column(Float)
    break_even_months = Column(Integer)

    technical_difficulty = Column(String(50))
    regulatory_risk = Column(String(50))
    market_risk = Column(String(50))
    key_risks = Column(JSON)
    critical_success_factors = Column(JSON)

    project_overview = Column(JSON)
    technical_feasibility = Column(JSON)
    market_feasibility = Column(JSON)
    financial_feasibility = Column(JSON)
    operational_feasibility = Column(JSON)
    legal_regulatory = Column(JSON)

    case_study_example = Column(JSON)
    success_patterns = Column(JSON)
    failure_patterns = Column(JSON)
    expert_perspective = Column(String(1000))

    aggregated_at = Column(DateTime(timezone=True), nullable=False)
    last_updated_at = Column(DateTime(timezone=True), nullable=False)
    data_freshness = Column(String(50))
    confidence_score = Column(Float)


class HubMarketByGeography(Base):
    __tablename__ = 'hub_markets_by_geography'

    market_id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(50), nullable=False, index=True)
    country = Column(String(50), nullable=False, server_default='USA')

    total_opportunities = Column(Integer)
    categories = Column(JSON)
    avg_opportunity_score = Column(Float)
    hot_categories = Column(JSON)

    total_businesses = Column(Integer)
    active_businesses = Column(Integer)
    avg_business_rating = Column(Float)
    business_categories = Column(JSON)
    competitor_analysis = Column(JSON)

    median_startup_cost_usd = Column(BigInteger)
    avg_monthly_revenue_usd = Column(BigInteger)
    median_roi_percent = Column(Float)
    cost_of_living_index = Column(Float)
    commercial_rent_sqft_month = Column(Float)

    population = Column(Integer)
    population_growth_percent = Column(Float)
    median_age = Column(Integer)
    median_household_income = Column(Integer)
    education_level_percent = Column(JSON)
    employment_rate_percent = Column(Float)
    industry_breakdown = Column(JSON)

    growth_trajectory = Column(String(50))
    emerging_trends = Column(JSON)
    seasonal_patterns = Column(JSON)

    new_opportunities_30d = Column(Integer)
    new_opportunities_90d = Column(Integer)
    monthly_opportunity_velocity = Column(Float)

    search_interest = Column(Float)
    social_mentions = Column(Integer)
    news_mentions = Column(Integer)

    aggregated_at = Column(DateTime(timezone=True), nullable=False)
    last_updated_at = Column(DateTime(timezone=True), nullable=False)


class HubIndustryInsight(Base):
    __tablename__ = 'hub_industries_insights'

    industry_id = Column(Integer, primary_key=True, autoincrement=True)
    industry_name = Column(String(200), nullable=False, unique=True, index=True)
    industry_code = Column(String(10), index=True)
    parent_industry = Column(String(200))

    global_market_size_usd = Column(BigInteger)
    usa_market_size_usd = Column(BigInteger)
    market_growth_rate_percent = Column(Float)
    market_maturity = Column(String(50))

    growth_drivers = Column(JSON)
    headwinds = Column(JSON)
    emerging_trends = Column(JSON)

    market_concentration = Column(String(50))
    typical_competitors_count = Column(Integer)
    barrier_to_entry = Column(String(50))
    switching_costs = Column(String(50))

    avg_startup_cost_usd = Column(BigInteger)
    median_year_1_revenue_usd = Column(BigInteger)
    median_gross_margin_percent = Column(Float)
    median_roi_percent = Column(Float)
    time_to_profitability_months = Column(Integer)

    critical_success_factors = Column(JSON)
    common_pitfalls = Column(JSON)
    skill_requirements = Column(JSON)

    regulatory_complexity = Column(String(50))
    required_licenses = Column(JSON)
    compliance_requirements = Column(JSON)

    top_players = Column(JSON)
    disruption_threats = Column(JSON)
    opportunities = Column(JSON)

    avg_employee_salary_usd = Column(Integer)
    skill_shortage_areas = Column(JSON)

    typical_customer_profile = Column(JSON)
    customer_acquisition_cost_usd = Column(Integer)
    customer_lifetime_value_usd = Column(Integer)
    average_contract_value_usd = Column(Integer)

    data_sources = Column(JSON)
    last_update = Column(DateTime(timezone=True), nullable=False)
    confidence_score = Column(Float)


class HubMarketSignal(Base):
    __tablename__ = 'hub_market_signals'

    signal_id = Column(Integer, primary_key=True, autoincrement=True)
    signal_type = Column(String(50), nullable=False, index=True)
    signal_name = Column(String(200), nullable=False, index=True)
    category = Column(String(100), index=True)

    signal_date = Column(Date, nullable=False, index=True)
    signal_strength = Column(Float)
    trend_direction = Column(String(50))
    momentum = Column(Float)

    applies_globally = Column(Boolean)
    primary_regions = Column(JSON)

    industries_affected = Column(JSON)
    opportunities_enabled = Column(JSON)
    opportunities_threatened = Column(JSON)

    data_source = Column(String(100))
    confidence_level = Column(String(50))
    supporting_evidence = Column(JSON)

    interpretation = Column(Text)
    strategic_implications = Column(Text)

    discovered_at = Column(DateTime(timezone=True), nullable=False)
    projected_duration_months = Column(Integer)


class HubValidationInsight(Base):
    __tablename__ = 'hub_validation_insights'

    validation_id = Column(Integer, primary_key=True, autoincrement=True)
    idea_hash = Column(String(64), index=True)
    industry = Column(String(100), nullable=False, index=True)
    business_model = Column(String(100))

    online_viability_score = Column(Integer)
    physical_viability_score = Column(Integer)
    overall_score = Column(Integer)

    market_fit_assessment = Column(JSON)
    competitive_positioning = Column(JSON)
    revenue_potential = Column(JSON)
    operational_feasibility = Column(JSON)

    go_no_go_recommendation = Column(String(50))
    recommendation_confidence = Column(Float)
    key_advantages = Column(JSON)
    key_risks = Column(JSON)

    similar_businesses = Column(JSON)

    improvement_opportunities = Column(JSON)
    resource_requirements = Column(JSON)

    cached_at = Column(DateTime(timezone=True), nullable=False)
    cache_validity_days = Column(Integer)


class HubUserCohort(Base):
    __tablename__ = 'hub_user_insights_cohorts'

    cohort_id = Column(Integer, primary_key=True, autoincrement=True)
    cohort_name = Column(String(100), nullable=False, unique=True)
    criteria = Column(JSON)
    user_count = Column(Integer)

    avg_reports_generated_per_month = Column(Float)
    preferred_report_types = Column(JSON)
    preferred_industries = Column(JSON)
    preferred_geographies = Column(JSON)

    avg_session_duration_minutes = Column(Float)
    monthly_active_user_percent = Column(Float)
    churn_rate_percent = Column(Float)

    free_to_paid_conversion_rate = Column(Float)
    average_customer_lifetime_value_usd = Column(Float)

    created_at = Column(DateTime(timezone=True), nullable=False)
    last_updated = Column(DateTime(timezone=True), nullable=False)


class HubFinancialSnapshot(Base):
    __tablename__ = 'hub_financial_snapshot'

    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)

    total_revenue_usd = Column(Float)
    mrr_recurring_revenue_usd = Column(Float)
    arr_recurring_revenue_usd = Column(Float)
    cac_customer_acquisition_cost_usd = Column(Float)
    ltv_customer_lifetime_value_usd = Column(Float)

    total_users = Column(Integer)
    active_users_30d = Column(Integer)
    paid_users = Column(Integer)
    free_users = Column(Integer)

    monthly_churn_rate_percent = Column(Float)
    mom_growth_percent = Column(Float)
    yoy_growth_percent = Column(Float)

    total_reports_generated = Column(Integer)
    reports_this_month = Column(Integer)
    avg_report_generation_time_ms = Column(Integer)

    api_uptime_percent = Column(Float)
    avg_api_response_time_ms = Column(Integer)
    error_rate_percent = Column(Float)

    ai_tokens_used = Column(Integer)
    ai_cost_usd = Column(Float)
    ai_cost_per_report_usd = Column(Float)

    snapshot_date = Column(Date, nullable=False, index=True)
    snapshot_period = Column(String(50))

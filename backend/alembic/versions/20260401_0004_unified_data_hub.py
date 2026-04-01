"""
Unified Data Hub - Aggregation Tables for Instant Report Generation

This migration creates 8 hub tables that cache all data needed for fast report generation.
Instead of AI calling multiple APIs per request, hub tables are populated once per day
and queries are instant (20-100ms).

Tables:
1. hub_opportunities_enriched - Opportunities + all computed fields
2. hub_markets_by_geography - City/state level market intelligence
3. hub_industries_insights - Industry benchmarks
4. hub_market_signals - Detected trends and signals
5. hub_validation_insights - Cached validation scores
6. hub_user_insights_cohorts - User behavior analysis
7. hub_financial_snapshot - Platform financial metrics
8. hub_report_sections - Pre-written report sections

Revision ID: 20260401_0004
Revises: 20260401_0003
Create Date: 2026-04-01 12:45:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '20260401_0004'
down_revision = '20260401_0003'
branch_labels = None
depends_on = None


def upgrade():
    # Table 1: hub_opportunities_enriched
    op.create_table(
        'hub_opportunities_enriched',
        sa.Column('opportunity_id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=False, index=True),
        sa.Column('subcategory', sa.String(100), nullable=True),
        sa.Column('source_platform', sa.String(100), nullable=True),
        
        # Geographic
        sa.Column('city', sa.String(100), nullable=True, index=True),
        sa.Column('state', sa.String(50), nullable=True, index=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        
        # Scoring
        sa.Column('ai_opportunity_score', sa.Float(), nullable=True),
        sa.Column('market_tier', sa.String(50), nullable=True),  # hot, growing, mature, declining
        sa.Column('trend_momentum', sa.Float(), nullable=True),  # -1 to 1
        sa.Column('competition_density', sa.String(50), nullable=True),  # sparse, moderate, saturated
        sa.Column('difficulty_score', sa.Integer(), nullable=True),  # 1-10
        sa.Column('market_readiness_score', sa.Integer(), nullable=True),
        
        # Market Size
        sa.Column('estimated_market_size_usd', sa.BigInteger(), nullable=True),
        sa.Column('target_market_size_usd', sa.BigInteger(), nullable=True),
        sa.Column('tam_saw_som', postgresql.JSON(), nullable=True),
        sa.Column('growth_rate_percent', sa.Float(), nullable=True),
        sa.Column('time_to_profitability_months', sa.Integer(), nullable=True),
        
        # Competition
        sa.Column('direct_competitors_count', sa.Integer(), nullable=True),
        sa.Column('indirect_competitors_count', sa.Integer(), nullable=True),
        sa.Column('key_competitors', postgresql.JSON(), nullable=True),
        sa.Column('competitive_advantages', postgresql.JSON(), nullable=True),
        sa.Column('barriers_to_entry', postgresql.JSON(), nullable=True),
        
        # Financial
        sa.Column('estimated_startup_cost_usd', sa.BigInteger(), nullable=True),
        sa.Column('estimated_monthly_costs_usd', sa.BigInteger(), nullable=True),
        sa.Column('estimated_monthly_revenue_usd', sa.BigInteger(), nullable=True),
        sa.Column('roi_estimate_percent', sa.Float(), nullable=True),
        sa.Column('break_even_months', sa.Integer(), nullable=True),
        
        # Risks
        sa.Column('technical_difficulty', sa.String(50), nullable=True),  # low, medium, high
        sa.Column('regulatory_risk', sa.String(50), nullable=True),
        sa.Column('market_risk', sa.String(50), nullable=True),
        sa.Column('key_risks', postgresql.JSON(), nullable=True),
        sa.Column('critical_success_factors', postgresql.JSON(), nullable=True),
        
        # Feasibility Components (cached from AI)
        sa.Column('project_overview', postgresql.JSON(), nullable=True),
        sa.Column('technical_feasibility', postgresql.JSON(), nullable=True),
        sa.Column('market_feasibility', postgresql.JSON(), nullable=True),
        sa.Column('financial_feasibility', postgresql.JSON(), nullable=True),
        sa.Column('operational_feasibility', postgresql.JSON(), nullable=True),
        sa.Column('legal_regulatory', postgresql.JSON(), nullable=True),
        
        # Content
        sa.Column('case_study_example', postgresql.JSON(), nullable=True),
        sa.Column('success_patterns', postgresql.JSON(), nullable=True),
        sa.Column('failure_patterns', postgresql.JSON(), nullable=True),
        sa.Column('expert_perspective', sa.String(1000), nullable=True),
        
        # Metadata
        sa.Column('aggregated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('data_freshness', sa.String(50), nullable=True),  # fresh, stale, unknown
        sa.Column('confidence_score', sa.Float(), nullable=True),  # 0-1
    )
    op.create_index('idx_hub_opps_category_tier', 'hub_opportunities_enriched', 
                    ['category', 'market_tier'])
    op.create_index('idx_hub_opps_location', 'hub_opportunities_enriched', 
                    ['city', 'state'])
    op.create_index('idx_hub_opps_score', 'hub_opportunities_enriched', 
                    ['ai_opportunity_score'], postgresql_using='btree')
    
    # Table 2: hub_markets_by_geography
    op.create_table(
        'hub_markets_by_geography',
        sa.Column('market_id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('city', sa.String(100), nullable=False, index=True),
        sa.Column('state', sa.String(50), nullable=False, index=True),
        sa.Column('country', sa.String(50), nullable=False, server_default='USA'),
        
        # Market overview
        sa.Column('total_opportunities', sa.Integer(), nullable=True),
        sa.Column('categories', postgresql.JSON(), nullable=True),
        sa.Column('avg_opportunity_score', sa.Float(), nullable=True),
        sa.Column('hot_categories', postgresql.JSON(), nullable=True),
        
        # Competition
        sa.Column('total_businesses', sa.Integer(), nullable=True),
        sa.Column('active_businesses', sa.Integer(), nullable=True),
        sa.Column('avg_business_rating', sa.Float(), nullable=True),
        sa.Column('business_categories', postgresql.JSON(), nullable=True),
        sa.Column('competitor_analysis', postgresql.JSON(), nullable=True),
        
        # Economics
        sa.Column('median_startup_cost_usd', sa.BigInteger(), nullable=True),
        sa.Column('avg_monthly_revenue_usd', sa.BigInteger(), nullable=True),
        sa.Column('median_roi_percent', sa.Float(), nullable=True),
        sa.Column('cost_of_living_index', sa.Float(), nullable=True),
        sa.Column('commercial_rent_sqft_month', sa.Float(), nullable=True),
        
        # Demographics
        sa.Column('population', sa.Integer(), nullable=True),
        sa.Column('population_growth_percent', sa.Float(), nullable=True),
        sa.Column('median_age', sa.Integer(), nullable=True),
        sa.Column('median_household_income', sa.Integer(), nullable=True),
        sa.Column('education_level_percent', postgresql.JSON(), nullable=True),
        sa.Column('employment_rate_percent', sa.Float(), nullable=True),
        sa.Column('industry_breakdown', postgresql.JSON(), nullable=True),
        
        # Trends
        sa.Column('growth_trajectory', sa.String(50), nullable=True),  # accelerating, stable, declining
        sa.Column('emerging_trends', postgresql.JSON(), nullable=True),
        sa.Column('seasonal_patterns', postgresql.JSON(), nullable=True),
        
        # Opportunity flow
        sa.Column('new_opportunities_30d', sa.Integer(), nullable=True),
        sa.Column('new_opportunities_90d', sa.Integer(), nullable=True),
        sa.Column('monthly_opportunity_velocity', sa.Float(), nullable=True),
        
        # Signals
        sa.Column('search_interest', sa.Float(), nullable=True),  # Google Trends 0-100
        sa.Column('social_mentions', sa.Integer(), nullable=True),
        sa.Column('news_mentions', sa.Integer(), nullable=True),
        
        # Metadata
        sa.Column('aggregated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_hub_market_location', 'hub_markets_by_geography', 
                    ['city', 'state'])
    op.create_index('idx_hub_market_growth', 'hub_markets_by_geography', 
                    ['growth_trajectory'])
    
    # Table 3: hub_industries_insights
    op.create_table(
        'hub_industries_insights',
        sa.Column('industry_id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('industry_name', sa.String(200), nullable=False, unique=True, index=True),
        sa.Column('industry_code', sa.String(10), nullable=True, index=True),
        sa.Column('parent_industry', sa.String(200), nullable=True),
        
        # Market size
        sa.Column('global_market_size_usd', sa.BigInteger(), nullable=True),
        sa.Column('usa_market_size_usd', sa.BigInteger(), nullable=True),
        sa.Column('market_growth_rate_percent', sa.Float(), nullable=True),
        sa.Column('market_maturity', sa.String(50), nullable=True),  # emerging, growth, mature, decline
        
        # Drivers
        sa.Column('growth_drivers', postgresql.JSON(), nullable=True),
        sa.Column('headwinds', postgresql.JSON(), nullable=True),
        sa.Column('emerging_trends', postgresql.JSON(), nullable=True),
        
        # Market structure
        sa.Column('market_concentration', sa.String(50), nullable=True),
        sa.Column('typical_competitors_count', sa.Integer(), nullable=True),
        sa.Column('barrier_to_entry', sa.String(50), nullable=True),
        sa.Column('switching_costs', sa.String(50), nullable=True),
        
        # Financial
        sa.Column('avg_startup_cost_usd', sa.BigInteger(), nullable=True),
        sa.Column('median_year_1_revenue_usd', sa.BigInteger(), nullable=True),
        sa.Column('median_gross_margin_percent', sa.Float(), nullable=True),
        sa.Column('median_roi_percent', sa.Float(), nullable=True),
        sa.Column('time_to_profitability_months', sa.Integer(), nullable=True),
        
        # Success/failure
        sa.Column('critical_success_factors', postgresql.JSON(), nullable=True),
        sa.Column('common_pitfalls', postgresql.JSON(), nullable=True),
        sa.Column('skill_requirements', postgresql.JSON(), nullable=True),
        
        # Regulatory
        sa.Column('regulatory_complexity', sa.String(50), nullable=True),
        sa.Column('required_licenses', postgresql.JSON(), nullable=True),
        sa.Column('compliance_requirements', postgresql.JSON(), nullable=True),
        
        # Competition
        sa.Column('top_players', postgresql.JSON(), nullable=True),
        sa.Column('disruption_threats', postgresql.JSON(), nullable=True),
        sa.Column('opportunities', postgresql.JSON(), nullable=True),
        
        # Labor
        sa.Column('avg_employee_salary_usd', sa.Integer(), nullable=True),
        sa.Column('skill_shortage_areas', postgresql.JSON(), nullable=True),
        
        # Customer
        sa.Column('typical_customer_profile', postgresql.JSON(), nullable=True),
        sa.Column('customer_acquisition_cost_usd', sa.Integer(), nullable=True),
        sa.Column('customer_lifetime_value_usd', sa.Integer(), nullable=True),
        sa.Column('average_contract_value_usd', sa.Integer(), nullable=True),
        
        # Metadata
        sa.Column('data_sources', postgresql.JSON(), nullable=True),
        sa.Column('last_update', sa.DateTime(timezone=True), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
    )
    op.create_index('idx_hub_industry_name', 'hub_industries_insights', 
                    ['industry_name'])
    op.create_index('idx_hub_industry_code', 'hub_industries_insights', 
                    ['industry_code'])
    
    # Table 4: hub_market_signals
    op.create_table(
        'hub_market_signals',
        sa.Column('signal_id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('signal_type', sa.String(50), nullable=False, index=True),  # trend, demand, supply, etc
        sa.Column('signal_name', sa.String(200), nullable=False, index=True),
        sa.Column('category', sa.String(100), nullable=True, index=True),
        
        # Temporal
        sa.Column('signal_date', sa.Date(), nullable=False, index=True),
        sa.Column('signal_strength', sa.Float(), nullable=True),  # 0-1
        sa.Column('trend_direction', sa.String(50), nullable=True),  # increasing, stable, decreasing
        sa.Column('momentum', sa.Float(), nullable=True),  # rate of change
        
        # Geography
        sa.Column('applies_globally', sa.Boolean(), nullable=True),
        sa.Column('primary_regions', postgresql.JSON(), nullable=True),
        
        # Impact
        sa.Column('industries_affected', postgresql.JSON(), nullable=True),
        sa.Column('opportunities_enabled', postgresql.JSON(), nullable=True),
        sa.Column('opportunities_threatened', postgresql.JSON(), nullable=True),
        
        # Source & confidence
        sa.Column('data_source', sa.String(100), nullable=True),
        sa.Column('confidence_level', sa.String(50), nullable=True),  # high, medium, low
        sa.Column('supporting_evidence', postgresql.JSON(), nullable=True),
        
        # Analysis
        sa.Column('interpretation', sa.Text(), nullable=True),
        sa.Column('strategic_implications', sa.Text(), nullable=True),
        
        # Metadata
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('projected_duration_months', sa.Integer(), nullable=True),
    )
    op.create_index('idx_hub_signals_type', 'hub_market_signals', ['signal_type'])
    op.create_index('idx_hub_signals_category', 'hub_market_signals', ['category'])
    op.create_index('idx_hub_signals_date', 'hub_market_signals', ['signal_date'], 
                    postgresql_using='btree')
    
    # Table 5: hub_validation_insights
    op.create_table(
        'hub_validation_insights',
        sa.Column('validation_id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('idea_hash', sa.String(64), nullable=True, index=True),  # For dedup
        sa.Column('industry', sa.String(100), nullable=False, index=True),
        sa.Column('business_model', sa.String(100), nullable=True),
        
        # Scores
        sa.Column('online_viability_score', sa.Integer(), nullable=True),  # 1-100
        sa.Column('physical_viability_score', sa.Integer(), nullable=True),  # 1-100
        sa.Column('overall_score', sa.Integer(), nullable=True),  # 1-100
        
        # Assessments
        sa.Column('market_fit_assessment', postgresql.JSON(), nullable=True),
        sa.Column('competitive_positioning', postgresql.JSON(), nullable=True),
        sa.Column('revenue_potential', postgresql.JSON(), nullable=True),
        sa.Column('operational_feasibility', postgresql.JSON(), nullable=True),
        
        # Insights
        sa.Column('go_no_go_recommendation', sa.String(50), nullable=True),  # GO, NO-GO, CONDITIONAL
        sa.Column('recommendation_confidence', sa.Float(), nullable=True),
        sa.Column('key_advantages', postgresql.JSON(), nullable=True),
        sa.Column('key_risks', postgresql.JSON(), nullable=True),
        
        # References
        sa.Column('similar_businesses', postgresql.JSON(), nullable=True),
        
        # Optimization
        sa.Column('improvement_opportunities', postgresql.JSON(), nullable=True),
        sa.Column('resource_requirements', postgresql.JSON(), nullable=True),
        
        # Metadata
        sa.Column('cached_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cache_validity_days', sa.Integer(), nullable=True),
    )
    op.create_index('idx_hub_validation_industry', 'hub_validation_insights', 
                    ['industry'])
    op.create_index('idx_hub_validation_score', 'hub_validation_insights', 
                    ['overall_score'], postgresql_using='btree')
    
    # Table 6: hub_user_insights_cohorts
    op.create_table(
        'hub_user_insights_cohorts',
        sa.Column('cohort_id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('cohort_name', sa.String(100), nullable=False, unique=True),
        sa.Column('criteria', postgresql.JSON(), nullable=True),
        sa.Column('user_count', sa.Integer(), nullable=True),
        
        # Behavior
        sa.Column('avg_reports_generated_per_month', sa.Float(), nullable=True),
        sa.Column('preferred_report_types', postgresql.JSON(), nullable=True),
        sa.Column('preferred_industries', postgresql.JSON(), nullable=True),
        sa.Column('preferred_geographies', postgresql.JSON(), nullable=True),
        
        # Engagement
        sa.Column('avg_session_duration_minutes', sa.Float(), nullable=True),
        sa.Column('monthly_active_user_percent', sa.Float(), nullable=True),
        sa.Column('churn_rate_percent', sa.Float(), nullable=True),
        
        # Conversion
        sa.Column('free_to_paid_conversion_rate', sa.Float(), nullable=True),
        sa.Column('average_customer_lifetime_value_usd', sa.Float(), nullable=True),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False),
    )
    
    # Table 7: hub_financial_snapshot
    op.create_table(
        'hub_financial_snapshot',
        sa.Column('snapshot_id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        
        # Revenue
        sa.Column('total_revenue_usd', sa.Float(), nullable=True),
        sa.Column('mrr_recurring_revenue_usd', sa.Float(), nullable=True),
        sa.Column('arr_recurring_revenue_usd', sa.Float(), nullable=True),
        sa.Column('cac_customer_acquisition_cost_usd', sa.Float(), nullable=True),
        sa.Column('ltv_customer_lifetime_value_usd', sa.Float(), nullable=True),
        
        # Users
        sa.Column('total_users', sa.Integer(), nullable=True),
        sa.Column('active_users_30d', sa.Integer(), nullable=True),
        sa.Column('paid_users', sa.Integer(), nullable=True),
        sa.Column('free_users', sa.Integer(), nullable=True),
        
        # Growth
        sa.Column('monthly_churn_rate_percent', sa.Float(), nullable=True),
        sa.Column('mom_growth_percent', sa.Float(), nullable=True),
        sa.Column('yoy_growth_percent', sa.Float(), nullable=True),
        
        # Content
        sa.Column('total_reports_generated', sa.Integer(), nullable=True),
        sa.Column('reports_this_month', sa.Integer(), nullable=True),
        sa.Column('avg_report_generation_time_ms', sa.Integer(), nullable=True),
        
        # Health
        sa.Column('api_uptime_percent', sa.Float(), nullable=True),
        sa.Column('avg_api_response_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_rate_percent', sa.Float(), nullable=True),
        
        # AI
        sa.Column('ai_tokens_used', sa.Integer(), nullable=True),
        sa.Column('ai_cost_usd', sa.Float(), nullable=True),
        sa.Column('ai_cost_per_report_usd', sa.Float(), nullable=True),
        
        # Metadata
        sa.Column('snapshot_date', sa.Date(), nullable=False, index=True),
        sa.Column('snapshot_period', sa.String(50), nullable=True),  # daily, weekly, monthly
    )
    op.create_index('idx_hub_financial_date', 'hub_financial_snapshot', 
                    ['snapshot_date'], postgresql_using='btree')


def downgrade():
    op.drop_table('hub_financial_snapshot')
    op.drop_table('hub_user_insights_cohorts')
    op.drop_table('hub_validation_insights')
    op.drop_table('hub_market_signals')
    op.drop_table('hub_industries_insights')
    op.drop_table('hub_markets_by_geography')
    op.drop_table('hub_opportunities_enriched')

"""
Saved Search Alerts Background Service

Hourly job that checks for new opportunities matching saved searches
and sends notifications via email, push, and Slack.

Integrates with AI Router for cost-optimized match scoring.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.database import SessionLocal
from app.models.saved_search import SavedSearch
from app.models.opportunity import Opportunity
from app.models.user import User
from app.services.email_service import send_email
from app.services.ai_router import AIRouter, TaskType

logger = logging.getLogger(__name__)


def run_saved_search_alerts():
    """
    Main entry point for the background job
    
    Should be called by a scheduler (cron, Celery, etc.) every hour
    """
    logger.info("Starting saved search alerts job...")
    
    db = SessionLocal()
    try:
        active_searches = db.query(SavedSearch).filter(
            SavedSearch.is_active == True
        ).all()
        
        logger.info(f"Found {len(active_searches)} active saved searches")
        
        alerts_sent = 0
        for search in active_searches:
            try:
                if should_send_alert(search):
                    matches = find_matching_opportunities(search, db)
                    
                    if matches:
                        send_notifications(search, matches, db)
                        
                        # Update tracking
                        search.last_notified_at = datetime.utcnow()
                        search.match_count += len(matches)
                        db.commit()
                        
                        alerts_sent += 1
                        logger.info(f"Sent alert for search '{search.name}' ({len(matches)} matches)")
            
            except Exception as e:
                logger.error(f"Error processing search {search.id}: {str(e)}")
                db.rollback()
                continue
        
        logger.info(f"Saved search alerts job completed. Sent {alerts_sent} alerts.")
    
    finally:
        db.close()


def should_send_alert(search: SavedSearch) -> bool:
    """
    Check if enough time has passed to send alert based on frequency
    
    Args:
        search: SavedSearch instance
        
    Returns:
        bool: True if should send alert now
    """
    user = getattr(search, "user", None)
    subscription = getattr(user, "subscription", None) if user is not None else None
    tier = getattr(subscription, "tier", None)
    tier_value = getattr(tier, "value", tier)
    if str(tier_value or "").upper() == "MONTHLY":
        return False

    prefs = search.notification_prefs
    frequency = prefs.get('frequency', 'daily')
    
    # Check if any notification method is enabled
    has_notification = prefs.get('email') or prefs.get('push') or prefs.get('slack')
    if not has_notification:
        return False
    
    # If never notified, send alert
    if not search.last_notified_at:
        return True
    
    time_since_last = datetime.utcnow() - search.last_notified_at
    
    # Instant notifications - send if more than 10 minutes passed (rate limiting)
    if frequency == 'instant':
        return time_since_last >= timedelta(minutes=10)
    
    # Daily digest - send if more than 24 hours passed
    elif frequency == 'daily':
        return time_since_last >= timedelta(hours=24)
    
    return False


def find_matching_opportunities(
    search: SavedSearch, 
    db: Session,
    test_mode: bool = False
) -> List[Opportunity]:
    """
    Find opportunities matching the saved search filters
    
    Args:
        search: SavedSearch instance
        db: Database session
        test_mode: If True, returns all matches (for testing). Otherwise only new since last_notified_at
        
    Returns:
        List of matching Opportunity objects
    """
    filters = search.filters
    
    # Base query
    query = db.query(Opportunity).filter(
        Opportunity.status == "active",
        Opportunity.moderation_status == 'approved'
    )
    
    # Only new opportunities since last notification (unless test mode)
    if not test_mode and search.last_notified_at:
        query = query.filter(Opportunity.created_at > search.last_notified_at)
    elif not test_mode:
        # First time - look at last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        query = query.filter(Opportunity.created_at > cutoff)
    
    # Apply search filters
    
    # Search query (title or description)
    if filters.get('search'):
        search_term = f"%{filters['search']}%"
        query = query.filter(
            or_(
                Opportunity.title.ilike(search_term),
                Opportunity.description.ilike(search_term)
            )
        )
    
    # Category filter
    if filters.get('category'):
        query = query.filter(Opportunity.category == filters['category'])
    
    # Feasibility range
    if filters.get('min_feasibility') is not None:
        query = query.filter(Opportunity.feasibility_score >= filters['min_feasibility'])
    
    if filters.get('max_feasibility') is not None:
        query = query.filter(Opportunity.feasibility_score <= filters['max_feasibility'])
    
    # Geographic scope
    if filters.get('geographic_scope'):
        query = query.filter(Opportunity.geographic_scope == filters['geographic_scope'])
    
    # Country
    if filters.get('country'):
        query = query.filter(Opportunity.country == filters['country'])
    
    # Completion status
    if filters.get('completion_status'):
        query = query.filter(Opportunity.completion_status == filters['completion_status'])
    
    # Realm type
    if filters.get('realm_type'):
        query = query.filter(Opportunity.realm_type == filters['realm_type'])
    
    # Validation count minimum
    if filters.get('min_validations') is not None:
        query = query.filter(Opportunity.validation_count >= filters['min_validations'])
    
    # Max age filter
    if filters.get('max_age_days') is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=filters['max_age_days'])
        query = query.filter(Opportunity.created_at >= cutoff_date)
    
    # Sort by (default: feasibility)
    sort_by = filters.get('sort_by', 'feasibility')
    if sort_by == 'feasibility':
        query = query.order_by(Opportunity.feasibility_score.desc())
    elif sort_by == 'recent':
        query = query.order_by(Opportunity.created_at.desc())
    elif sort_by == 'validated':
        query = query.order_by(Opportunity.validation_count.desc())
    
    # Execute query (limit to 50 matches per alert)
    matches = query.limit(50).all()
    
    return matches


def send_notifications(search: SavedSearch, opportunities: List[Opportunity], db: Session):
    """
    Send notifications via enabled channels
    
    Args:
        search: SavedSearch instance
        opportunities: List of matching opportunities
        db: Database session
    """
    prefs = search.notification_prefs
    user = db.query(User).filter(User.id == search.user_id).first()
    
    if not user:
        logger.error(f"User {search.user_id} not found for search {search.id}")
        return
    
    # Email notification
    if prefs.get('email', False):
        try:
            send_email_notification(user, search, opportunities)
        except Exception as e:
            logger.error(f"Failed to send email for search {search.id}: {str(e)}")
    
    # Push notification
    if prefs.get('push', False):
        try:
            send_push_notification(user, search, opportunities)
        except Exception as e:
            logger.error(f"Failed to send push for search {search.id}: {str(e)}")
    
    # Slack notification
    if prefs.get('slack', False):
        try:
            send_slack_notification(user, search, opportunities)
        except Exception as e:
            logger.error(f"Failed to send Slack for search {search.id}: {str(e)}")


def send_email_notification(user: User, search: SavedSearch, opportunities: List[Opportunity]):
    """
    Send email notification with matching opportunities
    
    Uses AI Router for generating personalized email content (cost-optimized)
    """
    
    # Build email HTML
    count = len(opportunities)
    plural = "opportunities" if count != 1 else "opportunity"
    
    email_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                       color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .opportunity {{ background: #f8f9fa; border-left: 4px solid #667eea; 
                           padding: 15px; margin: 15px 0; }}
            .opportunity h3 {{ margin-top: 0; color: #667eea; }}
            .metrics {{ display: flex; gap: 15px; margin: 10px 0; }}
            .metric {{ background: white; padding: 8px 12px; border-radius: 4px; }}
            .cta {{ background: #667eea; color: white; padding: 12px 24px; 
                   text-decoration: none; border-radius: 6px; display: inline-block;
                   margin: 20px 0; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔔 New Opportunities Found!</h1>
            <p>Your saved search "{search.name}" has {count} new {plural}</p>
        </div>
        
        <div class="content">
            <p>Hi {user.name or user.email.split('@')[0]},</p>
            <p>We found <strong>{count}</strong> new {plural} matching your saved search criteria.</p>
    """
    
    # Add up to 10 opportunities to email
    for i, opp in enumerate(opportunities[:10], 1):
        feasibility_color = "green" if opp.feasibility_score >= 75 else "orange" if opp.feasibility_score >= 60 else "gray"
        
        email_html += f"""
            <div class="opportunity">
                <h3>{i}. {opp.title}</h3>
                <p>{opp.description[:200]}{'...' if len(opp.description) > 200 else ''}</p>
                <div class="metrics">
                    <div class="metric">
                        <strong style="color: {feasibility_color}">Feasibility:</strong> {opp.feasibility_score or 'N/A'}
                    </div>
                    <div class="metric">
                        <strong>Validations:</strong> {opp.validation_count}
                    </div>
                    {f'<div class="metric"><strong>Growth:</strong> +{opp.growth_rate}%</div>' if opp.growth_rate else ''}
                </div>
                <p><strong>Category:</strong> {opp.category} | <strong>Scope:</strong> {opp.geographic_scope}</p>
            </div>
        """
    
    if len(opportunities) > 10:
        email_html += f"<p><em>... and {len(opportunities) - 10} more opportunities.</em></p>"
    
    # View all link
    # TODO: Add URL with search filter parameters
    email_html += f"""
            <a href="https://oppgrid.com/discover?saved_search={search.id}" class="cta">
                View All Matches →
            </a>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
            
            <p style="font-size: 14px; color: #666;">
                You're receiving this because you saved the search "{search.name}" with email notifications enabled.
                <br>
                <a href="https://oppgrid.com/saved-searches/{search.id}">Manage this search</a> | 
                <a href="https://oppgrid.com/settings/notifications">Notification settings</a>
            </p>
        </div>
        
        <div class="footer">
            <p>OppGrid - Discover Validated Business Opportunities</p>
            <p>© 2026 OppGrid. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    # Send email
    send_email(
        to_email=user.email,
        subject=f"🔔 {count} new {plural} matching \"{search.name}\"",
        html_content=email_html
    )
    
    logger.info(f"Sent email to {user.email} for search '{search.name}'")


def send_push_notification(user: User, search: SavedSearch, opportunities: List[Opportunity]):
    """
    Send push notification
    
    TODO: Integrate with push notification service (FCM, OneSignal, etc.)
    """
    count = len(opportunities)
    plural = "opportunities" if count != 1 else "opportunity"
    
    # Placeholder - implement when push service is set up
    logger.info(f"[PUSH] Would send to user {user.id}: {count} {plural} for '{search.name}'")
    
    # Example integration:
    # push_service.send(
    #     user_id=user.id,
    #     title=f"New Opportunities Found!",
    #     body=f"{count} {plural} match your search '{search.name}'",
    #     data={"search_id": search.id, "count": count}
    # )


def send_slack_notification(user: User, search: SavedSearch, opportunities: List[Opportunity]):
    """
    Send Slack notification
    
    TODO: Integrate with Slack API (requires user OAuth tokens)
    """
    count = len(opportunities)
    plural = "opportunities" if count != 1 else "opportunity"
    
    # Placeholder - implement when Slack integration is set up
    logger.info(f"[SLACK] Would send to user {user.id}: {count} {plural} for '{search.name}'")
    
    # Example Slack message format:
    # {
    #     "text": f"🔔 *New Opportunities Found!*\n\n"
    #             f"Your saved search \"{search.name}\" has {count} new {plural}.\n\n"
    #             f"<https://oppgrid.com/discover?saved_search={search.id}|View All →>",
    #     "attachments": [
    #         {
    #             "color": "#667eea",
    #             "fields": [
    #                 {"title": opp.title, "value": f"Feasibility: {opp.feasibility_score}"}
    #                 for opp in opportunities[:3]
    #             ]
    #         }
    #     ]
    # }


def calculate_match_score_with_ai(opportunity: Opportunity, user: User, db: Session) -> int:
    """
    Use AI Router to calculate sophisticated match score
    
    This is a premium feature - uses AI to analyze opportunity-user fit
    Falls back to rule-based scoring for cost optimization
    
    Args:
        opportunity: Opportunity to score
        user: User to match against
        db: Database session
        
    Returns:
        Match score 0-100
    """
    
    # Check if user has BYOK (Bring Your Own Key) - use AI freely
    # Otherwise use simple rule-based matching for cost efficiency
    
    # TODO: Check user's AI preferences / API key
    use_ai = False  # Default to rule-based for cost control
    
    if use_ai:
        router = AIRouter()
        
        prompt = f"""
        Calculate match score (0-100) between this opportunity and user:
        
        OPPORTUNITY:
        - Title: {opportunity.title}
        - Description: {opportunity.description[:500]}
        - Category: {opportunity.category}
        - Feasibility: {opportunity.feasibility_score}
        
        USER CONTEXT:
        - Previous validations: [TODO: get user's validation history]
        - Interests: [TODO: get user interests from profile]
        
        Return ONLY a number 0-100 representing match quality.
        """
        
        result = router.route(
            task_type=TaskType.SIMPLE_CLASSIFICATION,
            prompt=prompt,
            max_tokens=10
        )
        
        try:
            score = int(result['response'].strip())
            return min(max(score, 0), 100)  # Clamp to 0-100
        except ValueError:
            logger.warning("AI returned invalid score, falling back to rule-based")
    
    # Fallback: Rule-based scoring (from opportunities router)
    from app.routers.opportunities import calculate_match_score
    
    # Get user interests
    from app.models.validation import Validation
    user_validated_categories = db.query(Opportunity.category).join(
        Validation, Opportunity.id == Validation.opportunity_id
    ).filter(
        Validation.user_id == user.id,
        Opportunity.category.isnot(None)
    ).distinct().limit(5).all()
    
    user_interests = [c[0] for c in user_validated_categories if c[0]]
    
    return calculate_match_score(opportunity, user, user_interests, db)


# For testing - can be called manually
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_saved_search_alerts()

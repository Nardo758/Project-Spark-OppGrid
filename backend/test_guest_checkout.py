"""
Test guest checkout & payment gating logic.
Run: python -m pytest backend/test_guest_checkout.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

# Mock the database models
class MockSubscription:
    def __init__(self, tier):
        self.tier = tier
        self.current_period_end = datetime.utcnow() + timedelta(days=30)

class MockUser:
    def __init__(self, user_id, tier=None):
        self.id = user_id
        self.subscription = MockSubscription(tier) if tier else None

# Import service (we'll mock the DB)
from app.services.report_quota_service import ReportQuotaService


class TestGuestCheckout:
    """Test guest checkout flow (no account required)."""
    
    def setup_method(self):
        """Create mock database."""
        self.db = MagicMock(spec=Session)
        self.service = ReportQuotaService(self.db)
    
    def test_guest_can_generate_report(self):
        """Guest (no user) should be able to generate report."""
        can_gen, msg, price = self.service.check_access(None, "layer_1")
        
        assert can_gen == True, "Guest should be able to generate"
        assert price == 1500, "Guest should pay full price ($15)"
        assert "$15" in msg, f"Message should mention price: {msg}"
        assert "Generate report" in msg
    
    def test_guest_layer2_pricing(self):
        """Guest Layer 2 should cost $25."""
        can_gen, msg, price = self.service.check_access(None, "layer_2")
        
        assert can_gen == True
        assert price == 2500, "Layer 2 should be $25"
        assert "$25" in msg
    
    def test_guest_layer3_pricing(self):
        """Guest Layer 3 should cost $35."""
        can_gen, msg, price = self.service.check_access(None, "layer_3")
        
        assert can_gen == True
        assert price == 3500, "Layer 3 should be $35"
        assert "$35" in msg
    
    def test_free_member_full_price(self):
        """Free member should pay full price (no allocation)."""
        user = MockUser(user_id=1, tier="free")
        can_gen, msg, price = self.service.check_access(user, "layer_1")
        
        assert can_gen == True
        assert price == 1500, "Free member pays full price"
        assert "$15" in msg
        assert "Generate report" in msg
    
    def test_pro_member_with_quota(self):
        """Pro member with quota should generate free."""
        user = MockUser(user_id=2, tier="pro")
        
        # Mock quota check
        mock_quota = Mock()
        mock_quota.remaining.return_value = 4
        mock_quota.can_generate_free.return_value = True
        
        self.db.query.return_value.filter.return_value.first.return_value = mock_quota
        self.db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_quota
        
        can_gen, msg, price = self.service.check_access(user, "layer_1")
        
        assert can_gen == True
        assert price == 0, "Pro member with quota pays $0"
        assert "free" in msg.lower()
        assert "4" in msg
    
    def test_pro_member_quota_exhausted(self):
        """Pro member with exhausted quota should pay overage."""
        user = MockUser(user_id=3, tier="pro")
        
        # Mock exhausted quota
        mock_quota = Mock()
        mock_quota.remaining.return_value = 0
        mock_quota.can_generate_free.return_value = False
        
        self.db.query.return_value.filter.return_value.first.return_value = mock_quota
        self.db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_quota
        
        can_gen, msg, price = self.service.check_access(user, "layer_1")
        
        assert can_gen == True
        assert price == 1000, "Pro overage for Layer 1 is $10"
        assert "$10" in msg
        assert "quota exhausted" in msg.lower()
    
    def test_business_member_high_allocation(self):
        """Business member should have 15 Layer 1 allocations."""
        user = MockUser(user_id=4, tier="business")
        
        # Mock quota with high allocation
        mock_quota = Mock()
        mock_quota.remaining.return_value = 12
        mock_quota.can_generate_free.return_value = True
        
        self.db.query.return_value.filter.return_value.first.return_value = mock_quota
        self.db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_quota
        
        can_gen, msg, price = self.service.check_access(user, "layer_1")
        
        assert can_gen == True
        assert price == 0, "Business member with quota pays $0"
        assert "12" in msg
        assert "free" in msg.lower()
    
    def test_business_overage_pricing(self):
        """Business member overage should be cheaper than Pro."""
        user = MockUser(user_id=5, tier="business")
        
        # Mock exhausted quota
        mock_quota = Mock()
        mock_quota.remaining.return_value = 0
        mock_quota.can_generate_free.return_value = False
        
        self.db.query.return_value.filter.return_value.first.return_value = mock_quota
        self.db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_quota
        
        can_gen, msg, price = self.service.check_access(user, "layer_1")
        
        assert can_gen == True
        assert price == 800, "Business overage for Layer 1 is $8 (vs $10 for Pro)"
        assert "$8" in msg


class TestPricingComparison:
    """Compare pricing across all tiers."""
    
    def test_pricing_matrix(self):
        """Verify pricing matrix for all combinations."""
        db = MagicMock(spec=Session)
        service = ReportQuotaService(db)
        
        # Expected pricing
        expected = {
            "guest": {
                "layer_1": 1500,
                "layer_2": 2500,
                "layer_3": 3500,
            },
            "free": {
                "layer_1": 1500,
                "layer_2": 2500,
                "layer_3": 3500,
            },
            "pro_overage": {
                "layer_1": 1000,
                "layer_2": 1800,
                "layer_3": 2500,
            },
            "business_overage": {
                "layer_1": 800,
                "layer_2": 1500,
                "layer_3": 2000,
            },
        }
        
        # Verify base prices (guests)
        assert service.BASE_PRICES["layer_1"] == expected["guest"]["layer_1"]
        assert service.BASE_PRICES["layer_2"] == expected["guest"]["layer_2"]
        assert service.BASE_PRICES["layer_3"] == expected["guest"]["layer_3"]
        
        # Verify overage prices
        assert service.OVERAGE_PRICES["pro"]["layer_1"] == expected["pro_overage"]["layer_1"]
        assert service.OVERAGE_PRICES["pro"]["layer_2"] == expected["pro_overage"]["layer_2"]
        assert service.OVERAGE_PRICES["business"]["layer_1"] == expected["business_overage"]["layer_1"]
        assert service.OVERAGE_PRICES["business"]["layer_3"] == expected["business_overage"]["layer_3"]
    
    def test_allocation_matrix(self):
        """Verify allocation matrix for all tiers."""
        db = MagicMock(spec=Session)
        service = ReportQuotaService(db)
        
        expected = {
            "free": {"layer_1": 0, "layer_2": 0, "layer_3": 0},
            "pro": {"layer_1": 5, "layer_2": 2, "layer_3": 0},
            "business": {"layer_1": 15, "layer_2": 8, "layer_3": 3},
            "enterprise": {"layer_1": 50, "layer_2": 25, "layer_3": 10},
        }
        
        for tier, allocs in expected.items():
            for tier_name, count in allocs.items():
                assert service.TIER_ALLOCATIONS[tier][tier_name] == count, \
                    f"{tier} {tier_name} allocation mismatch"


class TestQuotaDecrement:
    """Test quota tracking and decrement."""
    
    def test_can_decrement_quota(self):
        """Should decrement quota when report generated."""
        db = MagicMock(spec=Session)
        service = ReportQuotaService(db)
        
        # Mock quota object
        mock_quota = Mock()
        mock_quota.is_exhausted.return_value = False
        mock_quota.decrement.return_value = True
        
        db.query.return_value.filter.return_value.first.return_value = mock_quota
        db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_quota
        
        user = MockUser(user_id=10, tier="pro")
        result = service.decrement_quota(user, "layer_1")
        
        assert result == True
        assert mock_quota.decrement.called
    
    def test_cannot_decrement_exhausted_quota(self):
        """Should not decrement if quota exhausted."""
        db = MagicMock(spec=Session)
        service = ReportQuotaService(db)
        
        # Mock exhausted quota
        mock_quota = Mock()
        mock_quota.is_exhausted.return_value = True
        mock_quota.decrement.return_value = False
        
        db.query.return_value.filter.return_value.first.return_value = mock_quota
        db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_quota
        
        user = MockUser(user_id=11, tier="pro")
        result = service.decrement_quota(user, "layer_1")
        
        assert result == False


class TestPurchaseLogging:
    """Test purchase log tracking."""
    
    def test_log_guest_purchase(self):
        """Log purchase for guest (no user account)."""
        db = MagicMock(spec=Session)
        service = ReportQuotaService(db)
        
        # Mock the database add/commit
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        
        # Log guest purchase
        log = service.log_purchase(
            report_tier="layer_1",
            payment_type="stripe",
            amount_cents=1500,
            stripe_charge_id="ch_123456",
            guest_email="john@example.com",
        )
        
        # Verify it was added to DB
        assert db.add.called
        assert db.commit.called
    
    def test_log_member_purchase(self):
        """Log purchase for registered member."""
        db = MagicMock(spec=Session)
        service = ReportQuotaService(db)
        
        user = MockUser(user_id=20, tier="pro")
        
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        
        log = service.log_purchase(
            report_tier="layer_1",
            payment_type="stripe",
            amount_cents=1000,  # Overage
            stripe_charge_id="ch_789",
            user=user,
        )
        
        assert db.add.called
        assert db.commit.called


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])

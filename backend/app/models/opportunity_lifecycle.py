from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from app.db.database import Base


class LifecycleState(str, Enum):
    """8 opportunity lifecycle states"""
    DISCOVERED = "discovered"      # Initial browse/preview
    SAVED = "saved"               # Added to collections
    ANALYZING = "analyzing"        # Market research, AI analysis
    PLANNING = "planning"          # Business plan, strategy
    EXECUTING = "executing"        # Active development, team
    LAUNCHED = "launched"          # Live, customers
    PAUSED = "paused"             # Temporarily paused
    ARCHIVED = "archived"          # Complete, lessons learned


class OpportunityLifecycle(Base):
    __tablename__ = 'opportunity_lifecycle'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'), nullable=False)
    current_state = Column(String(50), default=LifecycleState.DISCOVERED.value, nullable=False)
    
    # Timestamp tracking for each state
    discovered_at = Column(DateTime, default=datetime.utcnow)
    saved_at = Column(DateTime)
    analyzing_at = Column(DateTime)
    planning_at = Column(DateTime)
    executing_at = Column(DateTime)
    launched_at = Column(DateTime)
    paused_at = Column(DateTime)
    archived_at = Column(DateTime)
    
    # Progress & metadata
    progress_percent = Column(Integer, default=0)  # 0-100%
    notes = Column(Text)  # User notes about this opportunity's journey
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='opportunity_lifecycles')
    opportunity = relationship('Opportunity', back_populates='lifecycle')
    transitions = relationship('LifecycleStateTransition', back_populates='lifecycle', cascade='all, delete-orphan')
    milestones = relationship('LifecycleMilestone', back_populates='lifecycle', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'opportunity_id': self.opportunity_id,
            'current_state': self.current_state,
            'progress_percent': self.progress_percent,
            'discovered_at': self.discovered_at.isoformat() if self.discovered_at else None,
            'saved_at': self.saved_at.isoformat() if self.saved_at else None,
            'analyzing_at': self.analyzing_at.isoformat() if self.analyzing_at else None,
            'planning_at': self.planning_at.isoformat() if self.planning_at else None,
            'executing_at': self.executing_at.isoformat() if self.executing_at else None,
            'launched_at': self.launched_at.isoformat() if self.launched_at else None,
            'paused_at': self.paused_at.isoformat() if self.paused_at else None,
            'archived_at': self.archived_at.isoformat() if self.archived_at else None,
            'notes': self.notes,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def can_transition_to(self, target_state: str) -> bool:
        """Check if transition from current state to target is valid"""
        current = self.current_state
        
        # Define valid transitions (state machine)
        valid_transitions = {
            LifecycleState.DISCOVERED.value: [
                LifecycleState.SAVED.value,
                LifecycleState.ARCHIVED.value,
            ],
            LifecycleState.SAVED.value: [
                LifecycleState.ANALYZING.value,
                LifecycleState.ARCHIVED.value,
                LifecycleState.DISCOVERED.value,  # Can go back
            ],
            LifecycleState.ANALYZING.value: [
                LifecycleState.PLANNING.value,
                LifecycleState.SAVED.value,  # Go back
                LifecycleState.PAUSED.value,
            ],
            LifecycleState.PLANNING.value: [
                LifecycleState.EXECUTING.value,
                LifecycleState.ANALYZING.value,  # Go back
                LifecycleState.PAUSED.value,
            ],
            LifecycleState.EXECUTING.value: [
                LifecycleState.LAUNCHED.value,
                LifecycleState.PLANNING.value,  # Go back
                LifecycleState.PAUSED.value,
            ],
            LifecycleState.LAUNCHED.value: [
                LifecycleState.PAUSED.value,
                LifecycleState.ARCHIVED.value,
            ],
            LifecycleState.PAUSED.value: [
                LifecycleState.ANALYZING.value,  # Resume at analysis
                LifecycleState.EXECUTING.value,  # Resume at execution
                LifecycleState.ARCHIVED.value,
            ],
            LifecycleState.ARCHIVED.value: [
                LifecycleState.SAVED.value,  # Can restore
            ],
        }
        
        return target_state in valid_transitions.get(current, [])


class LifecycleStateTransition(Base):
    __tablename__ = 'lifecycle_state_transitions'

    id = Column(Integer, primary_key=True)
    lifecycle_id = Column(Integer, ForeignKey('opportunity_lifecycle.id'), nullable=False)
    from_state = Column(String(50), nullable=False)
    to_state = Column(String(50), nullable=False)
    reason = Column(Text)  # Why the transition happened
    transitioned_at = Column(DateTime, default=datetime.utcnow)

    lifecycle = relationship('OpportunityLifecycle', back_populates='transitions')

    def to_dict(self):
        return {
            'id': self.id,
            'lifecycle_id': self.lifecycle_id,
            'from_state': self.from_state,
            'to_state': self.to_state,
            'reason': self.reason,
            'transitioned_at': self.transitioned_at.isoformat() if self.transitioned_at else None,
        }


class LifecycleMilestone(Base):
    __tablename__ = 'lifecycle_milestones'

    id = Column(Integer, primary_key=True)
    lifecycle_id = Column(Integer, ForeignKey('opportunity_lifecycle.id'), nullable=False)
    state = Column(String(50), nullable=False)  # Which state this milestone belongs to
    title = Column(String(255), nullable=False)
    description = Column(Text)
    is_completed = Column(Boolean, default=False)
    order = Column(Integer, default=0)  # Display order
    completed_at = Column(DateTime)

    lifecycle = relationship('OpportunityLifecycle', back_populates='milestones')

    def to_dict(self):
        return {
            'id': self.id,
            'lifecycle_id': self.lifecycle_id,
            'state': self.state,
            'title': self.title,
            'description': self.description,
            'is_completed': self.is_completed,
            'order': self.order,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

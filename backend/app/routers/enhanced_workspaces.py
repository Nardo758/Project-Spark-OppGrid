# 🚀 ENHANCED WORKSPACE API ROUTER
# Production-ready API endpoints for OppGrid enhanced workspace

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from app.db.database import get_db
from app.models.enhanced_workspace import (
    EnhancedUserWorkspace, EnhancedWorkflowStage, EnhancedWorkflowTask,
    EnhancedResearchArtifact, CustomWorkflow, WorkflowType, WorkflowStatus,
    ResearchArtifactType, ResearchArtifactStatus
)
from app.models.user import User
from app.models.opportunity import Opportunity
from app.core.dependencies import get_current_active_user
from app.services.enhanced_workspace_service import EnhancedWorkspaceService

router = APIRouter(prefix="/enhanced-workspaces", tags=["enhanced-workspaces"])

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_enhanced_workspace(
    opportunity_id: int,
    workflow_type: WorkflowType = WorkflowType.CUSTOM,
    custom_title: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create enhanced workspace with custom workflow"""
    
    # Verify opportunity exists
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    
    # Check if workspace already exists
    existing_workspace = db.query(EnhancedUserWorkspace).filter(
        EnhancedUserWorkspace.user_id == current_user.id,
        EnhancedUserWorkspace.opportunity_id == opportunity_id
    ).first()
    
    if existing_workspace:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enhanced workspace already exists for this opportunity"
        )
    
    service = EnhancedWorkspaceService(db)
    workspace = service.create_enhanced_workspace(
        user_id=current_user.id,
        opportunity_id=opportunity_id,
        workflow_type=workflow_type,
        custom_title=custom_title
    )
    
    return {
        "id": workspace.id,
        "workflow_type": workspace.workflow_type,
        "status": workspace.status,
        "progress_percent": workspace.progress_percent,
        "stages_count": len(workspace.workflow_stages),
        "message": "Enhanced workspace created successfully"
    }

@router.get("/", response_model=List[dict])
def list_enhanced_workspaces(
    skip: int = 0,
    limit: int = 100,
    workflow_type: Optional[WorkflowType] = None,
    status: Optional[WorkflowStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List user's enhanced workspaces"""
    
    query = db.query(EnhancedUserWorkspace).filter(
        EnhancedUserWorkspace.user_id == current_user.id
    )
    
    if workflow_type:
        query = query.filter(EnhancedUserWorkspace.workflow_type == workflow_type)
    
    if status:
        query = query.filter(EnhancedUserWorkspace.status == status)
    
    workspaces = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": workspace.id,
            "custom_title": workspace.custom_title,
            "workflow_type": workspace.workflow_type,
            "status": workspace.status,
            "progress_percent": workspace.progress_percent,
            "validation_score": workspace.validation_score,
            "research_summary": workspace.research_summary,
            "opportunity_title": workspace.opportunity.title if workspace.opportunity else None,
            "created_at": workspace.created_at,
            "last_activity_at": workspace.last_activity_at
        } for workspace in workspaces
    ]

@router.get("/{workspace_id}", response_model=dict)
def get_enhanced_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get enhanced workspace with all details"""
    
    workspace = db.query(EnhancedUserWorkspace).options(
        joinedload(EnhancedUserWorkspace.opportunity),
        joinedload(EnhancedUserWorkspace.workflow_stages).joinedload(EnhancedWorkflowStage.tasks),
        joinedload(EnhancedUserWorkspace.research_artifacts),
        joinedload(EnhancedUserWorkspace.custom_workflows)
    ).filter(
        EnhancedUserWorkspace.id == workspace_id,
        EnhancedUserWorkspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return {
        "id": workspace.id,
        "custom_title": workspace.custom_title,
        "description": workspace.description,
        "workflow_type": workspace.workflow_type,
        "status": workspace.status,
        "progress_percent": workspace.progress_percent,
        "validation_score": workspace.validation_score,
        "research_summary": workspace.research_summary,
        "ai_recommendations": workspace.ai_recommendations,
        "opportunity": {
            "id": workspace.opportunity.id,
            "title": workspace.opportunity.title,
            "description": workspace.opportunity.description,
            "category": workspace.opportunity.category,
            "ai_opportunity_score": workspace.opportunity.ai_opportunity_score,
            "validation_count": workspace.opportunity.validation_count,
            "feasibility_score": workspace.opportunity.feasibility_score
        },
        "stages": [
            {
                "id": stage.id,
                "name": stage.name,
                "description": stage.description,
                "order_index": stage.order_index,
                "duration_weeks": stage.duration_weeks,
                "status": stage.status,
                "started_at": stage.started_at,
                "completed_at": stage.completed_at,
                "ai_recommendations": stage.ai_recommendations,
                "tasks": [
                    {
                        "id": task.id,
                        "name": task.name,
                        "description": task.description,
                        "is_completed": task.is_completed,
                        "priority": task.priority,
                        "due_date": task.due_date,
                        "completed_at": task.completed_at,
                        "sort_order": task.sort_order,
                        "ai_assistance_requested": task.ai_assistance_requested,
                        "ai_assistance_completed": task.ai_assistance_completed
                    } for task in stage.tasks
                ]
            } for stage in workspace.workflow_stages
        ],
        "research_artifacts": [
            {
                "id": artifact.id,
                "name": artifact.name,
                "artifact_type": artifact.artifact_type,
                "status": artifact.status,
                "content": artifact.content,
                "file_url": artifact.file_url,
                "metadata": artifact.artifact_metadata,
                "tags": artifact.tags,
                "ai_insights": artifact.ai_insights,
                "ai_summary": artifact.ai_summary,
                "ai_recommendations": artifact.ai_recommendations,
                "created_at": artifact.created_at,
                "updated_at": artifact.updated_at
            } for artifact in workspace.research_artifacts
        ],
        "created_at": workspace.created_at,
        "updated_at": workspace.updated_at,
        "last_activity_at": workspace.last_activity_at
    }

@router.put("/{workspace_id}", response_model=dict)
def update_enhanced_workspace(
    workspace_id: int,
    custom_title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[WorkflowStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update enhanced workspace details"""
    
    workspace = db.query(EnhancedUserWorkspace).filter(
        EnhancedUserWorkspace.id == workspace_id,
        EnhancedUserWorkspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    if custom_title is not None:
        workspace.custom_title = custom_title
    
    if description is not None:
        workspace.description = description
    
    if status is not None:
        workspace.status = status
        if status == WorkflowStatus.IN_PROGRESS and not workspace.started_at:
            workspace.started_at = datetime.utcnow()
        elif status == WorkflowStatus.COMPLETED and not workspace.completed_at:
            workspace.completed_at = datetime.utcnow()
    
    workspace.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "id": workspace.id,
        "custom_title": workspace.custom_title,
        "description": workspace.description,
        "status": workspace.status,
        "updated_at": workspace.updated_at,
        "message": "Workspace updated successfully"
    }

@router.post("/{workspace_id}/artifacts", response_model=dict)
def create_research_artifact(
    workspace_id: int,
    name: str,
    artifact_type: ResearchArtifactType,
    stage_id: Optional[int] = None,
    content: Optional[str] = None,
    file_url: Optional[str] = None,
    tags: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create research artifact with AI insights"""
    
    # Verify workspace ownership
    workspace = db.query(EnhancedUserWorkspace).filter(
        EnhancedUserWorkspace.id == workspace_id,
        EnhancedUserWorkspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Verify stage if provided
    if stage_id:
        stage = db.query(EnhancedWorkflowStage).filter(
            EnhancedWorkflowStage.id == stage_id,
            EnhancedWorkflowStage.workspace_id == workspace_id
        ).first()
        
        if not stage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stage not found in workspace"
            )
    
    service = EnhancedWorkspaceService(db)
    artifact = service.create_research_artifact(
        workspace_id=workspace_id,
        stage_id=stage_id,
        name=name,
        artifact_type=artifact_type,
        content=content,
        file_url=file_url,
        artifact_metadata={"tags": tags} if tags else None
    )
    
    # Update workspace last activity
    workspace.last_activity_at = datetime.utcnow()
    db.commit()
    
    return {
        "id": artifact.id,
        "name": artifact.name,
        "artifact_type": artifact.artifact_type,
        "status": artifact.status,
        "ai_insights": artifact.ai_insights,
        "ai_summary": artifact.ai_summary,
        "ai_recommendations": artifact.ai_recommendations,
        "created_at": artifact.created_at
    }

@router.get("/{workspace_id}/artifacts", response_model=List[dict])
def list_research_artifacts(
    workspace_id: int,
    artifact_type: Optional[ResearchArtifactType] = None,
    stage_id: Optional[int] = None,
    status: Optional[ResearchArtifactStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List research artifacts for workspace"""
    
    # Verify workspace ownership
    workspace = db.query(EnhancedUserWorkspace).filter(
        EnhancedUserWorkspace.id == workspace_id,
        EnhancedUserWorkspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    query = db.query(EnhancedResearchArtifact).filter(
        EnhancedResearchArtifact.workspace_id == workspace_id
    )
    
    if artifact_type:
        query = query.filter(EnhancedResearchArtifact.artifact_type == artifact_type)
    
    if stage_id:
        query = query.filter(EnhancedResearchArtifact.stage_id == stage_id)
    
    if status:
        query = query.filter(EnhancedResearchArtifact.status == status)
    
    artifacts = query.order_by(EnhancedResearchArtifact.created_at.desc()).all()
    
    return [
        {
            "id": artifact.id,
            "name": artifact.name,
            "artifact_type": artifact.artifact_type,
            "status": artifact.status,
            "content": artifact.content,
            "file_url": artifact.file_url,
            "metadata": artifact.artifact_metadata,
            "tags": artifact.tags,
            "ai_insights": artifact.ai_insights,
            "ai_summary": artifact.ai_summary,
            "ai_recommendations": artifact.ai_recommendations,
            "stage_id": artifact.stage_id,
            "created_at": artifact.created_at,
            "updated_at": artifact.updated_at
        } for artifact in artifacts
    ]

@router.put("/{workspace_id}/tasks/{task_id}/complete", response_model=dict)
def complete_task(
    workspace_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Complete task and update workspace progress"""
    
    # Verify workspace ownership
    workspace = db.query(EnhancedUserWorkspace).filter(
        EnhancedUserWorkspace.id == workspace_id,
        EnhancedUserWorkspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Find and complete task
    task = db.query(EnhancedWorkflowTask).join(EnhancedWorkflowStage).filter(
        EnhancedWorkflowTask.id == task_id,
        EnhancedWorkflowStage.workspace_id == workspace_id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    task.is_completed = True
    task.completed_at = datetime.utcnow()
    task.priority = "done"
    
    # Update workspace progress
    service = EnhancedWorkspaceService(db)
    progress_update = service.update_workspace_progress(workspace_id)
    
    # Update workspace last activity
    workspace.last_activity_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "task_completed": True,
        "progress_update": progress_update,
        "message": "Task completed successfully"
    }

@router.get("/{workspace_id}/analytics", response_model=dict)
def get_workspace_analytics(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get comprehensive workspace analytics"""
    
    workspace = db.query(EnhancedUserWorkspace).filter(
        EnhancedUserWorkspace.id == workspace_id,
        EnhancedUserWorkspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    service = EnhancedWorkspaceService(db)
    analytics = service.get_workspace_analytics(workspace_id)
    
    return analytics

@router.post("/{workspace_id}/custom-workflows", response_model=dict)
def create_custom_workflow(
    workspace_id: int,
    name: str,
    description: Optional[str] = None,
    workflow_config: Dict[str, Any] = None,
    is_public: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create custom workflow template"""
    
    # Verify workspace ownership
    workspace = db.query(EnhancedUserWorkspace).filter(
        EnhancedUserWorkspace.id == workspace_id,
        EnhancedUserWorkspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    custom_workflow = CustomWorkflow(
        workspace_id=workspace_id,
        created_by=current_user.id,
        name=name,
        description=description,
        workflow_config=workflow_config or {},
        is_public=is_public
    )
    
    db.add(custom_workflow)
    db.commit()
    
    return {
        "id": custom_workflow.id,
        "name": custom_workflow.name,
        "description": custom_workflow.description,
        "is_public": custom_workflow.is_public,
        "created_at": custom_workflow.created_at,
        "message": "Custom workflow created successfully"
    }

@router.get("/custom-workflows/public", response_model=List[dict])
def get_public_custom_workflows(
    skip: int = 0,
    limit: int = 50,
    workflow_type: Optional[WorkflowType] = None,
    db: Session = Depends(get_db)
):
    """Get public custom workflows (community marketplace)"""
    
    query = db.query(CustomWorkflow).filter(
        CustomWorkflow.is_public == True
    )
    
    if workflow_type:
        query = query.filter(CustomWorkflow.workflow_type == workflow_type)
    
    workflows = query.order_by(CustomWorkflow.usage_count.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "workflow_type": workflow.workflow_type,
            "usage_count": workflow.usage_count,
            "success_rate": workflow.success_rate,
            "created_by": {
                "id": workflow.creator.id,
                "username": workflow.creator.username,
                "avatar_url": workflow.creator.avatar_url
            },
            "created_at": workflow.created_at
        } for workflow in workflows
    ]

# =============================================================================
# 4 P's Smart Task Suggestions
# =============================================================================

PILLAR_TASK_TEMPLATES = {
    "product": [
        {"title": "Interview 5 potential customers", "description": "Validate pain points with real users", "priority": "high"},
        {"title": "Analyze competitor products", "description": "Document feature gaps and opportunities", "priority": "high"},
        {"title": "Create user survey", "description": "Gather quantitative demand data", "priority": "medium"},
        {"title": "Research trend data", "description": "Use Google Trends to validate growing demand", "priority": "medium"},
        {"title": "Define MVP features", "description": "List minimum features to solve core pain", "priority": "high"},
    ],
    "price": [
        {"title": "Research competitor pricing", "description": "Document pricing models in the market", "priority": "high"},
        {"title": "Calculate unit economics", "description": "Model CAC, LTV, and margins", "priority": "high"},
        {"title": "Survey willingness to pay", "description": "Ask potential customers about price sensitivity", "priority": "medium"},
        {"title": "Estimate market size (TAM/SAM/SOM)", "description": "Quantify the addressable market", "priority": "medium"},
        {"title": "Create pricing tiers", "description": "Design value-based pricing structure", "priority": "medium"},
    ],
    "place": [
        {"title": "Analyze target locations", "description": "Research best markets for launch", "priority": "high"},
        {"title": "Research local demographics", "description": "Understand population and income data", "priority": "medium"},
        {"title": "Identify distribution channels", "description": "Map how customers will find you", "priority": "high"},
        {"title": "Scout physical locations", "description": "If applicable, identify potential sites", "priority": "medium"},
        {"title": "Analyze foot traffic data", "description": "Research customer accessibility", "priority": "low"},
    ],
    "promotion": [
        {"title": "Map competitive landscape", "description": "Identify and analyze top 5 competitors", "priority": "high"},
        {"title": "Define unique value proposition", "description": "Articulate why customers choose you", "priority": "high"},
        {"title": "Create marketing channel plan", "description": "Identify top 3 customer acquisition channels", "priority": "medium"},
        {"title": "Estimate customer acquisition cost", "description": "Budget for marketing spend", "priority": "medium"},
        {"title": "Design brand positioning", "description": "Create messaging that differentiates", "priority": "medium"},
    ],
}


@router.get("/{workspace_id}/smart-tasks", response_model=dict)
def get_smart_task_suggestions(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get AI-powered task suggestions based on 4 P's analysis.
    
    Analyzes the opportunity's 4 P's scores and recommends tasks
    to strengthen weak areas.
    """
    from app.services.report_data_service import ReportDataService
    
    workspace = db.query(EnhancedUserWorkspace).filter(
        EnhancedUserWorkspace.id == workspace_id,
        EnhancedUserWorkspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    opportunity_id = workspace.opportunity_id
    
    # Get 4 P's data
    try:
        service = ReportDataService(db)
        four_ps = service.get_full_response(opportunity_id)
    except Exception as e:
        four_ps = None
    
    suggestions = []
    focus_areas = []
    
    if four_ps and four_ps.get("scores"):
        scores = four_ps["scores"]
        quality = four_ps.get("data_quality", {})
        
        # Sort pillars by score (weakest first)
        sorted_pillars = sorted(scores.items(), key=lambda x: x[1])
        
        for pillar, score in sorted_pillars:
            if score < 70:  # Needs attention
                focus_areas.append({
                    "pillar": pillar.upper(),
                    "score": score,
                    "status": "critical" if score < 40 else "needs_work" if score < 60 else "improving"
                })
                
                # Add tasks for this pillar
                pillar_tasks = PILLAR_TASK_TEMPLATES.get(pillar, [])
                for task in pillar_tasks[:3]:  # Top 3 tasks per weak pillar
                    suggestions.append({
                        "pillar": pillar.upper(),
                        "pillar_score": score,
                        **task
                    })
        
        # Include recommendations from data quality
        recommendations = quality.get("recommended_actions", [])
        
        return {
            "workspace_id": workspace_id,
            "opportunity_id": opportunity_id,
            "four_ps_scores": scores,
            "overall_score": four_ps.get("overall", 0),
            "data_quality": round(quality.get("completeness", 0) * 100),
            "focus_areas": focus_areas,
            "suggested_tasks": suggestions,
            "recommendations": recommendations,
            "message": f"Found {len(suggestions)} suggested tasks based on 4 P's analysis"
        }
    
    # Fallback if no 4 P's data
    return {
        "workspace_id": workspace_id,
        "opportunity_id": opportunity_id,
        "four_ps_scores": None,
        "focus_areas": [],
        "suggested_tasks": [],
        "recommendations": ["Generate 4 P's analysis to get personalized task suggestions"],
        "message": "No 4 P's data available. Complete market analysis for smart suggestions."
    }


@router.post("/{workspace_id}/smart-tasks/add", response_model=dict)
def add_smart_task(
    workspace_id: int,
    task_title: str,
    task_description: Optional[str] = None,
    task_priority: str = "medium",
    pillar: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a suggested task to the workspace."""
    
    workspace = db.query(EnhancedUserWorkspace).filter(
        EnhancedUserWorkspace.id == workspace_id,
        EnhancedUserWorkspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Find first active stage or create research stage
    active_stage = None
    for stage in workspace.workflow_stages:
        if stage.status == "in_progress":
            active_stage = stage
            break
    
    if not active_stage and workspace.workflow_stages:
        active_stage = workspace.workflow_stages[0]
    
    if not active_stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No workflow stage available"
        )
    
    # Create the task
    new_task = EnhancedWorkflowTask(
        stage_id=active_stage.id,
        title=task_title,
        description=task_description or f"Task from 4 P's {pillar.upper() if pillar else 'analysis'}",
        priority=task_priority,
        is_completed=False,
        sort_order=len(active_stage.tasks) + 1
    )
    
    db.add(new_task)
    workspace.last_activity_at = datetime.utcnow()
    db.commit()
    db.refresh(new_task)
    
    return {
        "task_id": new_task.id,
        "title": new_task.title,
        "stage_id": active_stage.id,
        "stage_name": active_stage.name,
        "pillar": pillar,
        "message": "Task added successfully"
    }

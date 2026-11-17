"""
backend/app/schemas.py â€” Pydantic request/response models.
"""
from __future__ import annotations
from datetime import date
from typing import Any, Optional
import re
from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
_PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).{16,200}$")

def _validate_email(v: str) -> str:
    s = (v or "").strip().lower()
    if not _EMAIL_RE.match(s):
        raise ValueError("A valid email address is required.")
    return s

def _validate_strong_password(v: str) -> str:
    if not _PASSWORD_RE.match(v or ""):
        raise ValueError("Password must be at least 16 characters and include uppercase, lowercase, number, and special character.")
    return v


class PlanRequest(BaseModel):
    budget_lakh: float = Field(gt=0, description="Total budget in lakh INR")
    strategy: str = Field(default="digonce_ilp")
    mobilisation_scale: float = Field(default=1.0, ge=0)
    min_ward_share: float = Field(default=0.0, ge=0, le=1)


class ScoreRequest(BaseModel):
    asset_id: str


class RecommendRequest(BaseModel):
    budget_lakh: float = Field(default=5000, gt=0)
    strategy: str = Field(default="digonce_ilp")
    mobilisation_scale: float = Field(default=1.0, ge=0)
    min_ward_share: float = Field(default=0.0, ge=0, le=1)
    ward: Optional[int] = None
    asset_type: Optional[str] = None
    min_risk: float = Field(default=0.0, ge=0, le=1)
    prefer_coordination: bool = True
    traffic_aware: bool = True
    urgency: str = Field(default="balanced")  # balanced | critical_first | leak_focus | equity
    limit: int = Field(default=40, ge=1, le=200)


class AgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[dict] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    kind: str = Field(default="not_working")  # not_working | suggestion | completed
    message: str = Field(min_length=3, max_length=1000)
    asset_id: Optional[str] = None
    district: Optional[str] = None
    name: Optional[str] = None


class FeedbackStatusRequest(BaseModel):
    status: str  # open | in_progress | done


# â”€â”€ Auth â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=16, max_length=200)
    name: str = Field(min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        return _validate_email(v)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_strong_password(v)


class BootstrapAdminRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=16, max_length=200)
    name: str = Field(min_length=1, max_length=100)
    bootstrap_key: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        return _validate_email(v)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_strong_password(v)


class ManagedUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=16, max_length=200)
    name: str = Field(min_length=1, max_length=100)
    role: str = Field(pattern="^(admin|field_worker|citizen)$")

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        return _validate_email(v)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_strong_password(v)


class ManagedUserUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    password: Optional[str] = Field(default=None, min_length=16, max_length=200)
    role: Optional[str] = Field(default=None, pattern="^(admin|field_worker|citizen)$")

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_strong_password(v)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)
    expected_role: Optional[str] = Field(default=None, pattern="^(citizen|admin|field_worker)$")

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        return _validate_email(v)


# â”€â”€ Citizen Reports â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ReportCreateRequest(BaseModel):
    category: str = Field(pattern="^(pothole|water_leak|streetlight|bridge_damage|drainage|waste|other)$")
    description: str = Field(min_length=3, max_length=2000)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    location_text: Optional[str] = Field(default=None, max_length=300)
    state: Optional[str] = Field(default="Tamil Nadu", max_length=100)
    district: Optional[str] = Field(default=None, max_length=100)
    taluk: Optional[str] = Field(default=None, max_length=100)
    block: Optional[str] = Field(default=None, max_length=100)
    local_body: Optional[str] = Field(default=None, max_length=120)
    local_body_type: Optional[str] = Field(default=None, max_length=80)
    ward: Optional[str] = Field(default=None, max_length=120)
    village: Optional[str] = Field(default=None, max_length=120)
    locality: Optional[str] = Field(default=None, max_length=200)
    pincode: Optional[str] = Field(default=None, max_length=20)
    hierarchy_source: Optional[str] = Field(default=None, max_length=80)
    image_filename: Optional[str] = Field(default=None, max_length=255)
    image_data_url: Optional[str] = Field(default=None, max_length=6_000_000)
    evidence_data_url: Optional[str] = Field(default=None, max_length=8_000_000)
    evidence_filename: Optional[str] = Field(default=None, max_length=255)


class ReportStatusRequest(BaseModel):
    status: str  # triaged | accepted | rejected | merged
    note: str = Field(default="")
    matched_asset_id: Optional[str] = None


class ReportUpdateRequest(BaseModel):
    category: str = Field(pattern="^(pothole|water_leak|streetlight|bridge_damage|drainage|waste|other)$")
    description: str = Field(min_length=3, max_length=2000)
    severity: Optional[str] = Field(default=None, pattern="^(low|medium|high|critical)$")
    location_text: Optional[str] = Field(default=None, max_length=300)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    state: Optional[str] = Field(default=None, max_length=100)
    district: Optional[str] = Field(default=None, max_length=100)
    taluk: Optional[str] = Field(default=None, max_length=100)
    block: Optional[str] = Field(default=None, max_length=100)
    local_body: Optional[str] = Field(default=None, max_length=120)
    local_body_type: Optional[str] = Field(default=None, max_length=80)
    ward: Optional[str] = Field(default=None, max_length=120)
    village: Optional[str] = Field(default=None, max_length=120)
    locality: Optional[str] = Field(default=None, max_length=200)
    pincode: Optional[str] = Field(default=None, max_length=20)
    hierarchy_source: Optional[str] = Field(default=None, max_length=80)


class CommunitySubscriptionRequest(BaseModel):
    district: Optional[str] = Field(default=None, max_length=100)
    taluk: Optional[str] = Field(default=None, max_length=100)
    block: Optional[str] = Field(default=None, max_length=100)
    local_body: Optional[str] = Field(default=None, max_length=120)
    ward: Optional[str] = Field(default=None, max_length=120)
    locality: Optional[str] = Field(default=None, max_length=200)


class CommunityCommentRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1000)


class CommunitySubscriptionRequest(BaseModel):
    district: Optional[str] = Field(default=None, max_length=100)
    taluk: Optional[str] = Field(default=None, max_length=100)
    local_body: Optional[str] = Field(default=None, max_length=100)
    ward: Optional[str] = Field(default=None, max_length=100)


# â”€â”€ Incidents â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class IncidentCreateRequest(BaseModel):
    asset_id: Optional[str] = None
    report_id: Optional[str] = None
    title: str = Field(min_length=3, max_length=300)
    description: str = Field(default="", max_length=2000)
    severity: str = Field(default="medium")  # low | medium | high | critical
    district: Optional[str] = None
    taluk: Optional[str] = Field(default=None, max_length=100)
    block: Optional[str] = Field(default=None, max_length=100)
    local_body: Optional[str] = Field(default=None, max_length=120)
    ward: Optional[str] = Field(default=None, max_length=120)
    locality: Optional[str] = Field(default=None, max_length=200)
    asset_type: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class IncidentTransitionRequest(BaseModel):
    status: str
    note: str = Field(default="")
    assigned_to: Optional[str] = None
    plan_id: Optional[str] = None
    evidence_url: Optional[str] = None


class IncidentAdminUpdateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str = Field(default="", max_length=2000)
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    district: Optional[str] = Field(default=None, max_length=100)
    taluk: Optional[str] = Field(default=None, max_length=100)
    block: Optional[str] = Field(default=None, max_length=100)
    local_body: Optional[str] = Field(default=None, max_length=120)
    ward: Optional[str] = Field(default=None, max_length=120)
    locality: Optional[str] = Field(default=None, max_length=200)
    asset_type: Optional[str] = Field(default=None, max_length=50)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)


class EvidenceAddRequest(BaseModel):
    evidence_url: Optional[str] = None
    image_data_url: Optional[str] = None
    note: str = Field(default="")


PROJECT_STATUS_PATTERN = "^(PROPOSED|SUBMITTED_FOR_APPROVAL|APPROVED|PLANNED|ONGOING|DELAYED|COMPLETED|VERIFIED|CANCELLED)$"


class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=3000)
    category: str = Field(min_length=2, max_length=80)
    district: str = Field(min_length=2, max_length=100)
    taluk: Optional[str] = Field(default=None, max_length=100)
    local_body: Optional[str] = Field(default=None, max_length=100)
    ward: Optional[str] = Field(default=None, max_length=100)
    department: Optional[str] = Field(default=None, max_length=150)
    responsible_authority: Optional[str] = Field(default=None, max_length=150)
    status: str = Field(default="PROPOSED", pattern=PROJECT_STATUS_PATTERN)
    estimated_cost_lakh: Optional[float] = Field(default=None, gt=0)
    funding_source: Optional[str] = Field(default=None, max_length=150)
    start_date: Optional[date] = None
    expected_completion_date: Optional[date] = None
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)


class ProjectUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, max_length=3000)
    category: Optional[str] = Field(default=None, min_length=2, max_length=80)
    district: Optional[str] = Field(default=None, min_length=2, max_length=100)
    taluk: Optional[str] = Field(default=None, max_length=100)
    local_body: Optional[str] = Field(default=None, max_length=100)
    ward: Optional[str] = Field(default=None, max_length=100)
    department: Optional[str] = Field(default=None, max_length=150)
    responsible_authority: Optional[str] = Field(default=None, max_length=150)
    status: Optional[str] = Field(default=None, pattern=PROJECT_STATUS_PATTERN)
    status_note: Optional[str] = Field(default=None, max_length=500)
    estimated_cost_lakh: Optional[float] = Field(default=None, gt=0)
    funding_source: Optional[str] = Field(default=None, max_length=150)
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    start_date: Optional[date] = None
    expected_completion_date: Optional[date] = None
    actual_completion_date: Optional[date] = None
    delay_reason: Optional[str] = Field(default=None, max_length=1000)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)


class ProjectMilestoneRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=1000)
    due_date: Optional[date] = None
    completed: bool = False


class ProjectMilestoneUpdateRequest(BaseModel):
    completed: bool


class ProjectExpenditureRequest(BaseModel):
    amount_lakh: float = Field(gt=0)
    description: str = Field(min_length=3, max_length=500)
    expenditure_date: date
    funding_source: Optional[str] = Field(default=None, max_length=150)
    reference: Optional[str] = Field(default=None, max_length=100)


class ManagedAssetCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    asset_type: str = Field(min_length=2, max_length=50)
    district: str = Field(min_length=2, max_length=100)
    ward: Optional[int] = Field(default=None, ge=1)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    age_years: Optional[float] = Field(default=None, ge=0, le=500)
    condition_score: Optional[float] = Field(default=None, ge=0, le=1)
    criticality: int = Field(default=1, ge=1, le=5)
    work_cost_lakh: Optional[float] = Field(default=None, ge=0)


class ManagedAssetUpdateRequest(ManagedAssetCreateRequest):
    pass


class AssetDetail(BaseModel):
    asset_id: str
    corridor_id: str
    asset_type: str
    material: str
    road_class: str
    age_years: float
    condition_score: float
    risk_score: float
    health_score: float
    health_band: str
    criticality: int
    work_cost_lakh: float
    mobilisation_cost_lakh: float
    ward: int
    lat: float
    lon: float
    attribution: list[dict]
    neighbours: list[dict]
    leak_status: Optional[float]
    recommendation: str


class PlanResponse(BaseModel):
    strategy: str
    budget_lakh: float
    selected_count: int
    corridors_opened: int
    planned_spend: float
    risk_reduction: float
    saving_vs_uncoordinated: float
    assets: list[dict]
    uncoordinated_spend: float
    uncoordinated_count: int

# ── District directory / officers / offices / public services ──────────────

class OfficerUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    designation: str = Field(min_length=1, max_length=200)
    department: str = Field(default="", max_length=200)
    district: str = Field(default="", max_length=100)
    taluk: str = Field(default="", max_length=100)
    block: str = Field(default="", max_length=100)
    local_body: str = Field(default="", max_length=120)
    ward: str = Field(default="", max_length=120)
    village: str = Field(default="", max_length=120)
    locality: str = Field(default="", max_length=200)
    jurisdiction: str = Field(default="", max_length=300)
    office_name: str = Field(default="", max_length=200)
    office_address: str = Field(default="", max_length=500)
    phone: str = Field(default="", max_length=50)
    email: str = Field(default="", max_length=200)
    working_hours: str = Field(default="", max_length=120)
    website: str = Field(default="", max_length=300)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    source_name: str = Field(default="", max_length=300)
    source_url: str = Field(default="", max_length=500)
    retrieved_at: str = Field(default="", max_length=40)
    verification_status: str = Field(default="unverified", pattern="^(unverified|verified|needs_update)$")
    last_verified: str = Field(default="", max_length=40)
    notes: str = Field(default="", max_length=1000)


class OfficeUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=250)
    office_type: str = Field(min_length=1, max_length=150)
    department: str = Field(default="", max_length=200)
    district: str = Field(default="", max_length=100)
    taluk: str = Field(default="", max_length=100)
    block: str = Field(default="", max_length=100)
    local_body: str = Field(default="", max_length=120)
    ward: str = Field(default="", max_length=120)
    village: str = Field(default="", max_length=120)
    locality: str = Field(default="", max_length=200)
    jurisdiction: str = Field(default="", max_length=300)
    address: str = Field(default="", max_length=500)
    phone: str = Field(default="", max_length=50)
    email: str = Field(default="", max_length=200)
    working_hours: str = Field(default="", max_length=120)
    website: str = Field(default="", max_length=300)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    source_name: str = Field(default="", max_length=300)
    source_url: str = Field(default="", max_length=500)
    retrieved_at: str = Field(default="", max_length=40)
    verification_status: str = Field(default="unverified", pattern="^(unverified|verified|needs_update)$")
    last_verified: str = Field(default="", max_length=40)
    notes: str = Field(default="", max_length=1000)


class PublicServiceUpsertRequest(BaseModel):
    service_id: str = Field(min_length=1, max_length=100)
    label: str = Field(default="", max_length=200)
    department: str = Field(default="", max_length=300)
    issue_category: str = Field(default="other", max_length=50)
    grievance_portal: str = Field(default="", max_length=500)
    note: str = Field(default="", max_length=1000)
    office_types: list[str] = Field(default_factory=list)
    source_name: str = Field(default="", max_length=300)
    source_url: str = Field(default="", max_length=500)
    verification_status: str = Field(default="reference", max_length=40)


class MapNotifyRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    district: Optional[str] = Field(None, max_length=100)
    taluk: Optional[str] = Field(None, max_length=120)
    block: Optional[str] = Field(None, max_length=120)
    local_body: Optional[str] = Field(None, max_length=120)
    ward: Optional[str] = Field(None, max_length=120)
    village: Optional[str] = Field(None, max_length=120)
    locality: Optional[str] = Field(None, max_length=200)
    display_name: Optional[str] = Field(None, max_length=500)
    note: Optional[str] = Field(None, max_length=1000)


class AnnouncementUpsertRequest(BaseModel):
    title: str = Field(min_length=2, max_length=250)
    body: str = Field(default="", max_length=5000)
    district: str = Field(default="", max_length=100)
    taluk: str = Field(default="", max_length=100)
    local_body: str = Field(default="", max_length=120)
    category: str = Field(default="general", max_length=80)
    source_name: str = Field(default="", max_length=300)
    source_url: str = Field(default="", max_length=500)
    verification_status: str = Field(default="unverified", pattern="^(unverified|verified|needs_update)$")
    published_at: Optional[str] = Field(default=None, max_length=40)

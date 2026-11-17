"""
backend/app/main.py â€” FastAPI application.

Serves built frontend at "/" and API under "/api".
Real-time city pulse over /ws/live.
"""
from __future__ import annotations

import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.app.schemas import (
    PlanRequest, ScoreRequest, RecommendRequest, AgentRequest,
    FeedbackRequest, FeedbackStatusRequest,
    RegisterRequest, LoginRequest, BootstrapAdminRequest, ManagedUserRequest, ManagedUserUpdateRequest,
    ReportCreateRequest, ReportStatusRequest, ReportUpdateRequest,
    CommunityCommentRequest, CommunitySubscriptionRequest,
    IncidentCreateRequest, IncidentTransitionRequest, IncidentAdminUpdateRequest,
    ManagedAssetCreateRequest, ManagedAssetUpdateRequest, EvidenceAddRequest,
    ProjectCreateRequest, ProjectUpdateRequest, ProjectMilestoneRequest,
    ProjectMilestoneUpdateRequest, ProjectExpenditureRequest,
    OfficerUpsertRequest, OfficeUpsertRequest, PublicServiceUpsertRequest, AnnouncementUpsertRequest,
)
from backend.app.services import (
    AnalyticsUnavailable, analytics_runtime_status, initialize_runtime, mark_runtime_unavailable,
    get_state, summary_kpis, corridors_geojson, assets_list,
    asset_detail, wards_summary, leaks_summary, traffic_summary,
    run_plan, score_asset,
)
from backend.app.live import get_engine, flexible_recommend
from backend.app.agent import run_agent
from backend.app import feedback as fb
from backend.app import users as usr
from backend.app import reports as rpt
from backend.app import community as community_mod
from backend.app import incidents as inc_mod
from backend.app import admin_assets as admin_assets_mod
from backend.app import projects as projects_mod
from backend.app import notifications as notif_mod
from backend.app import audit as audit_mod
from backend.app.attention import get_areas_needing_attention
from backend.app import governance as gov_mod
from backend.app import geography as geo_mod
from backend.app import directory as dir_mod
from backend.app import messaging as msg_mod
from backend.app.auth import (
    HTTPAuthorizationCredentials, get_current_user, require_admin, require_field, require_role,
)

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        state = initialize_runtime()
        engine = get_engine()
        engine.attach(state)
        engine.last_recs = engine.quick_recommendations(8)
        await engine.start()
    except Exception as exc:
        mark_runtime_unavailable(exc)
        logger.exception("Analytics runtime failed to initialize; authentication remains available")
        yield
        return
    yield
    await engine.stop()



app = FastAPI(title="NagarSync API", lifespan=lifespan)


@app.exception_handler(AnalyticsUnavailable)
async def analytics_unavailable_handler(_request, _exc: AnalyticsUnavailable):
    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Analytics features are temporarily unavailable. Authentication and account "
                "management remain available; use an organization-approved Python environment "
                "or contact your administrator."
            ),
            "service": "analytics",
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_AUTH_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/bootstrap",
}


@app.middleware("http")
async def protect_api_routes(request, call_next):
    path = request.url.path
    if path.startswith("/api/") and path not in PUBLIC_AUTH_PATHS and request.method != "OPTIONS":
        authorization = request.headers.get("authorization", "")
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() != "bearer" or not credentials:
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        try:
            get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials))
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


# â”€â”€ API routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# â”€â”€ Auth routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.post("/api/auth/register")
def auth_register(req: RegisterRequest):
    result = usr.register(req.email, req.password, "citizen", req.name)
    if isinstance(result, str):
        raise HTTPException(status_code=400, detail=result)
    return result


@app.post("/api/auth/bootstrap")
def auth_bootstrap(req: BootstrapAdminRequest):
    result = usr.bootstrap_admin(req.email, req.password, req.name, req.bootstrap_key)
    if isinstance(result, str):
        raise HTTPException(status_code=403 if "key" in result.lower() or "configured" in result.lower() else 409, detail=result)
    return result


@app.post("/api/auth/login")
def auth_login(req: LoginRequest):
    result = usr.login(req.email, req.password, req.expected_role)
    if isinstance(result, str):
        raise HTTPException(status_code=401, detail=result)
    return result


@app.post("/api/auth/logout")
def auth_logout(user: dict = Depends(get_current_user)):
    if not usr.revoke_tokens(user["sub"]):
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return {"status": "logged_out"}


@app.get("/api/auth/me")
def auth_me(user: dict = Depends(get_current_user)):
    return user


@app.get("/api/users")
def list_users(include_archived: bool = False, user: dict = Depends(require_admin)):
    return usr.list_users(include_archived=include_archived)


@app.post("/api/users")
def create_managed_user(req: ManagedUserRequest, user: dict = Depends(require_admin)):
    result = usr.create_managed_user(req.email, req.password, req.role, req.name)
    if isinstance(result, str):
        raise HTTPException(status_code=400, detail=result)
    audit_mod.record_event(user, "created", "user", result["user"]["id"], f"Created {req.role} account {req.email}")
    return result["user"]


@app.patch("/api/users/{user_id}")
def update_managed_user(user_id: str, req: ManagedUserUpdateRequest, user: dict = Depends(require_admin)):
    if user_id == user["sub"] and req.role is not None and req.role != "admin":
        raise HTTPException(status_code=409, detail="You cannot remove your own administrator role")
    target = usr.get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.get("archived_at") is None and target.get("role") == "admin" and req.role not in (None, "admin") and usr.active_admin_count() <= 1:
        raise HTTPException(status_code=409, detail="At least one active administrator must remain")
    if target.get("role") == "field_worker" and req.role not in (None, "field_worker") and any(
        incident.get("status") not in {"CLOSED", "CANCELLED", "REJECTED"}
        for incident in inc_mod.list_incidents(assigned_to=user_id, limit=2000)
    ):
        raise HTTPException(status_code=409, detail="Reassign or close this worker's active incidents before changing the role")
    result = usr.update_managed_user(user_id, req.name, req.role, req.password)
    if not result:
        raise HTTPException(status_code=404, detail="Active user not found or update invalid")
    changed = [key for key, value in (("name", req.name), ("role", req.role), ("password", req.password)) if value is not None]
    audit_mod.record_event(user, "updated", "user", user_id, f"Updated user fields: {', '.join(changed)}")
    return result


@app.post("/api/users/{user_id}/archive")
def archive_managed_user(user_id: str, user: dict = Depends(require_admin)):
    target = usr.get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if user_id == user["sub"]:
        raise HTTPException(status_code=409, detail="You cannot archive your own account")
    if target.get("role") == "admin" and target.get("archived_at") is None and usr.active_admin_count() <= 1:
        raise HTTPException(status_code=409, detail="At least one active administrator must remain")
    if target.get("role") == "field_worker" and any(
        incident.get("status") not in {"CLOSED", "CANCELLED", "REJECTED"}
        for incident in inc_mod.list_incidents(assigned_to=user_id, limit=2000)
    ):
        raise HTTPException(status_code=409, detail="Reassign or close this worker's active incidents before archiving the account")
    result = usr.set_user_archived(user_id, True)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    audit_mod.record_event(user, "archived", "user", user_id, f"Archived account {target.get('email', user_id)}")
    return result


@app.post("/api/users/{user_id}/restore")
def restore_managed_user(user_id: str, user: dict = Depends(require_admin)):
    result = usr.set_user_archived(user_id, False)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    audit_mod.record_event(user, "restored", "user", user_id, f"Restored account {result.get('email', user_id)}")
    return result


# â”€â”€ Citizen reports â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


# â”€â”€ Geography & jurisdiction (Tamil Nadu statewide) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.get("/api/geo/hierarchy")
def geo_hierarchy(user: dict = Depends(get_current_user)):
    return geo_mod.hierarchy_options()


@app.get("/api/geo/districts")
def geo_districts(user: dict = Depends(get_current_user)):
    return geo_mod.tn_districts()


@app.get("/api/geo/search")
def geo_search(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(8, ge=1, le=10),
    user: dict = Depends(get_current_user),
):
    return {"query": q, "results": geo_mod.search_places(q, limit=limit), "source": "OpenStreetMap Nominatim (live lookup when available)"}


@app.get("/api/geo/reverse")
def geo_reverse(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    user: dict = Depends(get_current_user),
):
    hierarchy = geo_mod.reverse_geocode(lat, lon)
    hierarchy["jurisdiction"] = geo_mod.jurisdiction_for_area(hierarchy)
    return hierarchy


@app.get("/api/geo/jurisdiction")
def geo_jurisdiction(
    district: str | None = Query(None),
    taluk: str | None = Query(None),
    block: str | None = Query(None),
    local_body: str | None = Query(None),
    ward: str | None = Query(None),
    locality: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    return geo_mod.jurisdiction_for_area({
        "district": district, "taluk": taluk, "block": block,
        "local_body": local_body, "ward": ward, "locality": locality,
    })


@app.post("/api/reports")
def create_report(req: ReportCreateRequest, user: dict = Depends(get_current_user)):
    # Check for possible duplicates
    dupes = rpt.check_duplicate(req.lat, req.lon, req.category)
    # resolve hierarchy from coordinates if available and fields missing
    resolved = {}
    if req.lat is not None and req.lon is not None:
        try:
            resolved = geo_mod.reverse_geocode(req.lat, req.lon)
        except Exception:
            resolved = {}
    def pick(field, req_val, *fallback_keys):
        v = (req_val or "").strip() if isinstance(req_val, str) else req_val
        if v:
            return v
        for k in fallback_keys:
            fv = (resolved.get(k) or "").strip()
            if fv:
                return fv
        return ""
    try:
        report = rpt.create_report(
            citizen_id=user["sub"],
            citizen_name=user.get("name", "Citizen"),
            category=req.category,
            severity=getattr(req, "severity", "medium"),
            description=req.description,
            lat=req.lat,
            lon=req.lon,
            location_text=req.location_text,
            state=pick("state", getattr(req, "state", None), "state") or "Tamil Nadu",
            district=pick("district", req.district, "district"),
            taluk=pick("taluk", req.taluk, "taluk"),
            block=pick("block", getattr(req, "block", None), "block"),
            local_body=pick("local_body", req.local_body, "local_body"),
            local_body_type=pick("local_body_type", getattr(req, "local_body_type", None), "local_body_type"),
            ward=pick("ward", req.ward, "ward", "ward_or_village"),
            village=pick("village", getattr(req, "village", None), "village"),
            locality=pick("locality", getattr(req, "locality", None), "locality"),
            pincode=pick("pincode", getattr(req, "pincode", None), "pincode"),
            hierarchy_source=pick("hierarchy_source", getattr(req, "hierarchy_source", None), "source") or ("nominatim_reverse" if resolved else ""),
            image_filename=req.image_filename,
            image_data_url=req.image_data_url,
            evidence_data_url=getattr(req, "evidence_data_url", None),
            evidence_filename=getattr(req, "evidence_filename", None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit_mod.record_event(user, "submitted", "report", report["id"], f"Submitted {req.category} report")
    area = {key: report.get(key) for key in community_mod.AREA_FIELDS if report.get(key)}
    if area.get("district"):
        try:
            recipients = set(community_mod.subscribed_users(area))
        except Exception:
            recipients = set()
        recipients.add(user["sub"])
        for recipient_id in recipients:
            if recipient_id == user["sub"]:
                continue
            notif_mod.create_notification(
                recipient_id=recipient_id,
                title="New infrastructure report in your followed area",
                message=f"A resident submitted a {req.category.replace('_', ' ')} report in {report.get('locality') or report.get('ward') or report.get('local_body') or report.get('taluk') or 'your area'}, {report.get('district') or 'Tamil Nadu'}.",
                kind="info",
                link="/public",
            )
    return {"report": report, "possible_duplicates": len(dupes), "duplicate_ids": [d["id"] for d in dupes[:3]]}


@app.get("/api/reports")
def list_reports(
    status: str | None = Query(None),
    district: str | None = Query(None, max_length=100),
    taluk: str | None = Query(None, max_length=100),
    block: str | None = Query(None, max_length=100),
    local_body: str | None = Query(None, max_length=120),
    ward: str | None = Query(None, max_length=120),
    locality: str | None = Query(None, max_length=200),
    limit: int = Query(50, ge=1, le=200),
    include_archived: bool = Query(False),
    user: dict = Depends(get_current_user),
):
    # Citizens see only their own; admins see all
    if user["role"] not in ("admin", "citizen"):
        raise HTTPException(status_code=403, detail="Only citizens and administrators can access reports")
    citizen_id = None if user["role"] == "admin" else user["sub"]
    return rpt.list_reports(
        citizen_id=citizen_id,
        status=status,
        limit=limit,
        include_archived=include_archived and user["role"] == "admin",
        area={
            key: value.strip()
            for key, value in {
                "district": district,
                "taluk": taluk,
                "block": block,
                "local_body": local_body,
                "ward": ward,
                "locality": locality,
            }.items()
            if value and value.strip()
        } or None,
    )


@app.get("/api/reports/nearby")
def nearby_reports(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(3.0, ge=0.2, le=25.0),
    limit: int = Query(50, ge=1, le=150),
    user: dict = Depends(get_current_user),
):
    """Privacy-safe nearby reports: no reporter identity, contact, or exact private details beyond report location."""
    items = rpt.nearby_reports(lat, lon, radius_km=radius_km, limit=limit, exclude_citizen_id=user["sub"])
    # attach public work status
    for item in items:
        rep = rpt.get_report(item["id"])
        if rep and rep.get("incident_id"):
            inc = inc_mod.get_incident(rep["incident_id"])
            if inc and inc.get("archived_at") is None:
                item["work_status"] = inc.get("status")
    return {"lat": lat, "lon": lon, "radius_km": radius_km, "count": len(items), "reports": items}


@app.get("/api/community/subscription")
def get_community_subscription(user: dict = Depends(get_current_user)):
    return {"area": community_mod.get_subscription(user["sub"])}


@app.put("/api/community/subscription")
def save_community_subscription(
    req: CommunitySubscriptionRequest,
    user: dict = Depends(get_current_user),
):
    values = req.model_dump()
    if not any(str(value or "").strip() for value in values.values()):
        return {"area": community_mod.set_subscription(user["sub"], None)}
    try:
        area = community_mod.normalize_area(values)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"area": community_mod.set_subscription(user["sub"], area)}


@app.get("/api/community/reports")
def get_community_reports(
    district: str = Query(..., min_length=2, max_length=100),
    taluk: str | None = Query(None, max_length=100),
    block: str | None = Query(None, max_length=100),
    local_body: str | None = Query(None, max_length=120),
    ward: str | None = Query(None, max_length=120),
    locality: str | None = Query(None, max_length=200),
    limit: int = Query(100, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    values = {
        "district": district,
        "taluk": taluk,
        "block": block,
        "local_body": local_body,
        "ward": ward,
        "locality": locality,
    }
    try:
        area = community_mod.normalize_area(values, allow_district_only=user["role"] == "admin")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    subscription = community_mod.get_subscription(user["sub"])
    if user["role"] != "admin" and (
        not subscription or not community_mod.same_area(subscription, area)
    ):
        raise HTTPException(status_code=403, detail="Follow this area before viewing its community reports")
    items = rpt.list_reports(area=area, limit=limit)
    public_items = []
    for report in items:
        public_report = {
            key: report.get(key)
            for key in (
                "id", "category", "description", "location_text", "state", "district", "taluk",
                "block", "local_body", "ward", "locality", "lat", "lon", "severity",
                "status", "incident_id", "created_at", "updated_at", "is_demo_sample", "has_image",
            )
        }
        public_report["status_history"] = [
            {key: event.get(key) for key in ("status", "ts", "note") if event.get(key) is not None}
            for event in report.get("status_history", [])
        ]
        public_report.update(community_mod.report_engagement(report["id"], user["sub"]))
        incident = inc_mod.get_incident(report["incident_id"]) if report.get("incident_id") else None
        if incident and incident.get("archived_at") is None:
            public_report["work_status"] = incident.get("status")
            public_report["work_updated_at"] = incident.get("updated_at")
            public_report["work_history"] = [
                {key: event.get(key) for key in ("status", "ts", "note") if event.get(key) is not None}
                for event in incident.get("status_history", [])
            ]
        public_items.append(public_report)
    return public_items


def _community_report_or_404(report_id: str, user: dict) -> dict:
    report = rpt.get_report(report_id)
    if not report or report.get("archived_at") is not None:
        raise HTTPException(status_code=404, detail="Community report not found")
    if not report.get("district") or not any(report.get(key) for key in community_mod.AREA_FIELDS[1:]):
        raise HTTPException(status_code=404, detail="Community report not found")
    if user["role"] != "admin":
        area = community_mod.get_subscription(user["sub"])
        if not area or not community_mod.area_matches(report, area):
            raise HTTPException(status_code=403, detail="Follow this report's area before engaging")
    return report


@app.post("/api/community/reports/{report_id}/acknowledge")
def acknowledge_community_report(
    report_id: str,
    user: dict = Depends(get_current_user),
):
    _community_report_or_404(report_id, user)
    return community_mod.acknowledge_report(report_id, user["sub"])


@app.post("/api/community/reports/{report_id}/comments")
def comment_on_community_report(
    report_id: str,
    req: CommunityCommentRequest,
    user: dict = Depends(get_current_user),
):
    report = _community_report_or_404(report_id, user)
    result = community_mod.add_comment(report_id, user["sub"], req.message)
    recipients = set(community_mod.subscribed_users({
        key: report[key] for key in community_mod.AREA_FIELDS if report.get(key)
    }))
    recipients.add(report["citizen_id"])
    for recipient_id in recipients - {user["sub"]}:
        notif_mod.create_notification(
            recipient_id=recipient_id,
            title="New community update on an infrastructure report",
            message=f"A community member added information to report {report_id}.",
            kind="info",
            link="/public",
        )
    return result


@app.get("/api/reports/{report_id}")
def get_report(report_id: str, user: dict = Depends(get_current_user)):
    r = rpt.get_report(report_id)
    if not r:
        raise HTTPException(404, "Report not found")
    if r.get("archived_at") is not None and user["role"] != "admin":
        raise HTTPException(404, "Report not found")
    # Citizens can only see their own
    if user["role"] == "citizen" and r["citizen_id"] != user["sub"]:
        raise HTTPException(403, "Forbidden")
    if user["role"] == "field_worker":
        raise HTTPException(403, "Field workers access reports through assigned incidents")
    return r


@app.get("/api/reports/{report_id}/image")
def get_report_image(report_id: str, user: dict = Depends(get_current_user)):
    report = rpt.get_report(report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    if report.get("archived_at") is not None and user["role"] != "admin":
        raise HTTPException(404, "Report not found")
    if user["role"] == "citizen" and report["citizen_id"] != user["sub"]:
        raise HTTPException(403, "Forbidden")
    if user["role"] == "field_worker":
        raise HTTPException(403, "Field workers access evidence through assigned incidents")
    image = rpt.image_path_for_report(report_id)
    if not image:
        raise HTTPException(404, "Report image not found")
    path, media_type = image
    return FileResponse(path, media_type=media_type)


@app.get("/api/reports/{report_id}/evidence")
def get_report_evidence(report_id: str, user: dict = Depends(get_current_user)):
    report = rpt.get_report(report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    if report.get("archived_at") is not None and user["role"] != "admin":
        raise HTTPException(404, "Report not found")
    if user["role"] == "citizen" and report["citizen_id"] != user["sub"]:
        raise HTTPException(403, "Forbidden")
    if user["role"] == "field_worker":
        raise HTTPException(403, "Field workers access evidence through assigned incidents")
    evidence = rpt.evidence_path_for_report(report_id)
    if not evidence:
        raise HTTPException(404, "Report evidence not found")
    path, media_type = evidence
    return FileResponse(path, media_type=media_type)


@app.patch("/api/reports/{report_id}")
def update_report(report_id: str, req: ReportStatusRequest, user: dict = Depends(require_admin)):
    r = rpt.update_report_status(
        report_id, req.status, user["sub"], req.note, req.matched_asset_id
    )
    if isinstance(r, str):
        raise HTTPException(status_code=409, detail=r)
    if not r:
        raise HTTPException(404, "Report not found")
    report = rpt.get_report(report_id)
    # If accepted, auto-create incident
    if req.status == "accepted":
        if report and not report.get("incident_id"):
            incident = inc_mod.create_incident(
                asset_id=req.matched_asset_id,
                report_id=report_id,
                title=f"{report['category'].replace('_',' ').title()} â€” {report.get('location_text','') or report.get('locality') or 'Location provided'}",
                description=report["description"],
                severity=report.get("severity") or ("high" if report["category"] in ("bridge_damage", "water_leak") else "medium"),
                created_by=user["sub"],
                district=report.get("district"),
                taluk=report.get("taluk"),
                block=report.get("block"),
                local_body=report.get("local_body"),
                ward=report.get("ward"),
                locality=report.get("locality"),
                asset_type=None,
                lat=report.get("lat"),
                lon=report.get("lon"),
            )
            rpt.attach_incident(report_id, incident["id"])
            audit_mod.record_event(
                user,
                "created",
                "incident",
                incident["id"],
                f"Created work order from citizen report {report_id}",
            )
    if report and report.get("citizen_id"):
        notif_mod.create_notification(
            recipient_id=report["citizen_id"],
            title=f"Report Status: {req.status.title()}",
            message=f"Your infrastructure report {report_id} ({report.get('category','')}) has been updated to {req.status}. {req.note or ''}".strip(),
            kind="info",
            link="/public",
        )
    if report:
        area = {key: report[key] for key in community_mod.AREA_FIELDS if report.get(key)}
        recipients = set(community_mod.subscribed_users(area)) if any(area.get(key) for key in community_mod.AREA_FIELDS[1:]) else set()
        recipients.add(report.get("citizen_id"))
        for recipient_id in recipients - {None, report.get("citizen_id")}:
            notif_mod.create_notification(
                recipient_id=recipient_id,
                title=f"Area report update: {report_id}",
                message=f"Municipal review changed this report to {req.status}. {req.note}".strip(),
                kind="verification",
                link="/public",
            )
    audit_mod.record_event(user, "status_changed", "report", report_id, f"Changed report status to {req.status}")
    return r


@app.put("/api/reports/{report_id}")
def edit_report(report_id: str, req: ReportUpdateRequest, user: dict = Depends(require_admin)):
    values = {
        "category": req.category,
        "description": req.description.strip(),
        "location_text": (req.location_text or "").strip(),
        "state": (req.state or "Tamil Nadu").strip() if req.state is not None else "Tamil Nadu",
        "district": (req.district or "").strip(),
        "taluk": (req.taluk or "").strip(),
        "block": (getattr(req, "block", None) or "").strip(),
        "local_body": (req.local_body or "").strip(),
        "local_body_type": (getattr(req, "local_body_type", None) or "").strip(),
        "ward": (req.ward or getattr(req, "village", None) or "").strip(),
        "ward_or_village": (req.ward or getattr(req, "village", None) or "").strip(),
        "village": (getattr(req, "village", None) or "").strip(),
        "locality": (getattr(req, "locality", None) or "").strip(),
        "pincode": (getattr(req, "pincode", None) or "").strip(),
        "hierarchy_source": (getattr(req, "hierarchy_source", None) or "").strip(),
        "lat": req.lat,
        "lon": req.lon,
    }
    if getattr(req, "severity", None):
        values["severity"] = req.severity
    result = rpt.update_report_fields(report_id, values, user["sub"])
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")
    audit_mod.record_event(user, "updated", "report", report_id, "Updated report details")
    return result


@app.post("/api/reports/{report_id}/archive")
def archive_report(report_id: str, user: dict = Depends(require_admin)):
    result = rpt.set_archived(report_id, True)
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")
    audit_mod.record_event(user, "archived", "report", report_id, "Archived citizen report")
    return result


@app.post("/api/reports/{report_id}/restore")
def restore_report(report_id: str, user: dict = Depends(require_admin)):
    result = rpt.set_archived(report_id, False)
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")
    audit_mod.record_event(user, "restored", "report", report_id, "Restored citizen report")
    return result


# â”€â”€ Incidents â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.post("/api/incidents")
def create_incident(req: IncidentCreateRequest, user: dict = Depends(require_admin)):
    incident = inc_mod.create_incident(
        asset_id=req.asset_id,
        report_id=req.report_id,
        title=req.title,
        description=req.description,
        severity=req.severity,
        created_by=user["sub"],
        district=req.district,
        taluk=req.taluk,
        block=req.block,
        local_body=req.local_body,
        ward=req.ward,
        locality=req.locality,
        asset_type=req.asset_type,
        lat=req.lat,
        lon=req.lon,
    )
    audit_mod.record_event(user, "created", "incident", incident["id"], f"Created {req.severity} severity work order")
    return incident


@app.get("/api/incidents")
def list_incidents(
    status: str | None = Query(None),
    asset_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    include_archived: bool = Query(False),
    user: dict = Depends(get_current_user),
):
    if user["role"] == "citizen":
        raise HTTPException(status_code=403, detail="Incident access is restricted")
    assigned_to = user["sub"] if user["role"] == "field_worker" else None
    return inc_mod.list_incidents(
        status=status,
        assigned_to=assigned_to,
        asset_id=asset_id,
        limit=limit,
        include_archived=include_archived and user["role"] == "admin",
    )


@app.get("/api/community/work")
def get_community_work(
    district: str = Query(..., min_length=2, max_length=100),
    taluk: str | None = Query(None, max_length=100),
    block: str | None = Query(None, max_length=100),
    local_body: str | None = Query(None, max_length=120),
    ward: str | None = Query(None, max_length=120),
    locality: str | None = Query(None, max_length=200),
    limit: int = Query(100, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    values = {"district": district, "taluk": taluk, "block": block, "local_body": local_body, "ward": ward, "locality": locality}
    try:
        area = community_mod.normalize_area(values, allow_district_only=user["role"] == "admin")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    subscription = community_mod.get_subscription(user["sub"])
    if user["role"] != "admin" and (
        not subscription or not community_mod.same_area(subscription, area)
    ):
        raise HTTPException(status_code=403, detail="Follow this area before viewing its municipal work")
    records = inc_mod.list_incidents(area=area, limit=limit)
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "description": item.get("description", ""),
            "severity": item.get("severity"),
            "status": item["status"],
            "district": item.get("district"),
            "taluk": item.get("taluk"),
            "block": item.get("block"),
            "local_body": item.get("local_body"),
            "ward": item.get("ward"),
            "locality": item.get("locality"),
            "lat": item.get("lat"),
            "lon": item.get("lon"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "is_demo_sample": bool(item.get("is_demo_sample")),
            "status_history": [
                {key: event.get(key) for key in ("status", "ts", "note") if event.get(key) is not None}
                for event in item.get("status_history", [])
            ],
        }
        for item in records
    ]


@app.get("/api/incidents/{inc_id}")
def get_incident(inc_id: str, user: dict = Depends(get_current_user)):
    i = inc_mod.get_incident(inc_id)
    if not i:
        raise HTTPException(404, "Incident not found")
    if i.get("archived_at") is not None and user["role"] != "admin":
        raise HTTPException(404, "Incident not found")
    if user["role"] == "citizen":
        raise HTTPException(status_code=403, detail="Incident access is restricted")
    if user["role"] == "field_worker" and i.get("assigned_to") != user["sub"]:
        raise HTTPException(status_code=403, detail="Incident is not assigned to this account")
    return i


@app.patch("/api/incidents/{inc_id}")
def transition_incident(inc_id: str, req: IncidentTransitionRequest, user: dict = Depends(require_field)):
    incident = inc_mod.get_incident(inc_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.get("archived_at") is not None and user["role"] != "admin":
        raise HTTPException(status_code=404, detail="Incident not found")
    if user["role"] == "field_worker":
        if incident.get("assigned_to") != user["sub"]:
            raise HTTPException(status_code=403, detail="Incident is not assigned to this account")
        if req.status not in {"IN_PROGRESS", "COMPLETION_SUBMITTED", "ESCALATED"}:
            raise HTTPException(status_code=403, detail="Field workers cannot perform this transition")
        if req.assigned_to or req.plan_id or req.evidence_url:
            raise HTTPException(status_code=403, detail="Field workers cannot change assignment or plan")
    elif req.status in {"APPROVED", "ASSIGNED", "VERIFIED", "CLOSED"}:
        if req.status == "ASSIGNED":
            assignee = usr.get_user_by_id(req.assigned_to or "")
            if not assignee or assignee.get("role") != "field_worker":
                raise HTTPException(status_code=422, detail="Assignment must target a registered field worker")
        if req.status == "VERIFIED" and not incident.get("evidence"):
            raise HTTPException(status_code=409, detail="Completion evidence is required before verification")
    result = inc_mod.transition_incident(
        inc_id, req.status, user["sub"], req.note,
        req.assigned_to, req.plan_id, req.evidence_url,
    )
    if isinstance(result, str):
        raise HTTPException(400, result)
    audit_mod.record_event(
        user,
        "status_changed",
        "incident",
        inc_id,
        f"Changed work order status from {incident['status']} to {req.status}",
    )

    # In-app notifications
    if req.status == "ASSIGNED" and req.assigned_to:
        notif_mod.create_notification(
            recipient_id=req.assigned_to,
            title=f"Work Assigned: {inc_id}",
            message=f"You have been assigned to infrastructure repair {inc_id}: {incident.get('title')}",
            kind="assignment",
            link="/field",
        )
    if req.status in {"IN_PROGRESS", "COMPLETION_SUBMITTED", "ESCALATED"}:
        for u in usr.list_users():
            if u.get("role") == "admin":
                notif_mod.create_notification(
                    recipient_id=u["id"],
                    title=f"Work Order {req.status.replace('_', ' ').title()}: {inc_id}",
                    message=f"{incident.get('title')} is now {req.status.replace('_', ' ').lower()}. {req.note}".strip(),
                    kind="verification" if req.status == "COMPLETION_SUBMITTED" else "alert" if req.status == "ESCALATED" else "info",
                    link="/dashboard",
                )
    if req.status in {"ASSIGNED", "IN_PROGRESS", "COMPLETION_SUBMITTED", "VERIFIED", "CLOSED", "ESCALATED"}:
        if incident.get("assigned_to"):
            notif_mod.create_notification(
                recipient_id=incident["assigned_to"],
                title=f"Work Order {req.status.replace('_', ' ').title()}: {inc_id}",
                message=f"{incident.get('title')} is now {req.status.replace('_', ' ').lower()}. {req.note}".strip(),
                kind="info",
                link="/field",
            )
    if incident.get("report_id"):
        rep = rpt.get_report(incident["report_id"])
        if rep and rep.get("citizen_id"):
            notif_mod.create_notification(
                recipient_id=rep["citizen_id"],
                title=f"Report Update: {incident['report_id']}",
                message=f"Your reported issue is now {req.status.replace('_', ' ').lower()}. {req.note}".strip(),
                kind="verification" if req.status in {"COMPLETION_SUBMITTED", "VERIFIED", "CLOSED"} else "info",
                link="/public",
            )
        area = {
            key: rep[key] for key in community_mod.AREA_FIELDS
            if rep and rep.get(key)
        } if rep else {}
        excluded = {user["sub"]}
        if rep and rep.get("citizen_id"):
            excluded.add(rep["citizen_id"])
        for recipient_id in set(community_mod.subscribed_users(area)) - excluded:
            notif_mod.create_notification(
                recipient_id=recipient_id,
                title=f"Municipal work update: {inc_id}",
                message=f"Work in your followed area is now {req.status.replace('_', ' ').lower()}. {req.note}".strip(),
                kind="verification" if req.status in {"COMPLETION_SUBMITTED", "VERIFIED", "CLOSED"} else "info",
                link="/public",
            )
    return result


@app.put("/api/incidents/{inc_id}")
def edit_incident(inc_id: str, req: IncidentAdminUpdateRequest, user: dict = Depends(require_admin)):
    result = inc_mod.update_incident_fields(
        inc_id,
        {
            "title": req.title.strip(),
            "description": req.description.strip(),
            "severity": req.severity,
            "district": req.district,
            "taluk": req.taluk,
            "block": getattr(req, "block", None),
            "local_body": req.local_body,
            "ward": req.ward,
            "locality": getattr(req, "locality", None),
            "asset_type": req.asset_type,
            "lat": req.lat,
            "lon": req.lon,
        },
    )
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    audit_mod.record_event(user, "updated", "incident", inc_id, "Updated work order details")
    return result


@app.post("/api/incidents/{inc_id}/archive")
def archive_incident(inc_id: str, user: dict = Depends(require_admin)):
    result = inc_mod.set_archived(inc_id, True)
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    audit_mod.record_event(user, "archived", "incident", inc_id, "Archived work order")
    return result


@app.post("/api/incidents/{inc_id}/restore")
def restore_incident(inc_id: str, user: dict = Depends(require_admin)):
    result = inc_mod.set_archived(inc_id, False)
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    audit_mod.record_event(user, "restored", "incident", inc_id, "Restored work order")
    return result


@app.post("/api/incidents/{inc_id}/evidence")
def add_evidence(
    inc_id: str,
    req: EvidenceAddRequest | None = None,
    evidence_url: str | None = Query(default=None),
    note: str = Query(default=""),
    user: dict = Depends(require_field),
):
    incident = inc_mod.get_incident(inc_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.get("archived_at") is not None and user["role"] != "admin":
        raise HTTPException(status_code=404, detail="Incident not found")
    if user["role"] == "field_worker":
        if incident.get("assigned_to") != user["sub"]:
            raise HTTPException(status_code=403, detail="Incident is not assigned to this account")
        if incident.get("status") not in {"IN_PROGRESS", "COMPLETION_SUBMITTED"}:
            raise HTTPException(status_code=409, detail="Evidence can only be added to active assigned work")
    final_url = (req.evidence_url if req and req.evidence_url else evidence_url) or "evidence_attached"
    final_note = (req.note if req and req.note else note) or ""
    final_image = req.image_data_url if req else None

    result = inc_mod.add_evidence(inc_id, final_url, user["sub"], final_note, image_data_url=final_image)
    if not result:
        raise HTTPException(404, "Incident not found")
    audit_mod.record_event(user, "evidence_added", "incident", inc_id, "Added work-order completion evidence")
    return result


@app.get("/api/incidents/{inc_id}/evidence-image/{fname}")
def get_incident_evidence_image(inc_id: str, fname: str, user: dict = Depends(get_current_user)):
    from ml.config import REPORTS_DIR
    target = REPORTS_DIR / "incident_evidence" / fname
    if not target.exists():
        raise HTTPException(status_code=404, detail="Evidence image not found")
    media_type = "image/jpeg"
    if fname.endswith(".png"):
        media_type = "image/png"
    elif fname.endswith(".webp"):
        media_type = "image/webp"
    return FileResponse(target, media_type=media_type)


# â”€â”€ Priority & Attention â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.get("/api/attention")
def areas_needing_attention(
    limit: int = Query(50, ge=1, le=200),
    ward: int | None = Query(None),
    asset_type: str | None = Query(None),
    min_priority: float = Query(30.0, ge=0, le=100),
    user: dict = Depends(get_current_user),
):
    return get_areas_needing_attention(get_state(), limit=limit, ward=ward, asset_type=asset_type, min_priority=min_priority)


# â”€â”€ Notifications â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.get("/api/notifications")
def get_user_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    return notif_mod.list_notifications(user["sub"], unread_only=unread_only, limit=limit)


@app.patch("/api/notifications/{notif_id}/read")
def read_notification(notif_id: str, user: dict = Depends(get_current_user)):
    ok = notif_mod.mark_as_read(notif_id, user["sub"])
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "read"}


@app.post("/api/notifications/read-all")
def read_all_notifications(user: dict = Depends(get_current_user)):
    count = notif_mod.mark_all_read(user["sub"])
    return {"marked_read": count}


@app.get("/api/admin/audit")
def list_audit_events(
    limit: int = Query(100, ge=1, le=500),
    entity_type: str | None = Query(None, max_length=50),
    actor_id: str | None = Query(None, max_length=100),
    user: dict = Depends(require_admin),
):
    return audit_mod.list_events(limit=limit, entity_type=entity_type, actor_id=actor_id)


# â”€â”€ Governance portal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.get("/api/governance/state")
def governance_state(user: dict = Depends(get_current_user)):
    """State-level overview: all districts, counts, recent activity."""
    return gov_mod.state_overview()


@app.get("/api/governance/district")
def governance_district(
    district: str = Query(..., min_length=2, max_length=100),
    user: dict = Depends(get_current_user),
):
    """District drill-down: taluks, municipalities, work order breakdown."""
    return gov_mod.district_overview(district.strip())


@app.get("/api/governance/area")
def governance_area(
    district: str = Query(..., min_length=2, max_length=100),
    taluk: str | None = Query(None, max_length=100),
    local_body: str | None = Query(None, max_length=100),
    ward: str | None = Query(None, max_length=100),
    user: dict = Depends(get_current_user),
):
    """Area-level detail: open issues, resolved work, development timeline, resource monitoring."""
    return gov_mod.area_overview(
        district.strip(),
        taluk.strip() if taluk else None,
        local_body.strip() if local_body else None,
        ward.strip() if ward else None,
    )


# â”€â”€ Development projects â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _project_public_view(project: dict) -> dict:
    public = {
        key: value for key, value in project.items()
        if key not in {"created_by", "archived_by"}
    }
    public["status_history"] = [
        {key: event.get(key) for key in ("status", "ts", "actor_name", "note") if event.get(key) is not None}
        for event in project.get("status_history", [])
    ]
    public["milestones"] = [
        {key: value for key, value in item.items() if key != "created_by"}
        for item in project.get("milestones", [])
    ]
    public["expenditures"] = [
        {key: value for key, value in item.items() if key != "recorded_by"}
        for item in project.get("expenditures", [])
    ]
    return public


@app.get("/api/projects")
def list_projects(
    district: str | None = Query(None, max_length=100),
    taluk: str | None = Query(None, max_length=100),
    local_body: str | None = Query(None, max_length=100),
    ward: str | None = Query(None, max_length=100),
    status: str | None = Query(None, pattern="^(PROPOSED|SUBMITTED_FOR_APPROVAL|APPROVED|PLANNED|ONGOING|DELAYED|COMPLETED|VERIFIED|CANCELLED)$"),
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    items = projects_mod.list_projects(
        district=district, taluk=taluk, local_body=local_body, ward=ward,
        status=status, include_private=user["role"] == "admin", limit=limit,
    )
    return items if user["role"] == "admin" else [_project_public_view(item) for item in items]


@app.get("/api/projects/{project_id}")
def get_project(project_id: str, user: dict = Depends(get_current_user)):
    project = projects_mod.get_project(project_id)
    if not project or project.get("archived_at") is not None:
        raise HTTPException(status_code=404, detail="Project not found")
    if user["role"] != "admin" and project.get("status") not in projects_mod.PUBLIC_STATUSES:
        raise HTTPException(status_code=404, detail="Project not found")
    return project if user["role"] == "admin" else _project_public_view(project)


@app.post("/api/projects")
def create_project(req: ProjectCreateRequest, user: dict = Depends(require_admin)):
    values = req.model_dump(mode="json")
    if values["status"] != "PROPOSED":
        raise HTTPException(status_code=422, detail="New projects must start as PROPOSED")
    project = projects_mod.create_project(values, user)
    audit_mod.record_event(user, "created", "project", project["id"], f"Created development project: {project['title']}")
    return project


@app.patch("/api/projects/{project_id}")
def update_project(project_id: str, req: ProjectUpdateRequest, user: dict = Depends(require_admin)):
    values = req.model_dump(mode="json", exclude_unset=True, exclude_none=True)
    previous = projects_mod.get_project(project_id)
    try:
        project = projects_mod.update_project(project_id, values, user)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if (
        previous
        and project.get("status") != previous.get("status")
        and project.get("status") in projects_mod.PUBLIC_STATUSES
    ):
        area = {
            key: project[key]
            for key in community_mod.AREA_FIELDS
            if project.get(key)
        }
        if area.get("district") and any(area.get(key) for key in community_mod.AREA_FIELDS[1:]):
            for recipient_id in community_mod.subscribed_users(area):
                notif_mod.create_notification(
                    recipient_id=recipient_id,
                    title="Development project update in your followed area",
                    message=f"{project['title']} is now {project['status'].replace('_', ' ').lower()}.",
                    kind="info",
                    link="/governance",
                )
    audit_mod.record_event(user, "updated", "project", project_id, f"Updated development project: {project['title']}")
    return project


@app.post("/api/projects/{project_id}/milestones")
def add_project_milestone(
    project_id: str,
    req: ProjectMilestoneRequest,
    user: dict = Depends(require_admin),
):
    milestone = projects_mod.add_milestone(
        project_id,
        req.model_dump(mode="json"),
        user,
    )
    if not milestone:
        raise HTTPException(status_code=404, detail="Project not found")
    audit_mod.record_event(user, "milestone_added", "project", project_id, f"Added project milestone: {req.title}")
    return milestone


@app.patch("/api/projects/{project_id}/milestones/{milestone_id}")
def update_project_milestone(
    project_id: str,
    milestone_id: str,
    req: ProjectMilestoneUpdateRequest,
    user: dict = Depends(require_admin),
):
    project = projects_mod.update_milestone(
        project_id,
        milestone_id,
        req.model_dump(),
        user,
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project or milestone not found")
    audit_mod.record_event(
        user, "milestone_updated", "project", project_id,
        f"Updated milestone {milestone_id} to {'complete' if req.completed else 'pending'}",
    )
    return project


@app.post("/api/projects/{project_id}/expenditures")
def add_project_expenditure(
    project_id: str,
    req: ProjectExpenditureRequest,
    user: dict = Depends(require_admin),
):
    try:
        project = projects_mod.add_expenditure(
            project_id,
            req.model_dump(mode="json"),
            user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    audit_mod.record_event(
        user, "expenditure_recorded", "project", project_id,
        f"Recorded expenditure of {req.amount_lakh:g} lakh for {project['title']}",
    )
    return project


@app.post("/api/projects/{project_id}/archive")
def archive_project(project_id: str, user: dict = Depends(require_admin)):
    project = projects_mod.archive_project(project_id, user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    audit_mod.record_event(user, "archived", "project", project_id, f"Archived development project: {project['title']}")
    return {"id": project_id, "archived": True}


# â”€â”€ Health â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.get("/api/health")
def health():
    analytics = analytics_runtime_status()
    mongo_ok = False
    mongo_err = None
    try:
        from backend.app.db import ping, last_error
        mongo_ok = ping()
        mongo_err = None if mongo_ok else last_error()
    except Exception as exc:
        mongo_err = str(exc)
    return {
        "status": "ok",
        "live": analytics["available"],
        "analytics": analytics,
        "mongo": mongo_ok,
        "mongo_error": mongo_err,
        "tick": get_engine().tick if analytics["available"] else None,
        "note": (
            "Simulated 37-district demo data and deterministic condition-priority scores; "
            "not verified municipal records or engineering assessments."
            if analytics.get("demo_only")
            else "Analytics unavailable; dashboard data could not be loaded."
            if not analytics["available"]
            else "Streaming and model data are demonstrations; not verified municipal records."
        ),
    }


@app.get("/api/summary")
def summary():
    base = summary_kpis(get_state())
    base["live"] = get_engine().status()["meta"]
    return base


@app.get("/api/corridors")
def corridors():
    return corridors_geojson(get_state())


@app.get("/api/assets")
def assets(
    asset_type: str | None = Query(None),
    ward: int | None = Query(None),
    min_risk: float = Query(0.0),
    limit: int = Query(200),
    corridor_id: str | None = Query(None, max_length=100),
):
    return assets_list(get_state(), asset_type, ward, min_risk, limit, corridor_id)


@app.get("/api/assets/{asset_id}")
def asset(asset_id: str):
    detail = asset_detail(asset_id, get_state())
    if detail is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return detail


@app.get("/api/admin/assets")
def list_managed_assets(include_archived: bool = False, user: dict = Depends(require_admin)):
    try:
        return admin_assets_mod.list_assets(include_archived=include_archived)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/admin/assets")
def create_managed_asset(req: ManagedAssetCreateRequest, user: dict = Depends(require_admin)):
    try:
        asset = admin_assets_mod.create_asset(req.model_dump(), user["sub"])
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not save managed asset: {exc}") from exc
    audit_mod.record_event(user, "created", "asset", asset["id"], f"Created unscored managed asset {asset['name']}")
    return asset


@app.put("/api/admin/assets/{asset_id}")
def update_managed_asset(asset_id: str, req: ManagedAssetUpdateRequest, user: dict = Depends(require_admin)):
    try:
        result = admin_assets_mod.update_asset(asset_id, req.model_dump())
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not update managed asset: {exc}") from exc
    if not result:
        raise HTTPException(status_code=404, detail="Managed asset not found")
    audit_mod.record_event(user, "updated", "asset", asset_id, "Updated managed asset details")
    return result


@app.post("/api/admin/assets/{asset_id}/archive")
def archive_managed_asset(asset_id: str, user: dict = Depends(require_admin)):
    try:
        result = admin_assets_mod.set_archived(asset_id, True)
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not archive managed asset: {exc}") from exc
    if not result:
        raise HTTPException(status_code=404, detail="Managed asset not found")
    audit_mod.record_event(user, "archived", "asset", asset_id, "Archived managed asset")
    return result


@app.post("/api/admin/assets/{asset_id}/restore")
def restore_managed_asset(asset_id: str, user: dict = Depends(require_admin)):
    try:
        result = admin_assets_mod.set_archived(asset_id, False)
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not restore managed asset: {exc}") from exc
    if not result:
        raise HTTPException(status_code=404, detail="Managed asset not found")
    audit_mod.record_event(user, "restored", "asset", asset_id, "Restored managed asset")
    return result


@app.get("/api/wards")
def wards():
    return wards_summary(get_state())


@app.get("/api/leaks")
def leaks():
    return leaks_summary(get_state())


@app.get("/api/traffic")
def traffic():
    return traffic_summary(get_state())


@app.get("/api/models")
def models(user: dict = Depends(require_admin)):
    return get_state().model_metrics


@app.get("/api/experiments")
def experiments(user: dict = Depends(require_admin)):
    return get_state().experiments


@app.get("/api/live")
def live_status():
    get_state()
    return get_engine().status()


@app.post("/api/plan")
def plan(req: PlanRequest, user: dict = Depends(require_admin)):
    return run_plan(
        req.budget_lakh, req.strategy,
        req.mobilisation_scale, req.min_ward_share,
        get_state(),
    )


@app.post("/api/recommend")
def recommend(req: RecommendRequest, user: dict = Depends(require_admin)):
    """Flexible real-time ML recommender â€” filters + NagarSync optimization + traffic windows."""
    return flexible_recommend(
        get_state(),
        budget_lakh=req.budget_lakh,
        strategy=req.strategy,
        mobilisation_scale=req.mobilisation_scale,
        min_ward_share=req.min_ward_share,
        ward=req.ward,
        asset_type=req.asset_type,
        min_risk=req.min_risk,
        prefer_coordination=req.prefer_coordination,
        traffic_aware=req.traffic_aware,
        urgency=req.urgency,
        limit=req.limit,
    )


@app.post("/api/agent")
def agent(req: AgentRequest, user: dict = Depends(require_admin)):
    """Interactive NagarSync agent â€” NL â†’ live ML tools (no external LLM)."""
    return run_agent(req.message, req.history)


@app.get("/api/feedback")
def feedback_list(status: str | None = Query(None), limit: int = Query(40, ge=1, le=100)):
    return fb.list_feedback(status=status, limit=limit)


@app.post("/api/feedback")
def feedback_create(req: FeedbackRequest):
    kind = req.kind if req.kind in ("not_working", "suggestion", "completed") else "not_working"
    return fb.add_feedback(
        kind=kind,
        message=req.message,
        asset_id=req.asset_id,
        district=req.district,
        name=req.name,
    )


@app.patch("/api/feedback/{fid}")
def feedback_update(fid: str, req: FeedbackStatusRequest):
    item = fb.update_feedback(fid, req.status)
    if item is None:
        raise HTTPException(status_code=404, detail="Feedback not found or bad status")
    return item


@app.post("/api/score")
def score(req: ScoreRequest, user: dict = Depends(require_field)):
    result = score_asset(req.asset_id, get_state())
    if result is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return result


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    offered_protocols = websocket.scope.get("subprotocols", [])
    credential_protocol = next(
        (protocol for protocol in offered_protocols if protocol.startswith("bearer.")),
        None,
    )
    if credential_protocol is None:
        await websocket.close(code=1008, reason="Authentication required")
        return
    try:
        get_current_user(HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=credential_protocol.removeprefix("bearer."),
        ))
    except AnalyticsUnavailable:
        await websocket.close(code=1013, reason="Analytics runtime unavailable")
        return
    except HTTPException:
        await websocket.close(code=1008, reason="Invalid or expired session")
        return
    try:
        get_state()
    except AnalyticsUnavailable:
        await websocket.close(code=1013, reason="Analytics runtime unavailable")
        return
    await websocket.accept(subprotocol="nagar-sync")
    engine = get_engine()
    queue = engine.subscribe()
    try:
        # Immediate snapshot so UI is not blank
        await websocket.send_json(engine.status() | {"type": "hello"})
        while True:
            raw = await queue.get()
            await websocket.send_text(raw)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        engine.unsubscribe(queue)



# ── District directory, officers, offices, public services (TN statewide) ──

@app.get("/api/directory/districts")
def list_district_directory(q: str | None = Query(None, max_length=120), user: dict = Depends(get_current_user)):
    data = dir_mod.load_district_profiles()
    items = data.get("districts", [])
    if q:
        ql = q.casefold()
        items = [d for d in items if ql in " ".join(str(d.get(k) or "") for k in ("name", "headquarters", "overview")).casefold()]
    return {"items": items, "total": len(items), "source": data.get("source", {})}


@app.get("/api/directory/districts/{district_id}")
def get_district_profile_api(district_id: str, user: dict = Depends(get_current_user)):
    summary = dir_mod.district_summary(district_id)
    if not summary.get("profile"):
        raise HTTPException(status_code=404, detail="District not found")
    return summary


@app.get("/api/directory/officers")
def list_officers_api(
    q: str | None = Query(None, max_length=200),
    district: str | None = Query(None, max_length=100),
    taluk: str | None = Query(None, max_length=100),
    department: str | None = Query(None, max_length=200),
    designation: str | None = Query(None, max_length=200),
    locality: str | None = Query(None, max_length=200),
    local_body: str | None = Query(None, max_length=120),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_archived: bool = Query(False),
    user: dict = Depends(get_current_user),
):
    filters = {"district": district, "taluk": taluk, "department": department, "designation": designation, "locality": locality, "local_body": local_body}
    return dir_mod.list_officers(filters=filters, q=q, page=page, page_size=page_size, include_archived=include_archived and user["role"] == "admin")


@app.get("/api/directory/officers/{officer_id}")
def get_officer_api(officer_id: str, user: dict = Depends(get_current_user)):
    rec = dir_mod.get_officer(officer_id)
    if not rec or (rec.get("archived_at") and user["role"] != "admin"):
        raise HTTPException(status_code=404, detail="Officer not found")
    return rec


@app.post("/api/directory/officers")
def create_officer_api(req: OfficerUpsertRequest, user: dict = Depends(require_admin)):
    rec = dir_mod.upsert_officer(req.model_dump(), user)
    audit_mod.record_event(user, "created", "officer", rec["id"], f"Created officer record: {rec.get('designation','')} {rec.get('name','')}".strip())
    return rec


@app.put("/api/directory/officers/{officer_id}")
def update_officer_api(officer_id: str, req: OfficerUpsertRequest, user: dict = Depends(require_admin)):
    if not dir_mod.get_officer(officer_id):
        raise HTTPException(status_code=404, detail="Officer not found")
    rec = dir_mod.upsert_officer(req.model_dump(), user, officer_id=officer_id)
    audit_mod.record_event(user, "updated", "officer", officer_id, f"Updated officer record: {rec.get('designation','')} {rec.get('name','')}".strip())
    return rec


@app.post("/api/directory/officers/{officer_id}/archive")
def archive_officer_api(officer_id: str, user: dict = Depends(require_admin)):
    rec = dir_mod.archive_officer(officer_id, user)
    if not rec:
        raise HTTPException(status_code=404, detail="Officer not found")
    audit_mod.record_event(user, "archived", "officer", officer_id, "Archived officer record")
    return {"id": officer_id, "archived": True}


@app.get("/api/directory/offices")
def list_offices_api(
    q: str | None = Query(None, max_length=200),
    district: str | None = Query(None, max_length=100),
    taluk: str | None = Query(None, max_length=100),
    department: str | None = Query(None, max_length=200),
    office_type: str | None = Query(None, max_length=150),
    locality: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_archived: bool = Query(False),
    user: dict = Depends(get_current_user),
):
    filters = {"district": district, "taluk": taluk, "department": department, "office_type": office_type, "locality": locality}
    return dir_mod.list_offices(filters=filters, q=q, page=page, page_size=page_size, include_archived=include_archived and user["role"] == "admin")


@app.get("/api/directory/offices/{office_id}")
def get_office_api(office_id: str, user: dict = Depends(get_current_user)):
    rec = dir_mod.get_office(office_id)
    if not rec or (rec.get("archived_at") and user["role"] != "admin"):
        raise HTTPException(status_code=404, detail="Office not found")
    return rec


@app.post("/api/directory/offices")
def create_office_api(req: OfficeUpsertRequest, user: dict = Depends(require_admin)):
    rec = dir_mod.upsert_office(req.model_dump(), user)
    audit_mod.record_event(user, "created", "office", rec["id"], f"Created office record: {rec.get('name','')}")
    return rec


@app.put("/api/directory/offices/{office_id}")
def update_office_api(office_id: str, req: OfficeUpsertRequest, user: dict = Depends(require_admin)):
    if not dir_mod.get_office(office_id):
        raise HTTPException(status_code=404, detail="Office not found")
    rec = dir_mod.upsert_office(req.model_dump(), user, office_id=office_id)
    audit_mod.record_event(user, "updated", "office", office_id, f"Updated office record: {rec.get('name','')}")
    return rec


@app.post("/api/directory/offices/{office_id}/archive")
def archive_office_api(office_id: str, user: dict = Depends(require_admin)):
    rec = dir_mod.archive_office(office_id, user)
    if not rec:
        raise HTTPException(status_code=404, detail="Office not found")
    audit_mod.record_event(user, "archived", "office", office_id, "Archived office record")
    return {"id": office_id, "archived": True}


@app.get("/api/directory/services")
def list_public_services_api(q: str | None = Query(None, max_length=200), user: dict = Depends(get_current_user)):
    return {"items": dir_mod.list_public_services(q=q)}


@app.put("/api/directory/services/{service_id}")
def upsert_public_service_api(service_id: str, req: PublicServiceUpsertRequest, user: dict = Depends(require_admin)):
    values = req.model_dump()
    values["service_id"] = service_id
    rec = dir_mod.upsert_public_service(values, user, service_id=service_id)
    audit_mod.record_event(user, "updated", "public_service", service_id, f"Updated public service mapping: {service_id}")
    return rec


@app.get("/api/directory/find-local-officer")
def find_local_officer_api(
    lat: float | None = Query(None, ge=-90, le=90),
    lon: float | None = Query(None, ge=-180, le=180),
    district: str | None = Query(None, max_length=100),
    taluk: str | None = Query(None, max_length=100),
    block: str | None = Query(None, max_length=100),
    local_body: str | None = Query(None, max_length=120),
    ward: str | None = Query(None, max_length=120),
    village: str | None = Query(None, max_length=120),
    locality: str | None = Query(None, max_length=200),
    q: str | None = Query(None, max_length=200),
    service_id: str | None = Query(None, max_length=100),
    user: dict = Depends(get_current_user),
):
    hierarchy = {}
    if lat is not None and lon is not None:
        try:
            hierarchy = geo_mod.reverse_geocode(lat, lon) or {}
        except Exception:
            hierarchy = {"lat": lat, "lon": lon, "source": "coordinates_only"}
    elif q:
        try:
            results = geo_mod.search_places(q, limit=1)
            if results:
                hierarchy = results[0]
        except Exception:
            hierarchy = {}
    area = {
        "district": district or hierarchy.get("district") or "",
        "taluk": taluk or hierarchy.get("taluk") or "",
        "block": block or hierarchy.get("block") or "",
        "local_body": local_body or hierarchy.get("local_body") or "",
        "ward": ward or hierarchy.get("ward") or hierarchy.get("ward_or_village") or "",
        "village": village or hierarchy.get("village") or hierarchy.get("ward_or_village") or "",
        "locality": locality or hierarchy.get("locality") or "",
        "state": hierarchy.get("state") or "Tamil Nadu",
        "display_name": hierarchy.get("display_name") or "",
        "lat": hierarchy.get("lat") if hierarchy.get("lat") is not None else lat,
        "lon": hierarchy.get("lon") if hierarchy.get("lon") is not None else lon,
    }
    result = dir_mod.find_local_contacts(area, service_id=service_id)
    result["hierarchy"] = hierarchy
    result["jurisdiction"] = geo_mod.jurisdiction_for_area(area)
    return result


@app.get("/api/directory/announcements")
def list_announcements_api(
    district: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    return dir_mod.list_announcements(filters={"district": district} if district else {}, page=page, page_size=page_size)


@app.post("/api/directory/announcements")
def create_announcement_api(req: AnnouncementUpsertRequest, user: dict = Depends(require_admin)):
    rec = dir_mod.upsert_announcement(req.model_dump(), user)
    audit_mod.record_event(user, "created", "announcement", rec["id"], f"Created announcement: {rec.get('title','')}")
    return rec


@app.put("/api/directory/announcements/{ann_id}")
def update_announcement_api(ann_id: str, req: AnnouncementUpsertRequest, user: dict = Depends(require_admin)):
    rec = dir_mod.upsert_announcement(req.model_dump(), user, ann_id=ann_id)
    audit_mod.record_event(user, "updated", "announcement", ann_id, f"Updated announcement: {rec.get('title','')}")
    return rec


@app.post("/api/directory/announcements/{ann_id}/archive")
def archive_announcement_api(ann_id: str, user: dict = Depends(require_admin)):
    rec = dir_mod.archive_announcement(ann_id, user)
    if not rec:
        raise HTTPException(status_code=404, detail="Announcement not found")
    audit_mod.record_event(user, "archived", "announcement", ann_id, "Archived announcement")
    return {"id": ann_id, "archived": True}

# â”€â”€ Serve frontend â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Do not swallow API/WS
        if full_path.startswith("api") or full_path.startswith("ws"):
            raise HTTPException(status_code=404)
        target = FRONTEND_DIST / full_path
        if full_path and target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")




# ── Map location notification ─────────────────────────────────────────────

@app.post("/api/map/notify")
def notify_map_location(req: schemas.MapNotifyRequest, user: dict = Depends(get_current_user)):
    """Create in-app notifications for admins/field workers for a selected map location; attempt email when SMTP configured."""
    try:
        hierarchy = geo_mod.reverse_geocode(req.lat, req.lon) or {}
    except Exception:
        hierarchy = {}
    area = {
        "state": hierarchy.get("state") or "Tamil Nadu",
        "district": (req.district or hierarchy.get("district") or "").strip(),
        "taluk": (req.taluk or hierarchy.get("taluk") or "").strip(),
        "block": (req.block or hierarchy.get("block") or "").strip(),
        "local_body": (req.local_body or hierarchy.get("local_body") or "").strip(),
        "ward": (req.ward or hierarchy.get("ward") or hierarchy.get("ward_or_village") or "").strip(),
        "village": (req.village or hierarchy.get("village") or "").strip(),
        "locality": (req.locality or hierarchy.get("locality") or "").strip(),
        "display_name": (req.display_name or hierarchy.get("display_name") or "").strip(),
        "lat": req.lat,
        "lon": req.lon,
    }
    recipients = usr.users_for_area_roles(area.get("district") or None)
    actor = user.get("name") or user.get("email") or "A user"
    area_label = ", ".join([p for p in [area.get("locality"), area.get("ward") or area.get("village"), area.get("local_body"), area.get("taluk"), area.get("district"), area.get("state")] if p]) or "Tamil Nadu"
    title = f"Map attention: {area.get('district') or 'Tamil Nadu'}"
    msg_lines = [
        f"{actor} selected a location on the Tamil Nadu GIS map that requires attention.",
        f"Area: {area_label}",
        f"Coordinates: {req.lat:.6f}, {req.lon:.6f}",
    ]
    if req.note:
        msg_lines.append(f"Note: {req.note.strip()}")
    msg_lines.append("Review this location in NagarSync and take appropriate action.")
    message = "\n".join(msg_lines)
    notified_ids = []
    email_results = []
    for r in recipients:
        notif_mod.create_notification(r["id"], title, message[:1000], kind="alert", link="/map")
        notified_ids.append(r["id"])
        if r.get("email"):
            email_results.append(msg_mod.send_email_notification(r["email"], title, message))
    audit_mod.record_event(user, "notified", "map_location", f"{req.lat:.5f},{req.lon:.5f}", f"Map notify for {area_label} -> {len(notified_ids)} recipients")
    return {
        "ok": True,
        "area": area,
        "notified_users": len(notified_ids),
        "email_attempted": sum(1 for e in email_results if e.get("attempted")),
        "email_delivered": sum(1 for e in email_results if e.get("delivered")),
        "email_configured": any(e.get("attempted") for e in email_results),
        "message": "In-app notifications created for available administrators/field staff." + (" Email delivery attempted where SMTP is configured." if email_results else " Configure SMTP_HOST/SMTP_* to enable email delivery."),
    }

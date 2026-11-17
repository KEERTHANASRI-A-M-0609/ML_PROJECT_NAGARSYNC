"""
backend/app/agent.py — Interactive NagarSync ops agent.

Local tool-using agent (no external LLM). Parses short natural-language
commands and runs live ML tools: recommend, score, districts, leaks, plan.
"""
from __future__ import annotations

import re
from typing import Any

from ml.config import district_name, DISTRICTS, N_DISTRICTS
from backend.app.live import get_engine, flexible_recommend
from backend.app.services import (
    get_state, summary_kpis, asset_detail, wards_summary, leaks_summary,
)


DISTRICT_ALIAS = {d[0].lower(): i for i, d in enumerate(DISTRICTS)}
# also allow partials
for i, d in enumerate(DISTRICTS):
    DISTRICT_ALIAS[d[0].lower().split()[0]] = i


def _find_district(text: str) -> int | None:
    t = text.lower()
    # longest name first
    for name, idx in sorted(DISTRICT_ALIAS.items(), key=lambda x: -len(x[0])):
        if name in t:
            return idx
    m = re.search(r"district\s+(\d+)|ward\s+(\d+)", t)
    if m:
        return int(m.group(1) or m.group(2))
    return None


def _find_budget(text: str, default: float = 3000.0) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lacs|cr|crore)?", text.lower())
    if not m:
        return default
    val = float(m.group(1))
    if "crore" in text.lower() or "cr" in text.lower():
        val *= 100  # crore → lakh
    return max(100.0, val)


def _find_asset_id(text: str) -> str | None:
    m = re.search(r"\b(A\d{4,6})\b", text, re.I)
    return m.group(1).upper() if m else None


def _find_type(text: str) -> str | None:
    for t in ("pipe", "road", "bridge", "streetlight"):
        if t in text.lower() or (t == "streetlight" and "light" in text.lower()):
            return t
    return None


def run_agent(message: str, history: list[dict] | None = None) -> dict[str, Any]:
    """Process one user message → reply + optional cards/actions."""
    state = get_state()
    eng = get_engine()
    text = (message or "").strip()
    low = text.lower()
    history = history or []

    if not text:
        return {"reply": "Ask me to plan repairs, check a district, score an asset, or show live alerts.", "cards": [], "actions": []}

    # greetings / help
    if re.match(r"^(hi|hello|hey|help|what can you)\b", low):
        return {
            "reply": (
                "I'm NagarSync Agent — statewide Tamil Nadu ops.\n"
                "Try: “plan Madurai with 2000 lakh”, “top risks in Coimbatore”, "
                "“score A00012”, “leak hotspots”, “live status”."
            ),
            "cards": eng.last_recs[:4],
            "actions": ["live", "recommend"],
        }

    # live status
    if any(k in low for k in ("live", "status", "pulse", "tick", "how is the city", "statewide")):
        st = eng.status()
        k = st["kpis"]
        return {
            "reply": (
                f"Live tick {st['tick']} · mean risk {(k['mean_risk']*100):.1f}% · "
                f"{k['critical_assets']} critical of {k['total_assets']} assets across "
                f"{N_DISTRICTS} TN districts."
            ),
            "cards": st.get("recommendations", [])[:6],
            "alerts": st.get("recent_alerts", [])[:5],
            "actions": ["live"],
        }

    # score / inspect asset
    aid = _find_asset_id(text)
    if aid or any(k in low for k in ("score", "inspect", "explain", "why is")):
        if not aid:
            return {"reply": "Give an asset id like A00012.", "cards": [], "actions": ["inspect"]}
        detail = asset_detail(aid, state)
        if not detail:
            return {"reply": f"{aid} not found in the live snapshot.", "cards": [], "actions": []}
        top = (detail.get("attribution") or [])[:3]
        drivers = ", ".join(
            f"{a.get('feature', '?')} ({a.get('delta_pp', a.get('delta', 0)):+.1f}pp)"
            if isinstance(a.get("delta_pp", a.get("delta")), (int, float))
            else str(a.get("feature"))
            for a in top
        ) or "see inspector"
        return {
            "reply": (
                f"{aid} in {detail.get('district', district_name(detail['ward']))}: "
                f"risk {detail['risk_score']*100:.1f}% ({detail['health_band']}). "
                f"{detail['recommendation']} Drivers: {drivers}."
            ),
            "cards": [{
                "rank": 1,
                "asset_id": aid,
                "asset_type": detail["asset_type"],
                "ward": detail["ward"],
                "district": detail.get("district"),
                "risk_score": detail["risk_score"],
                "health_band": detail["health_band"],
                "work_cost_lakh": detail["work_cost_lakh"],
                "reasons": [detail["recommendation"]],
                "action": detail["recommendation"],
            }],
            "detail": detail,
            "actions": ["inspect"],
        }

    # leaks
    if "leak" in low:
        leaks = sorted(leaks_summary(state), key=lambda x: -x["leak_score"])[:5]
        lines = [
            f"{district_name(l['dma'])}: {(l['leak_score']*100):.0f}% ({l['recent_leak_days']} leak-days)"
            for l in leaks
        ]
        return {
            "reply": "Top leak-detector DMAs:\n" + "\n".join(lines),
            "cards": [],
            "leaks": leaks,
            "actions": ["leaks"],
        }

    # district risks / top assets
    district = _find_district(text)
    if district is not None and any(k in low for k in ("risk", "top", "critical", "hotspot", "worst", "show")):
        wards = {w["ward"]: w for w in wards_summary(state)}
        w = wards.get(district)
        name = district_name(district)
        if not w:
            return {"reply": f"No assets for {name}.", "cards": [], "actions": []}
        # pull live recs filtered
        recs = [r for r in eng.quick_recommendations(12) if r["ward"] == district][:6]
        if not recs:
            # force recommend filter
            plan = flexible_recommend(
                state, budget_lakh=2000, strategy="greedy_coordinated",
                ward=district, limit=6, urgency="critical_first",
            )
            recs = [{**a, "rank": i + 1} for i, a in enumerate(plan.get("assets", [])[:6])]
        return {
            "reply": (
                f"{name}: mean risk {w['mean_risk']*100:.1f}%, "
                f"{w['critical_count']} critical, leak {(w['leak_score']*100):.0f}%. "
                f"Here are ML picks for the district."
            ),
            "cards": recs,
            "actions": ["recommend"],
        }

    # plan / recommend
    if any(k in low for k in ("plan", "recommend", "optim", "budget", "schedule", "digonce", "coordinate")):
        budget = _find_budget(text, 3000)
        district = _find_district(text)
        atype = _find_type(text)
        urgency = "balanced"
        if "leak" in low:
            urgency = "leak_focus"
        elif "critical" in low or "urgent" in low:
            urgency = "critical_first"
        elif "equity" in low or "fair" in low:
            urgency = "equity"
        strategy = "digonce_ilp" if "ilp" in low else "greedy_coordinated"
        plan = flexible_recommend(
            state,
            budget_lakh=budget,
            strategy=strategy,
            ward=district,
            asset_type=atype,
            urgency=urgency,
            prefer_coordination=True,
            traffic_aware=True,
            limit=10,
        )
        where = district_name(district) if district is not None else "all Tamil Nadu"
        return {
            "reply": (
                f"Plan for {where} · ₹{budget:.0f}L · {plan['strategy']} / {plan['urgency']}: "
                f"{plan['selected_count']} assets, {plan['corridors_opened']} corridors, "
                f"spend ₹{plan['planned_spend']:.0f}L, risk cut {plan['risk_reduction']:.2f} "
                f"(+{plan['saving_vs_uncoordinated']:.2f} vs uncoordinated)."
            ),
            "cards": [{**a, "rank": i + 1} for i, a in enumerate(plan.get("assets", [])[:8])],
            "plan": {
                "selected_count": plan["selected_count"],
                "planned_spend": plan["planned_spend"],
                "risk_reduction": plan["risk_reduction"],
                "saving_vs_uncoordinated": plan["saving_vs_uncoordinated"],
                "corridors_opened": plan["corridors_opened"],
                "strategy": plan["strategy"],
            },
            "actions": ["recommend", "planner"],
        }

    # summary KPIs
    if any(k in low for k in ("summary", "kpi", "overview", "stats")):
        k = summary_kpis(state)
        return {
            "reply": (
                f"TN snapshot: {k['total_assets']} assets, {k['critical_assets']} critical, "
                f"mean risk {k['mean_risk']*100:.1f}%, {k.get('n_districts', k['n_wards'])} districts."
            ),
            "cards": eng.last_recs[:5],
            "actions": ["dashboard"],
        }

    # fallback — treat as recommend with optional district
    district = _find_district(text)
    plan = flexible_recommend(
        state, budget_lakh=_find_budget(text, 2500),
        strategy="greedy_coordinated", ward=district,
        asset_type=_find_type(text), urgency="balanced", limit=8,
    )
    where = district_name(district) if district is not None else "Tamil Nadu"
    return {
        "reply": (
            f"I ran a quick NagarSync recommendation for {where}. "
            f"{plan['selected_count']} assets selected. "
            f"Say “plan …”, “score A…”, or “leaks” for other tools."
        ),
        "cards": [{**a, "rank": i + 1} for i, a in enumerate(plan.get("assets", [])[:6])],
        "actions": ["recommend"],
    }

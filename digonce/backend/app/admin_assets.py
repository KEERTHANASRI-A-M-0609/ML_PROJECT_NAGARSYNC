"""Admin-maintained asset register, kept separate from simulated model inputs."""
from __future__ import annotations

import json
import time
import uuid
from threading import Lock

from ml.config import REPORTS_DIR

_STORE = REPORTS_DIR / "managed_assets.json"
_LOCK = Lock()


def _load() -> list[dict]:
    if not _STORE.exists():
        return []
    try:
        items = json.loads(_STORE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read managed asset records: {exc}") from exc
    if not isinstance(items, list):
        raise RuntimeError("Managed asset store must contain a JSON list")
    return items


def _save(items: list[dict]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(items, indent=2), encoding="utf-8")


def list_assets(include_archived: bool = False) -> list[dict]:
    with _LOCK:
        items = _load()
    if not include_archived:
        items = [item for item in items if item.get("archived_at") is None]
    return sorted(items, key=lambda item: item["created_at"], reverse=True)


def get_asset(asset_id: str) -> dict | None:
    with _LOCK:
        return next((item for item in _load() if item["id"] == asset_id), None)


def create_asset(values: dict, created_by: str) -> dict:
    now = time.time()
    asset = {
        **values,
        "id": "MNA-" + str(uuid.uuid4())[:8].upper(),
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "archived_at": None,
        "model_status": "unscored_manual_record",
    }
    with _LOCK:
        items = _load()
        items.append(asset)
        _save(items)
    return asset


def update_asset(asset_id: str, values: dict) -> dict | None:
    with _LOCK:
        items = _load()
        for asset in items:
            if asset["id"] == asset_id:
                asset.update(values)
                asset["updated_at"] = time.time()
                _save(items)
                return asset
    return None


def set_archived(asset_id: str, archived: bool) -> dict | None:
    with _LOCK:
        items = _load()
        for asset in items:
            if asset["id"] == asset_id:
                asset["archived_at"] = time.time() if archived else None
                asset["updated_at"] = time.time()
                _save(items)
                return asset
    return None

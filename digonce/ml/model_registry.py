from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from ml.config import MODELS_DIR


def model_registry_entry(
    model_name: str,
    model_obj: Any,
    feature_list: list[str],
    metrics: dict[str, Any],
    training_data_version: str = "simulated-v1",
    model_version: str | None = None,
    random_seed: int = 42,
) -> dict[str, Any]:
    """Return structured metadata for every trained model artifact."""
    if model_version is None:
        model_version = f"{model_name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    return {
        "model_name": model_name,
        "model_version": model_version,
        "training_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "feature_list": list(feature_list),
        "training_data_version": training_data_version,
        "metrics": metrics,
        "random_seed": int(random_seed),
        "artifact_path": str(Path(MODELS_DIR) / f"{model_name}.joblib"),
        "model_class": model_obj.__class__.__name__,
    }


def save_model_artifact(
    model_name: str,
    model_obj: Any,
    feature_list: list[str],
    metrics: dict[str, Any],
    *,
    model_version: str | None = None,
    training_data_version: str = "simulated-v1",
    random_seed: int = 42,
) -> dict[str, Any]:
    """Persist model and a JSON sidecar with registry metadata."""
    import joblib

    registry = model_registry_entry(
        model_name=model_name,
        model_obj=model_obj,
        feature_list=feature_list,
        metrics=metrics,
        training_data_version=training_data_version,
        model_version=model_version,
        random_seed=random_seed,
    )
    artifact_path = Path(MODELS_DIR) / f"{model_name}.joblib"
    sidecar_path = artifact_path.with_suffix(".json")
    joblib.dump(model_obj, artifact_path)
    sidecar_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return registry


def load_model_artifact(model_name: str, *, fallback: Any | None = None) -> Any:
    import joblib

    artifact = Path(MODELS_DIR) / f"{model_name}.joblib"
    if artifact.exists():
        return joblib.load(artifact)
    return fallback

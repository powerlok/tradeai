"""File-backed registry for versioned ML model candidates and active models."""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

REGISTRY_PATH = "/app/models/registry.json"


def _read() -> Dict[str, Any]:
    if not os.path.exists(REGISTRY_PATH):
        return {"models": {}}
    with open(REGISTRY_PATH, "r", encoding="utf-8") as registry_file:
        return json.load(registry_file)


def _write(registry: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    temporary_path = f"{REGISTRY_PATH}.tmp"
    with open(temporary_path, "w", encoding="utf-8") as registry_file:
        json.dump(registry, registry_file, indent=2, sort_keys=True)
    os.replace(temporary_path, REGISTRY_PATH)


def model_key(symbol: str, timeframe: str, model_type: str) -> str:
    return f"{symbol.upper()}|{timeframe}|{model_type.lower()}"


def new_version() -> str:
    return datetime.now(timezone.utc).strftime("v%Y%m%d%H%M%S%f")


def version_dir(symbol: str, timeframe: str, model_type: str, version: str) -> str:
    return os.path.join("/app/models/versions", symbol.upper(), timeframe, model_type.lower(), version)


def register_candidate(record: Dict[str, Any]) -> Dict[str, Any]:
    registry = _read()
    key = model_key(record["symbol"], record["timeframe"], record["model_type"])
    models = registry.setdefault("models", {})
    entry = models.setdefault(key, {"active_version": None, "versions": []})
    entry["versions"] = [item for item in entry["versions"] if item["version"] != record["version"]]
    entry["versions"].append(record)
    _write(registry)
    return record


def approve_version(symbol: str, timeframe: str, model_type: str, version: str) -> Dict[str, Any]:
    registry = _read()
    key = model_key(symbol, timeframe, model_type)
    entry = registry.setdefault("models", {}).get(key)
    if not entry:
        raise FileNotFoundError("No registered models for this combination")
    selected = next((item for item in entry["versions"] if item["version"] == version), None)
    if selected is None:
        raise FileNotFoundError(f"Model version not found: {version}")
    entry["active_version"] = version
    selected["status"] = "approved"
    for item in entry["versions"]:
        if item["version"] != version and item.get("status") == "approved":
            item["status"] = "superseded"
    _write(registry)
    return selected


def get_active(symbol: str, timeframe: str, model_type: str) -> Optional[Dict[str, Any]]:
    entry = _read().get("models", {}).get(model_key(symbol, timeframe, model_type))
    if not entry or not entry.get("active_version"):
        return None
    return next((item for item in entry["versions"] if item["version"] == entry["active_version"]), None)


def list_versions(symbol: Optional[str] = None, timeframe: Optional[str] = None, model_type: Optional[str] = None) -> list:
    models = _read().get("models", {})
    records = []
    for key, entry in models.items():
        key_symbol, key_timeframe, key_model_type = key.split("|", 2)
        if symbol and key_symbol != symbol.upper():
            continue
        if timeframe and key_timeframe != timeframe:
            continue
        if model_type and key_model_type != model_type.lower():
            continue
        for record in entry["versions"]:
            records.append({**record, "active": record["version"] == entry.get("active_version")})
    return sorted(records, key=lambda item: item["created_at"], reverse=True)

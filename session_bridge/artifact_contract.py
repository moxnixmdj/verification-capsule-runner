from __future__ import annotations

from typing import Any


def normalize_artifact_contract(entries: list[Any]):
    normalized = []
    unsupported = []
    for entry in entries:
        if isinstance(entry, str):
            normalized.append({"source": entry, "destination": entry, "service": None})
            continue
        if not isinstance(entry, dict):
            unsupported.append({"entry": entry, "reason": "INVALID_ARTIFACT_ENTRY_TYPE"})
            continue
        source = entry.get("source")
        destination = entry.get("destination") or source
        service = entry.get("service")
        exclude = entry.get("exclude")
        if not isinstance(source, str) or not source:
            unsupported.append({"entry": entry, "reason": "ARTIFACT_SOURCE_MISSING_OR_INVALID"})
            continue
        if not isinstance(destination, str) or not destination:
            unsupported.append({"entry": entry, "reason": "ARTIFACT_DESTINATION_INVALID"})
            continue
        if service:
            unsupported.append({
                "source": source,
                "destination": destination,
                "service": service,
                "reason": "PER_SERVICE_ARTIFACT_REQUIRES_MULTI_SERVICE_COLLECTOR",
            })
            continue
        if exclude:
            unsupported.append({
                "source": source,
                "destination": destination,
                "exclude": exclude,
                "reason": "ARTIFACT_EXCLUDE_FILTER_UNSUPPORTED",
            })
            continue
        normalized.append({"source": source, "destination": destination, "service": None})
    return normalized, unsupported

"""
Shared evidence-reference validation for debate agents.

The agents may only cite tools that actually produced ledger results. Invalid or
missing refs are not repaired with guesswork; the affected claim is dropped and
the returned payload records what was removed for auditability.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple


def _tool_names(ledger) -> set:
    return {r.tool_name for r in getattr(ledger, "results", []) if getattr(r, "tool_name", None)}


def _canonical_ref(ref: Any, valid: set) -> Optional[str]:
    if not isinstance(ref, str):
        return None
    raw = ref.strip()
    if raw in valid:
        return raw
    for sep in (":", ".", "["):
        base = raw.split(sep, 1)[0].strip()
        if base in valid:
            return base
    return None


def validate_claim_refs(
    payload: Dict[str, Any],
    ledger,
    list_specs: Iterable[Tuple[str, str]],
) -> Dict[str, Any]:
    """Validate structured claim lists in an agent payload.

    `list_specs` is an iterable of `(list_key, claim_text_key)` pairs, e.g.
    `("key_drivers", "claim")`. Items with no resolvable refs are dropped.
    Items with mixed valid/invalid refs are kept with only canonical valid refs.
    """
    if not isinstance(payload, dict):
        return payload

    valid = _tool_names(ledger)
    invalid_refs: List[Dict[str, Any]] = []
    dropped_claims: List[Dict[str, Any]] = []

    for list_key, text_key in list_specs:
        items = payload.get(list_key)
        if not isinstance(items, list):
            continue

        kept = []
        for item in items:
            if not isinstance(item, dict):
                dropped_claims.append({"list": list_key, "claim": str(item), "reason": "malformed_claim"})
                continue

            refs = item.get("evidence_refs")
            if not isinstance(refs, list):
                refs = []

            canonical = []
            bad = []
            for ref in refs:
                resolved = _canonical_ref(ref, valid)
                if resolved:
                    if resolved not in canonical:
                        canonical.append(resolved)
                else:
                    bad.append(ref)

            if bad:
                invalid_refs.append({
                    "list": list_key,
                    "claim": item.get(text_key, ""),
                    "invalid_refs": bad,
                })

            if not canonical:
                dropped_claims.append({
                    "list": list_key,
                    "claim": item.get(text_key, ""),
                    "reason": "missing_valid_evidence_ref",
                })
                continue

            item["evidence_refs"] = canonical
            kept.append(item)

        payload[list_key] = kept

    if invalid_refs:
        payload["invalid_evidence_refs"] = invalid_refs
    if dropped_claims:
        payload["dropped_uncited_claims"] = dropped_claims
    return payload

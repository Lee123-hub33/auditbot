from fastapi import APIRouter, Depends, HTTPException
from collections import Counter

# Standard imports at the top are better for pytest collection
from app.auth.rbac import require_viewer
from app.utils.audit_rules import AUDIT_RULES

router = APIRouter(prefix="/api/v1/rules", tags=["Audit Rules"])

SEVERITY_MAP = {0: "INFO", 1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}

@router.get("", dependencies=[Depends(require_viewer)])
async def list_rules():
    """List all active audit rules."""
    return {
        "total": len(AUDIT_RULES),
        "rules": [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "description": r.description,
                "severity": SEVERITY_MAP.get(r.severity, "UNKNOWN"),
                "severity_level": r.severity,
                "category": r.category,
            }
            for r in AUDIT_RULES
        ]
    }

@router.get("/categories", dependencies=[Depends(require_viewer)])
async def list_categories():
    """List all rule categories and how many rules are in each."""
    counts = Counter(r.category for r in AUDIT_RULES)
    return {
        "categories": [
            {"category": cat, "rule_count": count}
            for cat, count in sorted(counts.items())
        ]
    }

@router.get("/{rule_id}", dependencies=[Depends(require_viewer)])
async def get_rule(rule_id: str):
    """Get full details of a specific rule by ID."""
    rule = next((r for r in AUDIT_RULES if r.rule_id == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return {
        "rule_id": rule.rule_id,
        "name": rule.name,
        "description": rule.description,
        "prompt_instruction": rule.prompt_instruction,
        "severity": SEVERITY_MAP.get(rule.severity, "UNKNOWN"),
        "severity_level": rule.severity,
        "category": rule.category,
    }

@router.get("/category/{category}", dependencies=[Depends(require_viewer)])
async def get_rules_by_category(category: str):
    """Get all rules in a specific category."""
    rules = [r for r in AUDIT_RULES if r.category.lower() == category.lower()]
    if not rules:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
    return {
        "category": category,
        "total": len(rules),
        "rules": [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "description": r.description,
                "severity": SEVERITY_MAP.get(r.severity, "UNKNOWN"),
                "severity_level": r.severity,
            }
            for r in rules
        ]
    }
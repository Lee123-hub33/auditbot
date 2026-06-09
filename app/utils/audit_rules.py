"""
Audit Rules Engine.

Each rule is a dataclass describing what to check.
Rules are evaluated by the AI pipeline in tasks.py.

Adding a new rule: create a new AuditRule entry in AUDIT_RULES.
No other code changes needed — the pipeline iterates all rules automatically.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AuditRule:
    rule_id: str          # e.g. "GDPR-001"
    name: str             # human-readable label
    description: str      # what this rule checks
    prompt_instruction: str  # injected into the AI prompt
    severity: int         # 0=info 1=low 2=medium 3=high 4=critical
    category: str         # grouping label for reports


# ── Rule definitions ──────────────────────────────────────────────────────────
# Extend this list freely. Each rule produces one AuditLog entry per document.

AUDIT_RULES: list[AuditRule] = [

    # ── GDPR / Privacy ────────────────────────────────────────────────────────
    AuditRule(
        rule_id="PRIVACY-001",
        name="Personal Data Exposure",
        description="Check for names, email addresses, phone numbers, or national IDs in the document.",
        prompt_instruction=(
            "Identify any personally identifiable information (PII) present, including: "
            "full names, email addresses, phone numbers, passport or national ID numbers, "
            "physical addresses. List every instance found."
        ),
        severity=4,
        category="Privacy",
    ),
    AuditRule(
        rule_id="PRIVACY-002",
        name="Data Retention Policy Reference",
        description="Verify the document references or complies with a data retention policy.",
        prompt_instruction=(
            "Does the document mention a data retention period or reference a data retention policy? "
            "If it handles personal data, is a retention period stated?"
        ),
        severity=2,
        category="Privacy",
    ),

    # ── Security ──────────────────────────────────────────────────────────────
    AuditRule(
        rule_id="SEC-001",
        name="Credentials or Secrets Exposure",
        description="Detect hardcoded passwords, API keys, tokens, or connection strings.",
        prompt_instruction=(
            "Scan the document for any hardcoded credentials, including: passwords, API keys, "
            "secret tokens, database connection strings, private keys, or bearer tokens. "
            "Flag any found, even if they appear to be examples or placeholders."
        ),
        severity=4,
        category="Security",
    ),
    AuditRule(
        rule_id="SEC-002",
        name="Sensitive System Information",
        description="Detect internal IP addresses, server names, or internal URLs.",
        prompt_instruction=(
            "Does the document contain internal network information such as private IP addresses "
            "(10.x, 172.16-31.x, 192.168.x), internal hostnames, internal URLs, or system paths "
            "that could expose infrastructure details?"
        ),
        severity=3,
        category="Security",
    ),

    # ── Compliance ────────────────────────────────────────────────────────────
    AuditRule(
        rule_id="COMP-001",
        name="Legal Disclaimer Presence",
        description="Check that the document includes required legal disclaimers if applicable.",
        prompt_instruction=(
            "Does the document include a legal disclaimer, confidentiality notice, or copyright notice "
            "where one would be expected? Is there a 'confidential' or 'proprietary' marking if the "
            "content appears sensitive?"
        ),
        severity=1,
        category="Compliance",
    ),
    AuditRule(
        rule_id="COMP-002",
        name="Financial Data Handling",
        description="Check for unprotected financial account numbers, card numbers, or financial identifiers.",
        prompt_instruction=(
            "Does the document contain any financial account numbers, credit/debit card numbers, "
            "bank routing numbers, or tax identification numbers (e.g. SSN, EIN) without appropriate "
            "masking or redaction?"
        ),
        severity=4,
        category="Compliance",
    ),

    # ── Content Quality ───────────────────────────────────────────────────────
    AuditRule(
        rule_id="QUAL-001",
        name="Document Completeness",
        description="Assess whether the document appears complete and coherent.",
        prompt_instruction=(
            "Does the document appear complete? Are there obvious signs of truncation, "
            "missing sections, placeholder text (e.g. 'Lorem ipsum', 'TBD', 'DRAFT'), "
            "or unresolved references?"
        ),
        severity=1,
        category="Quality",
    ),
    AuditRule(
        rule_id="QUAL-002",
        name="Profanity or Inappropriate Language",
        description="Flag profanity or inappropriate language not suitable for professional documents.",
        prompt_instruction=(
            "Does the document contain profanity, hate speech, discriminatory language, "
            "or content inappropriate for a professional or business context?"
        ),
        severity=2,
        category="Quality",
    ),
]

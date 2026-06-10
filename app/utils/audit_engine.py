# app/utils/audit_engine.py
import re
import json
import structlog
from typing import List, Dict, Any
from app.models import AuditResult

log = structlog.get_logger()


def check_pii_presence(text: str) -> Dict[str, Any]:
    findings = []
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", text):
        findings.append("Possible SSN detected (format: XXX-XX-XXXX)")
    if re.search(
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b",
        text.replace(" ", "").replace("-", ""),
    ):
        findings.append("Possible credit card number detected")
    emails = re.findall(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b", text)
    if len(emails) > 5:
        findings.append(f"Large number of email addresses found ({len(emails)})")
    if findings:
        return {
            "rule": "PII Detection",
            "result": AuditResult.VIOLATION,
            "findings": "PII concerns: " + "; ".join(findings),
            "severity": "HIGH",
        }
    return {
        "rule": "PII Detection",
        "result": AuditResult.PASSED,
        "findings": "No obvious PII patterns detected",
        "severity": "LOW",
    }


def check_document_length(text: str) -> Dict[str, Any]:
    word_count = len(text.split())
    if word_count < 10:
        return {
            "rule": "Document Length",
            "result": AuditResult.WARNING,
            "findings": f"Document contains only {word_count} words — may be incomplete",
            "severity": "MEDIUM",
        }
    return {
        "rule": "Document Length",
        "result": AuditResult.PASSED,
        "findings": f"Document contains {word_count} words",
        "severity": "LOW",
    }


def check_prohibited_terms(text: str) -> Dict[str, Any]:
    prohibited = [
        "confidential - do not distribute",
        "draft - not for release",
        "internal use only",
    ]
    text_lower = text.lower()
    found = [term for term in prohibited if term in text_lower]
    if found:
        return {
            "rule": "Prohibited Terms",
            "result": AuditResult.WARNING,
            "findings": f"Document contains restricted markers: {found}",
            "severity": "MEDIUM",
        }
    return {
        "rule": "Prohibited Terms",
        "result": AuditResult.PASSED,
        "findings": "No prohibited terms detected",
        "severity": "LOW",
    }


def check_url_presence(text: str) -> Dict[str, Any]:
    urls = re.findall(r"https?://[^\s]+", text)
    if len(urls) > 10:
        return {
            "rule": "External URL Count",
            "result": AuditResult.WARNING,
            "findings": f"Document contains {len(urls)} external URLs",
            "severity": "LOW",
        }
    return {
        "rule": "External URL Count",
        "result": AuditResult.PASSED,
        "findings": f"URL count within acceptable range ({len(urls)} found)",
        "severity": "LOW",
    }


def check_sensitive_keywords(text: str) -> Dict[str, Any]:
    sensitive = ["password", "secret", "api_key", "private key", "credentials", "token"]
    text_lower = text.lower()
    found = [kw for kw in sensitive if kw in text_lower]
    if found:
        return {
            "rule": "Sensitive Keywords",
            "result": AuditResult.VIOLATION,
            "findings": f"Sensitive keywords found in document: {found}",
            "severity": "HIGH",
        }
    return {
        "rule": "Sensitive Keywords",
        "result": AuditResult.PASSED,
        "findings": "No sensitive keywords detected",
        "severity": "LOW",
    }


def run_gemini_audit(text: str, gemini_api_key: str) -> List[Dict[str, Any]]:
    try:
        import google.generativeai as genai

        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        truncated = text[:8000]
        if len(text) > 8000:
            truncated += "\n\n[Document truncated for analysis]"

        prompt = f"""You are a professional document auditor. Analyse the following document against these rules:

1. COMPLIANCE_LANGUAGE: Does the document use appropriate compliance and legal language?
2. COMPLETENESS: Does the document appear complete with all required sections?
3. CLARITY: Is the document clear and unambiguous?
4. RISK_INDICATORS: Are there statements indicating legal, financial, or operational risk?
5. DATA_HANDLING: Does the document follow good data handling and privacy practices?

Respond ONLY with a JSON array. Each item must have exactly:
- "rule": rule name from the list above
- "result": one of "PASSED", "VIOLATION", or "WARNING"
- "findings": one concise sentence explanation
- "severity": one of "LOW", "MEDIUM", "HIGH", or "CRITICAL"

Respond with ONLY the JSON array, no markdown, no extra text.

Document:
---
{truncated}
---"""

        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        results = json.loads(raw)
        validated = []
        for r in results:
            if all(k in r for k in ("rule", "result", "findings", "severity")):
                result_val = r["result"].upper()
                if result_val not in ("PASSED", "VIOLATION", "WARNING"):
                    result_val = "WARNING"
                validated.append(
                    {
                        "rule": str(r["rule"])[:255],
                        "result": AuditResult(result_val),
                        "findings": str(r["findings"])[:2000],
                        "severity": str(r["severity"]).upper(),
                    }
                )
        log.info("gemini_audit_complete", rules_returned=len(validated))
        return validated

    except Exception as e:
        log.error("gemini_audit_failed", error=str(e))
        return [
            {
                "rule": "AI Analysis",
                "result": AuditResult.WARNING,
                "findings": f"AI analysis could not be completed: {str(e)[:200]}",
                "severity": "LOW",
            }
        ]


def run_all_rules(text: str, gemini_api_key: str) -> List[Dict[str, Any]]:
    results = []
    local_rules = [
        check_pii_presence,
        check_document_length,
        check_prohibited_terms,
        check_url_presence,
        check_sensitive_keywords,
    ]
    for rule_fn in local_rules:
        try:
            results.append(rule_fn(text))
        except Exception as e:
            log.error("local_rule_failed", rule=rule_fn.__name__, error=str(e))

    ai_results = run_gemini_audit(text, gemini_api_key)
    results.extend(ai_results)
    return results

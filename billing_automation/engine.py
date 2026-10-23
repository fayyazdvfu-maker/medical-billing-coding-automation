"""Structural checks and explicitly configured procedure/payer rules.

No payer coverage or medical-necessity assumptions are built in.
"""
from dataclasses import asdict, dataclass
from datetime import date


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    message: str
    line: int | None = None
    source: str | None = None

    def to_dict(self):
        return asdict(self)


def _date(value):
    if not isinstance(value, str):
        raise ValueError("date must be an ISO YYYY-MM-DD string")
    return date.fromisoformat(value)


def validate(claim, rules=(), catalog=None):
    """Return findings without mutating the claim.

    Catalog keys are code-set names; entries are keyed by code and may specify
    reportable, valid_from, and valid_to. Both date bounds are inclusive.
    Configured rule types: required_modifier and required_field.
    Missing payer/date context never establishes a payer-specific match.
    """
    if not isinstance(claim, dict):
        return [Finding("CLAIM_OBJECT", "error", "Claim must be a JSON object.")]
    findings = []
    try:
        dos = _date(claim.get("date_of_service"))
    except (ValueError, TypeError):
        dos = None
        findings.append(Finding("SERVICE_DATE", "error", "A valid date_of_service is required."))
    payer = claim.get("payer")
    if not isinstance(payer, str) or not payer.strip():
        payer = None
        findings.append(Finding("PAYER_REQUIRED", "error", "A payer identifier is required."))
    diagnoses = claim.get("diagnoses", [])
    if not isinstance(diagnoses, list) or not diagnoses or any(not isinstance(d, str) or not d.strip() for d in diagnoses):
        findings.append(Finding("DIAGNOSES_REQUIRED", "error", "Provide a nonempty list of diagnosis codes."))
        diagnoses = []
    lines = claim.get("lines")
    if not isinstance(lines, list) or not lines:
        return findings + [Finding("LINES_REQUIRED", "error", "Provide at least one service line.")]

    def check_code(code_set, code, line=None):
        if catalog is None:
            return
        entries = catalog.get(code_set)
        if entries is None:
            findings.append(Finding("CATALOG_UNAVAILABLE", "review", f"No {code_set} catalog supplied; code not verified.", line))
            return
        entry = entries.get(code)
        if entry is None:
            findings.append(Finding("CODE_NOT_IN_CATALOG", "review", f"{code_set} {code} is absent from the supplied catalog.", line))
            return
        if entry.get("reportable") is False:
            findings.append(Finding("CODE_NOT_REPORTABLE", "error", f"The supplied catalog marks {code} as not reportable.", line, entry.get("source")))
        if dos is not None:
            try:
                start = _date(entry["valid_from"]) if entry.get("valid_from") else date.min
                end = _date(entry["valid_to"]) if entry.get("valid_to") else date.max
                if start > end:
                    raise ValueError("reversed catalog date range")
                if not start <= dos <= end:
                    findings.append(Finding("CODE_DATE_RANGE", "error", f"{code} is outside the supplied catalog's effective dates.", line, entry.get("source")))
            except (ValueError, TypeError):
                findings.append(Finding("CATALOG_DATE_INVALID", "review", f"Invalid catalog dates for {code}; date validity not verified.", line))

    if catalog is None:
        findings.append(Finding("CATALOG_NOT_SUPPLIED", "review", "No catalog supplied; code validity and reportability were not verified."))
    for diagnosis in diagnoses:
        check_code("ICD-10-CM", diagnosis)
    for number, line in enumerate(lines, 1):
        if not isinstance(line, dict):
            findings.append(Finding("LINE_OBJECT", "error", "Service line must be an object.", number))
            continue
        code = line.get("procedure_code")
        code_set = line.get("code_set")
        if not isinstance(code, str) or not code.strip():
            findings.append(Finding("PROCEDURE_REQUIRED", "error", "A procedure_code is required.", number))
        elif code_set not in ("CPT", "HCPCS"):
            findings.append(Finding("CODE_SET_REQUIRED", "error", "code_set must be CPT or HCPCS.", number))
        else:
            check_code(code_set, code, number)
        modifiers = line.get("modifiers", [])
        if not isinstance(modifiers, list) or any(not isinstance(m, str) or not m.strip() for m in modifiers):
            findings.append(Finding("MODIFIERS_FORMAT", "error", "Modifiers must be a list of nonempty strings.", number))
            modifiers = []
        if len(modifiers) != len(set(modifiers)):
            findings.append(Finding("DUPLICATE_MODIFIER", "error", "Duplicate modifiers on the same service line.", number))
        pointers = line.get("diagnosis_pointers", [])
        if not isinstance(pointers, list) or not pointers or any(type(p) is not int or not 1 <= p <= len(diagnoses) for p in pointers):
            findings.append(Finding("DIAGNOSIS_POINTER", "error", "Use one-based diagnosis pointers that reference the claim diagnosis list.", number))
        for rule in rules:
            rule_id = rule.get("id", "UNNAMED_RULE")
            source = rule.get("source")
            required_keys = ("id", "type", "procedure_codes", "payer", "effective_from", "effective_to", "source")
            bad = any(k not in rule for k in required_keys) or not isinstance(source, str) or not source.strip()
            bad = bad or rule.get("type") not in ("required_modifier", "required_field")
            bad = bad or not isinstance(rule.get("procedure_codes"), list) or not rule.get("procedure_codes")
            bad = bad or rule.get("severity", "review") not in ("error", "review", "warning")
            key = "modifier" if rule.get("type") == "required_modifier" else "field"
            bad = bad or not isinstance(rule.get(key), str) or not rule.get(key, "").strip()
            try:
                start, end = _date(rule.get("effective_from")), _date(rule.get("effective_to"))
                bad = bad or start > end
            except (ValueError, TypeError):
                bad = True
            if bad:
                findings.append(Finding(str(rule_id), "review", "Invalid rule configuration; rule was not applied.", number))
                continue
            if dos is None or not start <= dos <= end or code not in rule["procedure_codes"]:
                continue
            if rule["payer"] != "*" and rule["payer"] != payer:
                continue
            missing = rule[key] not in modifiers if key == "modifier" else line.get(rule[key]) in (None, "", [])
            if missing:
                findings.append(Finding(rule_id, rule.get("severity", "review"), rule.get("message", f"Required {key}: {rule[key]}"), number, source))
    return findings

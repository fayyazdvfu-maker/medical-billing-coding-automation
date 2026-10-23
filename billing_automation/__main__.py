import argparse
import json
import sys
from pathlib import Path
from .engine import validate


def main():
    parser = argparse.ArgumentParser(description="Validate a JSON claim against supplied configuration.")
    parser.add_argument("claim", type=Path)
    parser.add_argument("--rules", type=Path)
    parser.add_argument("--catalog", type=Path)
    args = parser.parse_args()
    try:
        claim = json.loads(args.claim.read_text(encoding="utf-8"))
        rules = json.loads(args.rules.read_text(encoding="utf-8")) if args.rules else []
        catalog = json.loads(args.catalog.read_text(encoding="utf-8")) if args.catalog else None
        if not isinstance(rules, list) or any(not isinstance(r, dict) for r in rules):
            raise ValueError("Rules file must contain a list of objects.")
        if catalog is not None and (not isinstance(catalog, dict) or any(not isinstance(v, dict) or any(not isinstance(e, dict) for e in v.values()) for v in catalog.values())):
            raise ValueError("Catalog must map code sets to code-entry objects.")
        findings = validate(claim, rules, catalog)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"findings": [f.to_dict() for f in findings]}, indent=2))
    return 1 if any(f.severity == "error" for f in findings) else 2 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

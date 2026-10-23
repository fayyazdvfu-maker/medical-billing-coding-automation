# Medical Billing and Coding Automation

An early-stage Python project for configurable, source-traceable claim validation.
The initial implementation runs offline and uses only the Python standard library.

## Implemented

- Validate service dates, payer identifiers, procedure fields and diagnosis pointers.
- Detect duplicate modifiers on a service line.
- Check code presence, reportability and inclusive effective dates against a supplied catalog.
- Apply explicitly configured payer/procedure rules for required modifiers or fields.
- Return structured findings with rule IDs, severity, line numbers and source references.
- Flag missing catalogs and invalid configurations for review.

No medical-necessity crosswalk, payer policy set, CPT descriptors or patient records
are bundled. The example codes, payer and modifier are deliberately fictional.
An empty findings list means the configured checks passed; it does not establish
coverage, correct coding, regulatory compliance or payment approval.

## Quick start

Requires Python 3.10 or newer. From the repository directory:

```bash
python -m billing_automation examples/claim.json --rules examples/rules.json --catalog examples/catalog.json
python -m unittest discover -s tests -v
```

Optional installation:

```bash
python -m pip install -e .
billing-validate examples/claim.json --rules examples/rules.json --catalog examples/catalog.json
```

The supplied example produces `{"findings": []}`. Remove `DEMO_MOD` from the
example claim to see a review finding. Exit codes: 0 for no findings, 1 for
validation errors, and 2 for review/warning findings or invalid CLI input.

## Configuration and data

See [docs/rules.md](docs/rules.md) for the JSON contract. Supply catalog data you
are authorized to use and verify its release year and effective dates. The MIT
license covers this repository's original software, not third-party coding data.
Only use synthetic or appropriately de-identified examples in public contributions.
Do not commit real claims, patient information, credentials or restricted codebooks.

## Current scope and roadmap

This is a new starter project. No adoption, download or external-contribution
figures are claimed. Planned work includes catalog import adapters, rule-schema
versioning, more configuration diagnostics and an optional review interface.
Those planned features are not implemented yet.

Contributions should include a reproducible synthetic example, tests, and source
provenance for any proposed rule. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT; see [LICENSE](LICENSE).

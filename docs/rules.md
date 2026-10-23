# Rule and catalog contract

Claims contain `date_of_service` (ISO date), `payer`, a nonempty `diagnoses` list,
and a nonempty `lines` list. Each line supplies `code_set` (`CPT` or `HCPCS`),
`procedure_code`, `modifiers` and one-based integer `diagnosis_pointers`.
Booleans are not valid diagnosis pointers. Code-set labels identify configured
catalog namespaces; labels do not make a fictional or unknown code valid.

Each configured rule requires:

| Field | Meaning |
| --- | --- |
| id | Stable rule identifier |
| type | `required_modifier` or `required_field` |
| procedure_codes | Nonempty list of exact procedure identifiers |
| payer | Exact payer identifier, or `*` for an explicitly configured general rule |
| effective_from / effective_to | Inclusive ISO date boundaries |
| source | Provenance reference; a URL and policy/version identifier are recommended |
| modifier / field | Required value or service-line field, according to rule type |
| severity | Optional: `review` (default), `warning` or `error` |
| message | Optional explanation |

Rules do not override one another: every matching rule is evaluated. Authors
must resolve conflicting policies in configuration. No rule executes for an
unknown service date. Missing payer context does not match a specific payer.
The source is retained in findings; its presence does not verify its authority.

Catalog JSON maps code-set names to code-entry dictionaries. Supported entry
fields are `reportable` (boolean), `valid_from`, `valid_to`, and `source`.
Missing date bounds are unbounded; explicitly provide bounds for versioned data.
Unknown codes produce review findings, not a claim of universal invalidity.
Catalog/reportability checks do not determine coverage or clinical appropriateness.

This tool does not parse X12, query payers, contact clearinghouses, validate
CLIA certificates, implement NCCI edits, or submit claims. Any such integrations
require their own reviewed implementation and data permissions.

# Searchable PDF Evaluation

TenderGuard's uploaded-document workflow consumes one tender requirements PDF and at
least two supplier bid PDFs. The PDFs—not the existing synthetic JSON—are the evidence
used by this workflow.

## Safety and validation

The ingestion service:

- accepts `application/pdf` with a `.pdf` filename and PDF signature;
- defaults to a 10 MB file limit and 80-page limit;
- generates server-side workspace and document identifiers;
- stores originals under the configured runtime storage root;
- rejects encrypted PDFs, automatic actions, JavaScript, embedded files, malformed
  content, and PDFs with no searchable text;
- extracts text one page at a time with pypdf;
- stores SHA-256, page count, safe filename, extraction status, and short previews;
- never executes uploaded content or treats document text as model instructions.

Set `TENDERGUARD_DOCUMENT_STORAGE`, `TENDERGUARD_MAX_PDF_MB`, and
`TENDERGUARD_MAX_PDF_PAGES` to adjust deployment boundaries. Docker stores originals
and extracted JSON in the `tenderguard_documents` volume.

Image-only and scanned PDFs are rejected with a clear OCR-required message. OCR is not
implemented in this release; it is intentionally not simulated.

## Extracted and evaluated evidence

The deterministic Procurement MCP tool extracts labeled tender fields, mandatory
documents, eligibility criteria, technical specifications, financial requirements,
supplier-submitted evidence, submission dates, and prices. Every material check has a
document ID, filename, page number, and source quote.

Unknown or absent content is `MISSING_EVIDENCE`, `UNVERIFIED`, or
`REQUIRES_HUMAN_REVIEW`. TenderGuard never converts missing evidence into compliance.
Submission deadlines and bid timestamps are metadata only: timeliness is not assessed
and does not affect compliance, supplier risk, or review priority. Timestamp metadata
and its citations are excluded from AI synthesis. Portal acceptance is not inferred
from a PDF or from the presence of a workspace. Direct submitted-price ordering is explicitly not a
ranking or award recommendation. Historical price comparison remains disabled unless
a suitable comparable dataset is established.

The local Qwen model plans the LangGraph tool sequence and synthesizes the structured,
page-cited findings. Deterministic guards set attention priority when evidence is
missing/noncompliant and always preserve:

```text
status = AWAITING_HUMAN_REVIEW
human_committee_required = true
final_award_decision = null
```

## Synthetic evidence set

The committed `demo_documents/` directory contains:

- `tender_requirements_synthetic.pdf`
- `alpha_supplier_bid_synthetic.pdf`
- `beta_supplier_bid_synthetic.pdf`

Every PDF is visibly marked as synthetic demonstration data. Alpha contains all
required evidence. Beta intentionally omits tax-clearance evidence,
contains partial delivery/warranty responses, and has an internal
entity-name inconsistency. These are synthetic review flags, not accusations.

The tender deadline is 15 December 2026 at 12:00 EAT. The Alpha and Beta PDF
submission metadata is 14 December 2026 at 10:15 and 09:30 EAT respectively.

Regenerate the deterministic files with:

```powershell
.\.venv\Scripts\python.exe scripts\generate_synthetic_pdfs.py
```

## CLI evaluation and authorized report

```powershell
.\.venv\Scripts\python.exe -m app.agent.run_documents `
  --tender demo_documents\tender_requirements_synthetic.pdf `
  --bid demo_documents\alpha_supplier_bid_synthetic.pdf `
  --bid demo_documents\beta_supplier_bid_synthetic.pdf
```

Copy the returned `workspace_id`, review the evidence, then authorize only draft report
generation through the separate CLI gate:

```powershell
.\.venv\Scripts\python.exe -m app.agent.approve_documents `
  --workspace EVL-REPLACE_WITH_WORKSPACE_ID `
  --approved-by "Named Demo Reviewer"
```

The report is marked `DRAFT FOR HUMAN PROCUREMENT COMMITTEE REVIEW`; it contains no
award decision.

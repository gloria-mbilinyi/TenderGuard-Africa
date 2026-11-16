import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TENDER_DATA_DIR = PROJECT_ROOT / "data" / "ocds"
BID_DATA_DIR = PROJECT_ROOT / "data" / "synthetic_bids"


class CatalogSelectionError(ValueError):
    """Raised when a requested synthetic tender or bid is not in the catalog."""


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_catalog() -> dict[str, list[dict[str, Any]]]:
    bids = [_read_json(path) for path in sorted(BID_DATA_DIR.glob("*.json"))]
    tenders: list[dict[str, Any]] = []

    for tender_path in sorted(TENDER_DATA_DIR.glob("*.json")):
        record = _read_json(tender_path)
        tender = record.get("tender")
        if not isinstance(tender, dict) or not tender.get("id"):
            continue

        value = tender.get("value") or {}
        entity = tender.get("procuringEntity") or {}
        tender_bids = []
        for bid in bids:
            if bid.get("tender_id") != tender.get("id"):
                continue
            supplier = bid.get("supplier") or {}
            price = bid.get("price") or {}
            tender_bids.append(
                {
                    "bid_id": bid.get("bid_id"),
                    "supplier_name": supplier.get("name"),
                    "supplier_identifier": supplier.get("identifier"),
                    "amount": price.get("amount"),
                    "currency": price.get("currency"),
                    "submitted_at": bid.get("submitted_at"),
                    "submitted_document_codes": [
                        document.get("code")
                        for document in bid.get("documents", [])
                        if document.get("code")
                    ],
                    "synthetic": True,
                }
            )

        tenders.append(
            {
                "tender_id": tender.get("id"),
                "ocid": record.get("ocid"),
                "title": tender.get("title"),
                "description": tender.get("description"),
                "status": tender.get("status"),
                "procurement_method": tender.get("procurementMethod"),
                "submission_deadline": tender.get("submissionDeadline"),
                "amount": value.get("amount"),
                "currency": value.get("currency"),
                "procuring_entity": entity.get("name"),
                "required_documents": [
                    {"code": item.get("code"), "label": item.get("name")}
                    for item in tender.get("requiredDocuments", [])
                ],
                "eligibility_requirements": [
                    {"code": item.get("code"), "label": item.get("description")}
                    for item in tender.get("eligibilityRequirements", [])
                ],
                "bids": tender_bids,
                "source_file": tender_path.relative_to(PROJECT_ROOT).as_posix(),
                "synthetic": True,
            }
        )

    return {"tenders": tenders}


def validate_catalog_selection(tender_id: str, bid_id: str) -> None:
    catalog = load_catalog()
    tender = next(
        (item for item in catalog["tenders"] if item["tender_id"] == tender_id),
        None,
    )
    if tender is None:
        raise CatalogSelectionError(f"Tender '{tender_id}' is not available in the demo catalog.")
    if not any(bid["bid_id"] == bid_id for bid in tender["bids"]):
        raise CatalogSelectionError(
            f"Bid '{bid_id}' is not available for tender '{tender_id}'."
        )

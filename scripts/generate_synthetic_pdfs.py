"""Generate deterministic searchable PDFs for the TenderGuard live demonstration."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "demo_documents"
BANNER = "SYNTHETIC DEMONSTRATION DATA — NOT A REAL PROCUREMENT"


def _pdf_string(value: str) -> str:
    encoded = value.encode("cp1252", errors="replace")
    escaped = []
    for byte in encoded:
        if byte in {40, 41, 92}:
            escaped.append(f"\\{chr(byte)}")
        elif 32 <= byte <= 126:
            escaped.append(chr(byte))
        else:
            escaped.append(f"\\{byte:03o}")
    return "".join(escaped)


def _write_pdf(path: Path, title: str, lines: list[str]) -> None:
    page_capacity = 46
    page_chunks = [lines[index : index + page_capacity] for index in range(0, len(lines), page_capacity)]
    objects: list[bytes] = [b""]
    page_refs = " ".join(f"{4 + index * 2} 0 R" for index in range(len(page_chunks)))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(
        f"<< /Type /Pages /Kids [{page_refs}] /Count {len(page_chunks)} >>".encode("ascii")
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")

    for page_number, chunk in enumerate(page_chunks, start=1):
        page_object = 4 + (page_number - 1) * 2
        content_object = page_object + 1
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_object} 0 R >>"
            ).encode("ascii")
        )
        display_lines = [BANNER, title, f"Page {page_number} of {len(page_chunks)}", "", *chunk]
        commands = ["BT", "/F1 9.5 Tf", "48 758 Td", "13 TL"]
        for line in display_lines:
            commands.append(f"({_pdf_string(line)}) Tj")
            commands.append("T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("ascii")
        objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects[1:], start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects)}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    path.write_bytes(output)


TENDER_LINES = [
    "PROCUREMENT NOTICE AND TENDER REQUIREMENTS",
    "Tender ID: TG-PDF-DEMO-001",
    "Procurement Title: Supply and Installation of ICT Equipment",
    "Procuring Entity: East Africa Digital Services Agency (Synthetic)",
    "Tender Currency: TZS",
    "Submission Deadline: 2026-12-15 12:00 EAT",
    "Procurement Method: Open Competitive Tender - Synthetic Demonstration",
    "Scope: 40 business laptops, 10 desktop workstations, networking, installation and training.",
    "",
    "MANDATORY REQUIRED DOCUMENTS",
    "- REQ-BID-FORM | Signed and completed bid form",
    "- REQ-BUSINESS-LICENSE | Valid business licence",
    "- REQ-TAX-CLEARANCE | Valid tax clearance certificate",
    "- REQ-MANUFACTURER-AUTH | Manufacturer authorization letter",
    "",
    "MANDATORY ELIGIBILITY CRITERIA",
    "- ELIG-REGISTRATION | Supplier must be legally registered",
    "- ELIG-TAX | Supplier must provide evidence of current tax compliance",
    "- ELIG-EXPERIENCE | At least three years of comparable ICT supply experience",
    "",
    "TECHNICAL SPECIFICATIONS",
    "- TECH-LAPTOP | 40 laptops, minimum Core i5, 16 GB RAM, 512 GB SSD",
    "- TECH-DESKTOP | 10 desktops, minimum Core i5, 16 GB RAM, 1 TB SSD",
    "- TECH-DELIVERY | Delivery and installation within 30 calendar days",
    "- TECH-WARRANTY | Minimum three-year manufacturer-backed warranty",
    "- TECH-TRAINING | On-site user and administrator training",
    "",
    "FINANCIAL REQUIREMENTS",
    "- FIN-PRICE | Total price must include taxes, delivery, installation and training",
    "- FIN-VALIDITY | Bid price must remain valid for 90 days",
    "",
    "EVALUATION CRITERIA",
    "- CRIT-01 | Mandatory document and eligibility evidence review",
    "- CRIT-02 | Technical conformance review with human assessment",
    "- CRIT-03 | Direct comparison of verified common-currency submitted prices",
    "- CRIT-04 | Human procurement committee review and final decision",
    "",
    "GOVERNANCE NOTICE",
    "TenderGuard Africa may prepare evidence and comparisons only.",
    "No automated system may award, reject, disqualify or select a supplier.",
]

ALPHA_LINES = [
    "SUPPLIER BID SUBMISSION",
    "Bid Reference: BID-PDF-ALPHA-001",
    "Tender ID: TG-PDF-DEMO-001",
    "Supplier Name: Alpha Technologies Ltd",
    "Registered Entity Name: Alpha Technologies Ltd",
    "Supplier Identifier: SYNTH-ALPHA-001",
    "Submission Date: 2026-12-14 10:15 EAT",
    "Bid Price: TZS 42,000,000",
    "Bid Validity: 90 days",
    "",
    "SUBMITTED DOCUMENTS",
    "- REQ-BID-FORM | Signed bid form | INCLUDED",
    "- REQ-BUSINESS-LICENSE | Business licence BL-SYNTH-1001 | INCLUDED",
    "- REQ-TAX-CLEARANCE | Tax clearance TC-SYNTH-1001 | INCLUDED",
    "- REQ-MANUFACTURER-AUTH | Manufacturer authorization MA-SYNTH-1001 | INCLUDED",
    "",
    "ELIGIBILITY EVIDENCE",
    "- ELIG-REGISTRATION | MET | Synthetic registration certificate attached",
    "- ELIG-TAX | MET | Synthetic current tax clearance attached",
    "- ELIG-EXPERIENCE | MET | Four years comparable ICT supply experience",
    "",
    "TECHNICAL RESPONSE",
    "- TECH-LAPTOP | COMPLIES | 40 Core i5 laptops, 16 GB RAM, 512 GB SSD",
    "- TECH-DESKTOP | COMPLIES | 10 Core i5 desktops, 16 GB RAM, 1 TB SSD",
    "- TECH-DELIVERY | COMPLIES | Delivery and installation in 25 calendar days",
    "- TECH-WARRANTY | COMPLIES | Three-year manufacturer-backed warranty",
    "- TECH-TRAINING | COMPLIES | Two on-site training sessions included",
    "",
    "FINANCIAL OFFER",
    "- FIN-PRICE | TZS 42,000,000 inclusive of taxes, delivery, installation and training",
    "- FIN-VALIDITY | Price valid for 90 days",
    "",
    "SUPPLIER DECLARATIONS",
    "All information is synthetic demonstration data and must not be used for procurement.",
    "Final evaluation and any procurement decision remain with an authorised human committee.",
]

BETA_LINES = [
    "SUPPLIER BID SUBMISSION",
    "Bid Reference: BID-PDF-BETA-001",
    "Tender ID: TG-PDF-DEMO-001",
    "Supplier Name: Beta Systems Ltd",
    "Registered Entity Name: Beta Systems Holdings Ltd",
    "Supplier Identifier: SYNTH-BETA-001",
    "Submission Date: 2026-12-14 09:30 EAT",
    "Bid Price: TZS 47,000,000",
    "Bid Validity: 60 days",
    "",
    "SUBMITTED DOCUMENTS",
    "- REQ-BID-FORM | Signed bid form | INCLUDED",
    "- REQ-BUSINESS-LICENSE | Business licence BL-SYNTH-2001 | INCLUDED",
    "- REQ-MANUFACTURER-AUTH | Manufacturer authorization MA-SYNTH-2001 | INCLUDED",
    "",
    "ELIGIBILITY EVIDENCE",
    "- ELIG-REGISTRATION | MET | Synthetic registration certificate attached",
    "- ELIG-TAX | NOT MET | No current tax clearance evidence included",
    "- ELIG-EXPERIENCE | MET | Five years general technology supply experience",
    "",
    "TECHNICAL RESPONSE",
    "- TECH-LAPTOP | COMPLIES | 40 Core i5 laptops, 16 GB RAM, 512 GB SSD",
    "- TECH-DESKTOP | COMPLIES | 10 Core i5 desktops, 16 GB RAM, 1 TB SSD",
    "- TECH-DELIVERY | PARTIAL | Delivery proposed within 45 calendar days",
    "- TECH-WARRANTY | PARTIAL | One-year supplier warranty stated",
    "- TECH-TRAINING | COMPLIES | One on-site training session included",
    "",
    "FINANCIAL OFFER",
    "- FIN-PRICE | TZS 47,000,000 inclusive of taxes and delivery",
    "- FIN-VALIDITY | Price valid for 60 days",
    "",
    "SUPPLIER DECLARATIONS",
    "The registered entity name differs from the trading name and requires clarification.",
    "All information is synthetic demonstration data and must not be used for procurement.",
    "Final evaluation and any procurement decision remain with an authorised human committee.",
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_pdf(
        OUTPUT_DIR / "tender_requirements_synthetic.pdf",
        "Tender Requirements — TG-PDF-DEMO-001",
        TENDER_LINES,
    )
    _write_pdf(
        OUTPUT_DIR / "alpha_supplier_bid_synthetic.pdf",
        "Alpha Technologies Ltd — Supplier Bid",
        ALPHA_LINES,
    )
    _write_pdf(
        OUTPUT_DIR / "beta_supplier_bid_synthetic.pdf",
        "Beta Systems Ltd — Supplier Bid",
        BETA_LINES,
    )


if __name__ == "__main__":
    main()
